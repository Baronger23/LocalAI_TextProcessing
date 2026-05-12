"""
Debug: xem với k khác nhau thì chunk nào được retrieve,
và chunk 46 của LATS (có nội dung Hiện thực/Tự do/Kiến tạo) có vào top-k không.

Chạy:
    venv\\Scripts\\python.exe tests/integration/debug_topk.py
"""
from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from pgvector import Vector

QUERY = "Các công trình lý luận về vai trò trong quan hệ quốc tế"
SEP = "=" * 70

TOPICS = [
    ("Hiện thực",  ["hiện thực", "realism", "waltz", "morgenthau", "cnht"]),
    ("Tự do",      ["tự do", "liberalism", "liberal", "keohane", "cntd"]),
    ("Kiến tạo",   ["kiến tạo", "constructivism", "wendt", "cnkt"]),
    ("Role Theory",["role theory", "holsti", "thuyết vai trò", "lý thuyết vai trò"]),
    ("SNA",        ["mạng lưới xã hội", "social network", "sna"]),
]

def check_topics(content: str) -> list[str]:
    cl = content.lower()
    return [t for t, kws in TOPICS if any(k in cl for k in kws)]

def run_search(conn, qvec, k: int) -> list[dict]:
    fetch = k + 10
    rows = conn.execute("""
        WITH sem AS (
            SELECT c.id, c.content, c.metadata, c.chunk_index,
                   d.file_name,
                   ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s) AS sem_rank
            FROM public.document_chunks c
            JOIN public.documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s LIMIT %s
        ),
        kw AS (
            SELECT c.id, c.content, c.metadata, c.chunk_index,
                   d.file_name,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(c.fts_vector,
                           websearch_to_tsquery('simple', %s)) DESC
                   ) AS kw_rank
            FROM public.document_chunks c
            JOIN public.documents d ON d.id = c.document_id
            WHERE c.fts_vector @@ websearch_to_tsquery('simple', %s)
            LIMIT %s
        )
        SELECT
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.metadata, k.metadata) AS metadata,
            COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(s.file_name, k.file_name) AS file_name,
            COALESCE(1.0/(60+s.sem_rank),0) + COALESCE(1.0/(60+k.kw_rank),0) AS rrf
        FROM sem s FULL OUTER JOIN kw k ON s.id = k.id
        ORDER BY rrf DESC LIMIT %s
    """, (Vector(qvec), Vector(qvec), fetch,
          QUERY, QUERY, fetch, k)).fetchall()
    return rows

def main():
    print(f"\n{SEP}")
    print(f"QUERY: {QUERY}")
    print(SEP)

    # Connect
    conn = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
        autocommit=True, row_factory=dict_row,
    )
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)

    # Embed
    print("\n⏳ Embedding query...")
    from src.embeddings import EmbeddingManager
    t0 = time.perf_counter()
    qvec = EmbeddingManager().embed_query(QUERY)
    print(f"   Done ({(time.perf_counter()-t0)*1000:.0f}ms)")

    # Test với nhiều giá trị k
    for k in [8, 12, 15, 20]:
        rows = run_search(conn, qvec, k)

        # Đếm coverage
        covered = set()
        lats_chunks = []
        asean55_chunks = []

        for i, r in enumerate(rows, 1):
            fname = r["file_name"] or ""
            topics = check_topics(r["content"])
            covered.update(topics)
            if "LATS" in fname:
                lats_chunks.append((i, r["chunk_index"], topics, r["rrf"]))
            else:
                asean55_chunks.append((i, r["chunk_index"], topics, r["rrf"]))

        print(f"\n{'─'*70}")
        print(f"k={k}: {len(covered)}/5 topics covered | "
              f"LATS chunks: {len(lats_chunks)} | "
              f"ASEAN55 chunks: {len(asean55_chunks)}")
        print(f"  Topics covered: {list(covered) if covered else '(none)'}")

        if lats_chunks:
            print(f"  LATS chunks in top-{k}:")
            for rank, cidx, topics, rrf in lats_chunks:
                print(f"    rank={rank} chunk_idx={cidx} rrf={rrf:.4f} topics={topics}")
        else:
            print(f"  ❌ Không có chunk nào từ LATS trong top-{k}")

    # Tìm chunk 46 của LATS cụ thể
    print(f"\n{SEP}")
    print("🔍 Tìm chunk 46 của LATS trong DB:")
    lats_doc = conn.execute(
        "SELECT id FROM public.documents WHERE file_name LIKE '%LATS%'"
    ).fetchone()
    if lats_doc:
        chunk46 = conn.execute(
            "SELECT id, content, chunk_index FROM public.document_chunks "
            "WHERE document_id = %s AND chunk_index = 46",
            (lats_doc["id"],)
        ).fetchone()
        if chunk46:
            print(f"  chunk_index=46, id={chunk46['id']}")
            print(f"  Content: {chunk46['content'][:300].replace(chr(10),' ')}...")

            # Xem rank của chunk 46 trong semantic search
            rank_row = conn.execute("""
                SELECT ROW_NUMBER() OVER (ORDER BY embedding <=> %s) AS rank,
                       1 - (embedding <=> %s) AS score
                FROM public.document_chunks
                WHERE id = %s
            """, (Vector(qvec), Vector(qvec), chunk46["id"])).fetchone()

            # Tính rank thực tế
            better = conn.execute(
                "SELECT COUNT(*) as c FROM public.document_chunks "
                "WHERE embedding <=> %s < (SELECT embedding <=> %s FROM public.document_chunks WHERE id = %s)",
                (Vector(qvec), Vector(qvec), chunk46["id"])
            ).fetchone()
            actual_rank = better["c"] + 1
            print(f"  Semantic rank: #{actual_rank} trong toàn bộ {conn.execute('SELECT COUNT(*) as c FROM public.document_chunks').fetchone()['c']} chunks")
            print(f"  → Cần k >= {actual_rank} để retrieve được chunk này")
        else:
            print("  chunk_index=46 không tồn tại")

    conn.close()
    print(SEP)

if __name__ == "__main__":
    main()
