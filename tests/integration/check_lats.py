"""Check LATS-2017 chunks specifically."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg
from psycopg.rows import dict_row

conn = psycopg.connect(
    "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
    autocommit=True, row_factory=dict_row,
)

# Get document_id for LATS
doc = conn.execute("""
    SELECT id, file_name FROM public.documents
    WHERE file_name LIKE '%LATS%'
""").fetchone()

if not doc:
    print("LATS document not found!")
    conn.close()
    sys.exit(1)

doc_id = doc['id']
print(f"LATS doc_id: {doc_id}")
print(f"File: {doc['file_name']}")

# Count chunks
cnt = conn.execute(
    "SELECT COUNT(*) as c FROM public.document_chunks WHERE document_id = %s",
    (doc_id,)
).fetchone()['c']
print(f"Total chunks: {cnt}")

# Search for Chuong 1 content in LATS
print("\n=== Chunks from LATS about Chuong 1 / ly luan ===")
keywords = [
    'tổng quan', '1.1', 'chủ nghĩa hiện thực', 'chủ nghĩa tự do',
    'chủ nghĩa kiến tạo', 'role theory', 'lý thuyết vai trò',
    'holsti', 'wendt', 'waltz',
]
conditions = " OR ".join(
    f"LOWER(content) LIKE '%%{kw}%%'" for kw in keywords
)
rows = conn.execute(
    f"""
    SELECT content, metadata, chunk_index
    FROM public.document_chunks
    WHERE document_id = %s AND ({conditions})
    ORDER BY chunk_index LIMIT 15
    """,
    (doc_id,)
).fetchall()

print(f"Found {len(rows)} relevant chunks in LATS:")
for r in rows:
    meta = r['metadata'] or {}
    print(f"\n  [chunk {r['chunk_index']}] page={meta.get('page','?')}")
    print(f"  {r['content'][:250].replace(chr(10), ' ')}...")

# Also show first 5 chunks to understand structure
print("\n=== First 5 chunks of LATS ===")
first5 = conn.execute("""
    SELECT content, chunk_index, metadata
    FROM public.document_chunks
    WHERE document_id = %s
    ORDER BY chunk_index LIMIT 5
""", (doc_id,)).fetchall()
for r in first5:
    print(f"\n  [chunk {r['chunk_index']}]")
    print(f"  {r['content'][:200].replace(chr(10), ' ')}...")

conn.close()
