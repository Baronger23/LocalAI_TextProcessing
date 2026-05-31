"""Detailed trace of insertion process."""
import hashlib
import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import EmbeddingManager
from src.rag.vector_store import VectorStoreManager

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.ollama]


def trace_postgres_add_documents():
    """Manually trace through _postgres_add_documents logic."""

    # Create small test case
    test_chunks = [
        Document(page_content=f"Chunk {i}: Test content {i}" * 20,
                metadata={"source": "test.pdf", "page": i})
        for i in range(1, 6)  # 5 chunks
    ]

    print(f"\n[TRACE] Starting manual insertion trace with {len(test_chunks)} chunks")

    embedding_mgr = EmbeddingManager()
    vs_mgr = VectorStoreManager(embedding_manager=embedding_mgr, backend="postgres")

    # Step 1: Manually compute hashes
    print("\n[TRACE] Step 1: Compute content hashes")
    hashes = []
    for i, doc in enumerate(test_chunks):
        h = hashlib.sha256(doc.page_content.encode()).hexdigest()
        hashes.append(h)
        print(f"  Chunk {i+1}: hash={h[:16]}..., len={len(doc.page_content)}")

    # Step 2: Check existing hashes
    print("\n[TRACE] Step 2: Check existing hashes in DB")
    with vs_mgr._get_postgres_connection() as conn:
        if hashes:
            placeholders = ",".join(["%s"] * len(hashes))
            existing = conn.execute(
                f"SELECT content_hash FROM public.document_chunks WHERE content_hash IN ({placeholders})",
                hashes
            ).fetchall()
            print(f"  Found {len(existing)} existing hashes")
            for row in existing:
                print(f"    {row['content_hash'][:16]}...")

    # Step 3: Call add_documents
    print("\n[TRACE] Step 3: Call add_documents")
    try:
        ids = vs_mgr.add_documents(test_chunks)
        print(f"  Returned IDs: {ids}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Check DB directly
    print("\n[TRACE] Step 4: Verify in DB")
    with vs_mgr._get_postgres_connection() as conn:
        doc_count = conn.execute("SELECT COUNT(*) as cnt FROM public.documents").fetchone()
        print(f"  Total documents: {doc_count['cnt']}")

        chunk_count = conn.execute("SELECT COUNT(*) as cnt FROM public.document_chunks").fetchone()
        print(f"  Total chunks: {chunk_count['cnt']}")

        # Show documents
        docs = conn.execute(
            """
            SELECT d.id, d.source_key, d.file_name,
                   COUNT(c.id) as chunk_count,
                   d.embedding_status
            FROM public.documents d
            LEFT JOIN public.document_chunks c ON d.id = c.document_id
            GROUP BY d.id, d.source_key, d.file_name, d.embedding_status
            ORDER BY d.created_at DESC
            LIMIT 5
            """
        ).fetchall()

        print("\n  Recent documents:")
        for doc in docs:
            print(f"    {doc['file_name']}: {doc['chunk_count']} chunks (status: {doc['embedding_status']})")


if __name__ == "__main__":
    trace_postgres_add_documents()
