"""
Debug script: xem chính xác chunks nào được retrieve cho câu hỏi,
và tại sao chatbot trả lời thiếu các ý lớn.

Chạy:
    venv\\Scripts\\python.exe tests/integration/debug_retrieval.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

QUERY = "Các công trình lý luận về vai trò trong quan hệ quốc tế"

EXPECTED_TOPICS = [
    ("Chủ nghĩa Hiện thực",  ["hiện thực", "realism", "waltz", "morgenthau"]),
    ("Chủ nghĩa Tự do",      ["tự do", "liberalism", "keohane", "nye"]),
    ("Chủ nghĩa Kiến tạo",   ["kiến tạo", "constructivism", "wendt", "identity"]),
    ("Lý thuyết Vai trò",    ["role theory", "holsti", "thuyết vai trò"]),
    ("SNA",                  ["mạng lưới", "social network", "sna"]),
]

SEP = "=" * 70


def main():
    print(f"\n{SEP}")
    print("DEBUG: RETRIEVAL ANALYSIS")
    print(f"Query: {QUERY}")
    print(SEP)

    # ── Kết nối DB trực tiếp ────────────────────────────────────────────────
    import psycopg
    from pgvector.psycopg import register_vector
    from psycopg.rows import dict_row

    conn = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
        autocommit=True, row_factory=dict_row,
    )
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)

    # Tổng số chunks
    total = conn.execute("SELECT COUNT(*) as c FROM public.document_chunks").fetchone()["c"]
    print(f"\n📊 Tổng chunks trong DB: {total}")

    # Tìm chunks liên quan đến các ý lớn
    print("\n🔍 Tìm chunks chứa từ khóa của từng ý lớn:")
    for topic, keywords in EXPECTED_TOPICS:
        kw_conditions = " OR ".join(
            f"LOWER(content) LIKE '%{kw.lower()}%'" for kw in keywords
        )
        rows = conn.execute(
            f"SELECT COUNT(*) as c FROM public.document_chunks WHERE {kw_conditions}"
        ).fetchone()
        cnt = rows["c"]
        status = "✅" if cnt > 0 else "❌"
        print(f"  {status} {topic}: {cnt} chunks chứa từ khóa")
        if cnt > 0:
            # Lấy 1 sample
            sample = conn.execute(
                f"SELECT content, metadata FROM public.document_chunks "
                f"WHERE {kw_conditions} LIMIT 1"
            ).fetchone()
            if sample:
                meta = sample["metadata"] or {}
                print(f"     Sample: [{meta.get('breadcrumb','N/A')}]")
                print(f"     {sample['content'][:120].replace(chr(10),' ')}...")

    # ── Embed query ──────────────────────────────────────────────────────────
    print("\n🔢 Embed query...")
    from src.embeddings import EmbeddingManager
    em = EmbeddingManager()
    t0 = time.perf_counter()
    qvec = em.embed_query(QUERY)
    print(f"   ✅ Done ({(time.perf_counter()-t0)*1000:.0f}ms)")

    # ── Hybrid search — xem top 8 chunks được retrieve ──────────────────────
    print("\n🔍 Top 8 chunks được retrieve (hybrid search):")
    from pgvector import Vector
    k = 8
    rows = conn.execute(
        """
        WITH sem AS (
            SELECT c.id, c.content, c.metadata,
                   ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s) AS sem_rank
            FROM public.document_chunks c
            ORDER BY c.embedding <=> %s LIMIT 20
        ),
        kw AS (
            SELECT c.id, c.content, c.metadata,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(c.fts_vector,
                           websearch_to_tsquery('simple', %s)) DESC
                   ) AS kw_rank
            FROM public.document_chunks c
            WHERE c.fts_vector @@ websearch_to_tsquery('simple', %s)
            LIMIT 20
        )
        SELECT
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.metadata, k.metadata) AS metadata,
            COALESCE(1.0/(60+s.sem_rank),0) + COALESCE(1.0/(60+k.kw_rank),0) AS rrf
        FROM sem s FULL OUTER JOIN kw k ON s.id = k.id
        ORDER BY rrf DESC LIMIT %s
        """,
        (Vector(qvec), Vector(qvec), QUERY, QUERY, k),
    ).fetchall()

    topic_coverage = {t: False for t, _ in EXPECTED_TOPICS}

    for i, row in enumerate(rows, 1):
        meta = row["metadata"] or {}
        breadcrumb = meta.get("breadcrumb", "N/A")
        content_lower = row["content"].lower()
        preview = row["content"][:150].replace("\n", " ")

        # Kiểm tra chunk này cover ý lớn nào
        covered = []
        for topic, keywords in EXPECTED_TOPICS:
            if any(kw.lower() in content_lower for kw in keywords):
                covered.append(topic)
                topic_coverage[topic] = True

        covered_str = f" → covers: {', '.join(covered)}" if covered else ""
        print(f"\n  [{i}] rrf={row['rrf']:.4f}  {breadcrumb}{covered_str}")
        print(f"       {preview}...")

    # ── Tổng kết coverage ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("📊 COVERAGE CỦA TOP 8 CHUNKS:")
    covered_count = 0
    for topic, covered in topic_coverage.items():
        status = "✅" if covered else "❌"
        print(f"  {status} {topic}")
        if covered:
            covered_count += 1

    print(f"\n  Kết quả: {covered_count}/5 ý lớn có trong retrieved chunks")

    if covered_count < 3:
        print("\n⚠️  CHẨN ĐOÁN: Retrieval không lấy được đủ chunks liên quan.")
        print("   Nguyên nhân có thể:")
        print("   1. Tài liệu về các trường phái lý thuyết nằm ở chunks khác")
        print("      → Thử tăng k (số chunks retrieve) lên 15-20")
        print("   2. Câu hỏi quá chung chung → thử hỏi cụ thể hơn")
        print("   3. Chunking quá nhỏ → mỗi trường phái nằm ở chunk riêng")
        print("      → Cần tăng k hoặc dùng query cụ thể hơn")

        # Thử với k=15
        print("\n🔍 Thử lại với k=15:")
        rows15 = conn.execute(
            """
            WITH sem AS (
                SELECT c.id, c.content, c.metadata,
                       ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s) AS sem_rank
                FROM public.document_chunks c
                ORDER BY c.embedding <=> %s LIMIT 30
            ),
            kw AS (
                SELECT c.id, c.content, c.metadata,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank(c.fts_vector,
                               websearch_to_tsquery('simple', %s)) DESC
                       ) AS kw_rank
                FROM public.document_chunks c
                WHERE c.fts_vector @@ websearch_to_tsquery('simple', %s)
                LIMIT 30
            )
            SELECT
                COALESCE(s.id, k.id) AS id,
                COALESCE(s.content, k.content) AS content,
                COALESCE(s.metadata, k.metadata) AS metadata,
                COALESCE(1.0/(60+s.sem_rank),0) + COALESCE(1.0/(60+k.kw_rank),0) AS rrf
            FROM sem s FULL OUTER JOIN kw k ON s.id = k.id
            ORDER BY rrf DESC LIMIT 15
            """,
            (Vector(qvec), Vector(qvec), QUERY, QUERY),
        ).fetchall()

        topic_coverage15 = {t: False for t, _ in EXPECTED_TOPICS}
        for row in rows15:
            content_lower = row["content"].lower()
            for topic, keywords in EXPECTED_TOPICS:
                if any(kw.lower() in content_lower for kw in keywords):
                    topic_coverage15[topic] = True

        covered15 = sum(1 for v in topic_coverage15.values() if v)
        print(f"   k=15 coverage: {covered15}/5 ý lớn")
        for topic, covered in topic_coverage15.items():
            print(f"   {'✅' if covered else '❌'} {topic}")

    conn.close()
    print(SEP)


if __name__ == "__main__":
    main()
