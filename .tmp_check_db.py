from src.config import POSTGRES_CONNECTION_STRING, POSTGRES_SCHEMA
import json

print('Using POSTGRES_CONNECTION_STRING from src.config')
try:
    import psycopg
    from psycopg.rows import dict_row
except Exception as e:
    print('psycopg not available:', e)
    print('You can install with: pip install psycopg[binary]')
    raise

conn = psycopg.connect(POSTGRES_CONNECTION_STRING, row_factory=dict_row)
with conn:
    sql = f"SELECT id, file_name, metadata, uploaded_by, created_at FROM {POSTGRES_SCHEMA}.documents ORDER BY created_at DESC LIMIT 50"
    rows = conn.execute(sql).fetchall()
    print(f'Found {len(rows)} rows in {POSTGRES_SCHEMA}.documents')
    for r in rows:
        rdict = dict(r)
        # ensure metadata is JSON-serializable
        rdict['metadata'] = rdict.get('metadata') or {}
        print(json.dumps(rdict, default=str, ensure_ascii=False))
