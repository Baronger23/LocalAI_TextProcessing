import sys
from pathlib import Path

sys.path.insert(0, str(Path('.')))
from src.rag.vector_store import VectorStoreManager

vsm = VectorStoreManager()
print("--- DATABASE CONTENT CHECK ---")
try:
    with vsm._get_postgres_connection() as conn:
        rows = conn.execute("""
            SELECT d.file_name, COUNT(c.id) as chunks 
            FROM public.documents d 
            LEFT JOIN public.document_chunks c ON d.id = c.document_id 
            GROUP BY d.file_name
        """).fetchall()

        if not rows:
            print("Database is EMPTY.")
        else:
            for row in rows:
                # Use ascii safe representation for the file name to avoid terminal encoding issues
                fname = str(row['file_name']).encode('ascii', 'replace').decode()
                print(f"File: {fname} -> {row['chunks']} chunks")
except Exception as e:
    print(f"Error checking DB: {e}")
