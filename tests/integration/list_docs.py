"""List all indexed documents and search for LATS content."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg
from psycopg.rows import dict_row

conn = psycopg.connect(
    "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
    autocommit=True, row_factory=dict_row,
)

print("=== Files in DB ===")
rows = conn.execute("""
    SELECT d.file_name, d.file_path, COUNT(c.id) as chunks
    FROM public.documents d
    LEFT JOIN public.document_chunks c ON c.document_id = d.id
    GROUP BY d.id, d.file_name, d.file_path
    ORDER BY chunks DESC
""").fetchall()
for r in rows:
    print(f"  {r['file_name']}: {r['chunks']} chunks")
    print(f"    path: {r['file_path']}")

print("\n=== Search for Chuong 1 / 1.1 content ===")
rows2 = conn.execute("""
    SELECT content, metadata
    FROM public.document_chunks
    WHERE LOWER(content) LIKE '%1.1%'
       OR LOWER(content) LIKE '%tổng quan%'
       OR LOWER(content) LIKE '%chủ nghĩa hiện thực%'
       OR LOWER(content) LIKE '%chủ nghĩa tự do%'
       OR LOWER(content) LIKE '%chủ nghĩa kiến tạo%'
    LIMIT 10
""").fetchall()
for r in rows2:
    meta = r['metadata'] or {}
    src = meta.get('source', 'N/A')
    print(f"\n  source: {src}")
    print(f"  content: {r['content'][:200].replace(chr(10), ' ')}...")

conn.close()
