"""Quick DB inspection script."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg
from psycopg.rows import dict_row

conn = psycopg.connect(
    "postgresql://postgres:postgres@localhost:5430/secure_docs_ai",
    autocommit=True,
    row_factory=dict_row,
)

# List all tables with row counts
tables = conn.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_type='BASE TABLE'
      AND table_schema NOT IN ('pg_catalog','information_schema')
""").fetchall()

print("=== Tables in DB ===")
for t in tables:
    schema = t["table_schema"]
    name = t["table_name"]
    try:
        cnt = conn.execute(f'SELECT COUNT(*) as c FROM "{schema}"."{name}"').fetchone()
        print(f"  {schema}.{name}: {cnt['c']} rows")
    except Exception as e:
        print(f"  {schema}.{name}: ERROR - {e}")

# Check document_chunks specifically
print("\n=== Sample from document_chunks (if exists) ===")
try:
    rows = conn.execute("""
        SELECT id, content, metadata
        FROM public.document_chunks
        LIMIT 3
    """).fetchall()
    if rows:
        for r in rows:
            meta = r["metadata"] or {}
            print(f"  breadcrumb: {meta.get('breadcrumb','N/A')}")
            print(f"  content: {r['content'][:100]}...")
    else:
        print("  (empty)")
except Exception as e:
    print(f"  ERROR: {e}")

conn.close()
