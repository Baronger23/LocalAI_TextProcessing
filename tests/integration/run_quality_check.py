"""
Script kiểm tra chất lượng câu trả lời RAG — chạy trực tiếp.

Chạy:
    venv\\Scripts\\python.exe tests/integration/run_quality_check.py

Yêu cầu:
    - PostgreSQL đang chạy tại localhost:5430 (docker-compose)
    - Ollama đang chạy tại localhost:11434
    - Dữ liệu đã được index vào DB
"""
from __future__ import annotations

import re
import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Cấu hình ────────────────────────────────────────────────────────────────
QUERY = "Các công trình lý luận về vai trò trong quan hệ quốc tế"

EXPECTED_TOPICS = [
    (
        "Chủ nghĩa Hiện thực (Realism)",
        ["hiện thực", "realism", "realist", "waltz", "morgenthau", "quyền lực", "power"],
    ),
    (
        "Chủ nghĩa Tự do (Liberalism)",
        ["tự do", "liberalism", "liberal", "keohane", "nye", "hợp tác",
         "interdependence", "phụ thuộc lẫn nhau"],
    ),
    (
        "Chủ nghĩa Kiến tạo (Constructivism)",
        ["kiến tạo", "constructivism", "constructivist", "wendt",
         "bản sắc", "identity", "chuẩn mực", "norm"],
    ),
    (
        "Lý thuyết Vai trò (Role Theory)",
        ["vai trò", "role theory", "holsti", "thuyết vai trò",
         "nhận thức vai trò", "role conception"],
    ),
    (
        "Phân tích Mạng lưới Xã hội (SNA)",
        ["mạng lưới", "social network", "sna", "network analysis",
         "phân tích mạng", "centrality"],
    ),
]

MIN_TOPICS_REQUIRED = 3
SEP = "=" * 70


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_topic(answer_lower: str, keywords: list[str]) -> tuple[bool, str]:
    for kw in keywords:
        if kw.lower() in answer_lower:
            return True, kw
    return False, ""


def _print_answer(answer: str) -> None:
    print("\n📝 CÂU TRẢ LỜI CỦA CHATBOT:")
    print("-" * 70)
    for line in answer.split("\n"):
        if line.strip():
            print(textwrap.fill(line, width=70))
        else:
            print()
    print("-" * 70)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{SEP}")
    print("RAG ANSWER QUALITY CHECK")
    print(f"Query: {QUERY}")
    print(SEP)

    # ── Bước 1: Kết nối DB trực tiếp (bypass pool) ──────────────────────────
    print("\n🔌 Bước 1: Kết nối PostgreSQL trực tiếp...")
    try:
        import psycopg
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row

        conn = psycopg.connect(
            "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
            autocommit=True,
            row_factory=dict_row,
        )
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        print("   ✅ Kết nối DB thành công")
    except Exception as e:
        print(f"   ❌ Kết nối DB thất bại: {e}")
        print("   Kiểm tra: docker ps | grep postgres")
        sys.exit(1)

    # ── Bước 2: Kiểm tra số lượng chunks trong DB ────────────────────────────
    print("\n📊 Bước 2: Kiểm tra dữ liệu trong DB...")
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM public.document_chunks").fetchone()
        total_chunks = row["cnt"] if row else 0
        print(f"   Tổng số chunks trong DB: {total_chunks}")
        if total_chunks == 0:
            print("   ❌ DB trống — chưa có dữ liệu được index!")
            conn.close()
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Lỗi query DB: {e}")
        conn.close()
        sys.exit(1)

    # ── Bước 3: Embed query ──────────────────────────────────────────────────
    print("\n🔢 Bước 3: Embed query...")
    try:
        from src.embeddings import EmbeddingManager
        em = EmbeddingManager()
        t0 = time.perf_counter()
        query_vector = em.embed_query(QUERY)
        embed_ms = (time.perf_counter() - t0) * 1000
        print(f"   ✅ Embed xong ({embed_ms:.0f}ms), vector dim={len(query_vector)}")
    except Exception as e:
        print(f"   ❌ Embed thất bại: {e}")
        print("   Kiểm tra Ollama: curl http://localhost:11434/api/tags")
        conn.close()
        sys.exit(1)

    # ── Bước 4: Hybrid search trực tiếp ─────────────────────────────────────
    print("\n🔍 Bước 4: Hybrid search (pgvector + FTS)...")
    try:
        from pgvector import Vector
        k = 8
        fetch_limit = k + 5  # SEARCH_RESULT_BUFFER=5

        t0 = time.perf_counter()
        rows = conn.execute(
            """
            WITH semantic_search AS (
                SELECT c.id AS chunk_id, c.content, c.metadata,
                       ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s) AS semantic_rank
                FROM public.document_chunks c
                ORDER BY c.embedding <=> %s
                LIMIT %s
            ),
            keyword_search AS (
                SELECT c.id AS chunk_id, c.content, c.metadata,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank(c.fts_vector,
                               websearch_to_tsquery('simple', %s)) DESC
                       ) AS keyword_rank
                FROM public.document_chunks c
                WHERE c.fts_vector @@ websearch_to_tsquery('simple', %s)
                LIMIT %s
            )
            SELECT
                COALESCE(s.chunk_id, k.chunk_id) AS chunk_id,
                COALESCE(s.content, k.content) AS content,
                COALESCE(s.metadata, k.metadata) AS metadata,
                COALESCE(1.0/(60+s.semantic_rank), 0.0) +
                COALESCE(1.0/(60+k.keyword_rank), 0.0) AS rrf_score
            FROM semantic_search s
            FULL OUTER JOIN keyword_search k ON s.chunk_id = k.chunk_id
            ORDER BY rrf_score DESC
            LIMIT %s
            """,
            (Vector(query_vector), Vector(query_vector), fetch_limit,
             QUERY, QUERY, fetch_limit, k),
        ).fetchall()
        search_ms = (time.perf_counter() - t0) * 1000

        print(f"   ✅ Tìm được {len(rows)} chunks ({search_ms:.0f}ms)")
        for i, row in enumerate(rows[:5], 1):
            meta = row["metadata"] or {}
            breadcrumb = meta.get("breadcrumb", "N/A")
            preview = row["content"][:100].replace("\n", " ")
            print(f"   [{i}] rrf={row['rrf_score']:.4f}  {breadcrumb}")
            print(f"        {preview}...")

        if not rows:
            print("   ❌ Không tìm được chunk nào — kiểm tra lại dữ liệu index")
            conn.close()
            sys.exit(1)

    except Exception as e:
        print(f"   ❌ Search thất bại: {e}")
        conn.close()
        sys.exit(1)

    conn.close()

    # ── Bước 5: Gọi LLM qua RAGPipeline ─────────────────────────────────────
    print("\n🤖 Bước 5: Gọi LLM (có thể mất 15-60 giây)...")
    try:
        from src.rag import RAGPipeline
        # Tắt connection pool để tránh treo — dùng direct connection
        rag = RAGPipeline()
        # Warm pool trước khi query
        rag.vector_store_manager._init_postgres_schema()

        t0 = time.perf_counter()
        result = rag.query(question=QUERY, k=8)
        total_ms = (time.perf_counter() - t0) * 1000

        answer = result.get("answer", "")
        timing = result.get("timing", {})

        print(f"   ✅ Nhận được câu trả lời ({total_ms:.0f}ms)")
        print(f"   Timing: embed={timing.get('embedding_ms',0):.0f}ms  "
              f"search={timing.get('search_ms',0):.0f}ms  "
              f"llm={timing.get('llm_ms',0):.0f}ms")

    except Exception as e:
        print(f"   ❌ LLM thất bại: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Bước 6: Đánh giá câu trả lời ────────────────────────────────────────
    _print_answer(answer)

    print("\n📊 ĐÁNH GIÁ THEO CÁC Ý LỚN:")
    answer_lower = answer.lower()
    topic_results = []
    for topic_name, keywords in EXPECTED_TOPICS:
        found, matched_kw = _check_topic(answer_lower, keywords)
        topic_results.append((topic_name, found, matched_kw))
        status = "✅ CÓ" if found else "❌ THIẾU"
        detail = f"  ← '{matched_kw}'" if found else ""
        print(f"  {status}  {topic_name}{detail}")

    topics_found = sum(1 for _, f, _ in topic_results if f)

    # ── Bước 7: Kiểm tra regression bugs ────────────────────────────────────
    print("\n🔍 KIỂM TRA REGRESSION BUGS:")

    json_artifacts = ['"answer":', '"rewritten_query":', '```json']
    found_artifacts = [a for a in json_artifacts if a in answer]
    if found_artifacts:
        print(f"  ❌ Bug 1 (JSON artifact): {found_artifacts}")
    else:
        print("  ✅ Bug 1 (JSON artifact): Không có")

    lines = [l.strip() for l in answer.split("\n") if l.strip()]
    bc_pat = re.compile(r'^[\w\s]+\s*[>:]\s*[\w\s]+')
    is_breadcrumb = (len(lines) <= 3 and len(answer) < 200
                     and all(bc_pat.match(l) for l in lines[:3]))
    if is_breadcrumb:
        print("  ❌ Bug 1 (breadcrumb only): Answer chỉ là chỉ mục")
    else:
        print("  ✅ Bug 1 (breadcrumb only): Answer có nội dung thực")

    # ── Kết luận ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"📈 KẾT QUẢ: {topics_found}/{len(EXPECTED_TOPICS)} ý lớn được đề cập")
    print(f"   Ngưỡng yêu cầu: ≥ {MIN_TOPICS_REQUIRED}/{len(EXPECTED_TOPICS)}")

    ok = topics_found >= MIN_TOPICS_REQUIRED and not found_artifacts and not is_breadcrumb
    if ok:
        print("✅ KẾT LUẬN: ĐẠT")
    else:
        issues = []
        if topics_found < MIN_TOPICS_REQUIRED:
            missing = [n for n, f, _ in topic_results if not f]
            issues.append(f"Thiếu ý: {', '.join(missing)}")
        if found_artifacts:
            issues.append(f"JSON artifact: {found_artifacts}")
        if is_breadcrumb:
            issues.append("Answer chỉ là breadcrumb")
        print(f"❌ KẾT LUẬN: CHƯA ĐẠT — {'; '.join(issues)}")
    print(SEP)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
