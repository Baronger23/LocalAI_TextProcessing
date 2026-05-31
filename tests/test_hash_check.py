"""Check for content_hash duplicates and insert conflicts."""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


def compute_content_hash(text: str) -> str:
    """SHA256 hash of chunk text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_hash_duplicates():
    """Check if any chunks have duplicate content_hash."""

    rag = RAGPipeline()

    with rag.vector_store_manager._get_postgres_connection() as conn:
        # Get all chunks with content
        chunks = conn.execute(
            """
            SELECT id, document_id, content, content_hash, created_at
            FROM public.document_chunks
            ORDER BY document_id, id
            LIMIT 20
            """
        ).fetchall()

        print(f"\n[CHECK] Total chunks in DB sample: {len(chunks)}")

        # Check for duplicate content_hash
        hashes_seen = {}
        duplicates = []

        for chunk in chunks:
            content_hash = chunk['content_hash']
            if content_hash in hashes_seen:
                duplicates.append({
                    'hash': content_hash,
                    'chunk_id': chunk['id'],
                    'prev_chunk_id': hashes_seen[content_hash]['id']
                })
            else:
                hashes_seen[content_hash] = chunk

        if duplicates:
            print(f"\n[ALERT] Found {len(duplicates)} duplicate content_hash!")
            for dup in duplicates[:5]:
                print(f"  Hash {dup['hash'][:16]}... appears in chunks {dup['prev_chunk_id']} and {dup['chunk_id']}")
        else:
            print("\n[OK] No duplicate content_hash found")

        # Check for ON CONFLICT conflicts
        print("\n[CHECK] Looking for potential ON CONFLICT issues...")

        # Get hash distribution
        duplicate_hashes = conn.execute(
            """
            SELECT content_hash, COUNT(*) as count
            FROM public.document_chunks
            GROUP BY content_hash
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        ).fetchall()

        if duplicate_hashes:
            print(f"[ALERT] Found {len(duplicate_hashes)} content_hash values with multiple rows:")
            for row in duplicate_hashes:
                print(f"  Hash {row['content_hash'][:16]}... has {row['count']} rows")
        else:
            print("[OK] No content_hash duplicates")

        # Check documents and their chunk counts
        print("\n[CHECK] Document chunk distribution:")
        docs = conn.execute(
            """
            SELECT d.id, d.source_key, d.file_name,
                   COUNT(c.id) as chunk_count,
                   d.embedding_status,
                   d.created_at
            FROM public.documents d
            LEFT JOIN public.document_chunks c ON d.id = c.document_id
            GROUP BY d.id, d.source_key, d.file_name, d.embedding_status, d.created_at
            ORDER BY d.created_at DESC
            LIMIT 5
            """
        ).fetchall()

        for doc in docs:
            print(f"  Doc: {doc['file_name']}")
            print(f"    ID: {doc['id']}")
            print(f"    Chunks: {doc['chunk_count']}")
            print(f"    Status: {doc['embedding_status']}")


if __name__ == "__main__":
    test_hash_duplicates()
