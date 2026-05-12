import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import psycopg
from psycopg.rows import dict_row

conn = psycopg.connect(
    "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
    autocommit=True, row_factory=dict_row,
)
doc = conn.execute(
    "SELECT id FROM public.documents WHERE file_name LIKE '%LATS%'"
).fetchone()

for idx in [38, 41, 42, 44, 46]:
    r = conn.execute(
        "SELECT content, chunk_index FROM public.document_chunks "
        "WHERE document_id = %s AND chunk_index = %s",
        (doc["id"], idx)
    ).fetchone()
    if r:
        print(f"\n{'='*60}")
        print(f"CHUNK {r['chunk_index']}:")
        print(r["content"])
conn.close()
