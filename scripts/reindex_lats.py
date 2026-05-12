"""
Re-index LATS document với CHUNK_SIZE=2000, CHUNK_OVERLAP=400.

Bước thực hiện:
  1. Xóa chunks cũ của LATS trong DB
  2. Reset embedding_status về 'pending'
  3. Re-process file với chunk size mới
  4. Verify số chunks mới

Chạy:
    venv\\Scripts\\python.exe scripts/reindex_lats.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from psycopg.rows import dict_row

LATS_FILE = "data/raw/LATS-2017 - Vai Trò Của Asean Trong Hợp Tác An Ninh - Chính Trị Đông Á Từ Sau 1991 Đến 2015.pdf"
SEP = "=" * 60


def main():
    print(f"\n{SEP}")
    print("RE-INDEX LATS với CHUNK_SIZE=2000, CHUNK_OVERLAP=400")
    print(SEP)

    # ── Kiểm tra file tồn tại ────────────────────────────────────────
    lats_path = Path(LATS_FILE)
    if not lats_path.exists():
        # Tìm file LATS trong data/raw
        candidates = list(Path("data/raw").glob("*LATS*"))
        if not candidates:
            print(f"❌ Không tìm thấy file LATS trong data/raw/")
            print("   Các file hiện có:")
            for f in Path("data/raw").iterdir():
                print(f"   - {f.name}")
            sys.exit(1)
        lats_path = candidates[0]
        print(f"   Tìm thấy: {lats_path.name}")

    print(f"\n📄 File: {lats_path.name}")

    # ── Kết nối DB ───────────────────────────────────────────────────
    conn = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
        autocommit=True, row_factory=dict_row,
    )

    # Tìm document record
    doc = conn.execute(
        "SELECT id, file_name, embedding_status FROM public.documents "
        "WHERE file_name LIKE '%LATS%'"
    ).fetchone()

    if doc:
        old_count = conn.execute(
            "SELECT COUNT(*) as c FROM public.document_chunks WHERE document_id = %s",
            (doc["id"],)
        ).fetchone()["c"]
        print(f"\n🗑️  Xóa {old_count} chunks cũ của LATS...")

        # Xóa chunks cũ
        conn.execute(
            "DELETE FROM public.document_chunks WHERE document_id = %s",
            (doc["id"],)
        )
        # Xóa document record để force re-insert
        conn.execute(
            "DELETE FROM public.documents WHERE id = %s",
            (doc["id"],)
        )
        print(f"   ✅ Đã xóa {old_count} chunks và document record")
    else:
        print("\n   Document chưa có trong DB — sẽ index mới")

    conn.close()

    # ── Re-index với chunk size mới ──────────────────────────────────
    print(f"\n⚙️  Khởi tạo RAGPipeline với CHUNK_SIZE=2000...")
    from src.rag import RAGPipeline
    from src.document_loader import DocumentProcessor
    from src.config import CHUNK_SIZE, CHUNK_OVERLAP

    print(f"   CHUNK_SIZE={CHUNK_SIZE}, CHUNK_OVERLAP={CHUNK_OVERLAP}")

    if CHUNK_SIZE < 1500:
        print(f"   ⚠️  CHUNK_SIZE={CHUNK_SIZE} — hãy đảm bảo .env đã được cập nhật!")
        print("   Thử reload env...")
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import CHUNK_SIZE as CS2, CHUNK_OVERLAP as CO2
        print(f"   Sau reload: CHUNK_SIZE={CS2}, CHUNK_OVERLAP={CO2}")

    rag = RAGPipeline()

    print(f"\n📥 Đang process và index file...")
    t0 = time.perf_counter()

    try:
        count = rag.load_documents(str(lats_path), is_directory=False)
        elapsed = time.perf_counter() - t0
        print(f"\n✅ Index xong: {count} chunks ({elapsed:.1f}s)")
    except Exception as e:
        print(f"\n❌ Index thất bại: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Verify ───────────────────────────────────────────────────────
    print(f"\n🔍 Verify kết quả...")
    conn2 = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
        autocommit=True, row_factory=dict_row,
    )
    doc2 = conn2.execute(
        "SELECT id FROM public.documents WHERE file_name LIKE '%LATS%'"
    ).fetchone()
    if doc2:
        new_count = conn2.execute(
            "SELECT COUNT(*) as c FROM public.document_chunks WHERE document_id = %s",
            (doc2["id"],)
        ).fetchone()["c"]
        print(f"   Chunks mới trong DB: {new_count}")

        # Kiểm tra chunk có nội dung về 5 trường phái không
        topics = {
            "Hiện thực": ["hiện thực", "cnht"],
            "Tự do":     ["tự do", "cntd"],
            "Kiến tạo":  ["kiến tạo", "cnkt"],
            "Role Theory":["role theory", "holsti"],
            "SNA":       ["mạng lưới xã hội", "sna"],
        }
        print(f"\n   Kiểm tra coverage trong chunks mới:")
        for topic, kws in topics.items():
            cond = " OR ".join(f"LOWER(content) LIKE '%%{k}%%'" for k in kws)
            cnt = conn2.execute(
                f"SELECT COUNT(*) as c FROM public.document_chunks "
                f"WHERE document_id = %s AND ({cond})",
                (doc2["id"],)
            ).fetchone()["c"]
            status = "✅" if cnt > 0 else "❌"
            print(f"   {status} {topic}: {cnt} chunks")

        # Xem chunk nào chứa cả 5 trường phái
        print(f"\n   Chunks chứa nhiều trường phái nhất:")
        sample = conn2.execute(
            """
            SELECT chunk_index, content
            FROM public.document_chunks
            WHERE document_id = %s
              AND (LOWER(content) LIKE '%%hiện thực%%'
                   OR LOWER(content) LIKE '%%tự do%%'
                   OR LOWER(content) LIKE '%%kiến tạo%%')
            ORDER BY chunk_index
            LIMIT 5
            """,
            (doc2["id"],)
        ).fetchall()
        for r in sample:
            preview = r["content"][:200].replace("\n", " ")
            print(f"   [chunk {r['chunk_index']}] {preview}...")

    conn2.close()
    print(f"\n{SEP}")
    print("✅ HOÀN THÀNH — Restart Streamlit để áp dụng thay đổi")
    print(SEP)


if __name__ == "__main__":
    main()
