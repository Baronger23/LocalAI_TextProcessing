"""Debug insertion issue - why only 2 chunks in DB when 344 should be inserted."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document

from src.rag import RAGPipeline

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.ollama]


def test_insertion_debug():
    """Test insertion with detailed logging."""

    # Create 10 test chunks
    test_chunks = [
        f"Chunk {i}: Test content for chunk {i}. " * 20
        for i in range(1, 11)
    ]

    documents = [
        Document(
            page_content=content,
            metadata={
                "source": "test_doc.pdf",
                "file_path": "test_doc.pdf",
                "file_name": "test_doc.pdf",
                "page": i
            }
        )
        for i, content in enumerate(test_chunks, 1)
    ]

    print(f"\n[TEST] Starting insertion test with {len(documents)} documents")

    rag = RAGPipeline()

    # Add documents
    ids = rag.vector_store_manager.add_documents(documents)
    print(f"\n[TEST] Returned IDs: {ids}")

    # Query database directly
    with rag.vector_store_manager._get_postgres_connection() as conn:
        # Check documents
        doc_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM public.documents"
        ).fetchone()
        print(f"[TEST] Total documents in DB: {doc_count['cnt']}")

        # Check chunks
        chunk_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM public.document_chunks"
        ).fetchone()
        print(f"[TEST] Total chunks in DB: {chunk_count['cnt']}")

        # Show chunk samples
        chunks = conn.execute(
            """
            SELECT id, document_id, chunk_index, content, embedding_model
            FROM public.document_chunks
            ORDER BY created_at
            LIMIT 5
            """
        ).fetchall()

        print("\n[TEST] Chunk samples:")
        for i, chunk in enumerate(chunks, 1):
            content_preview = chunk['content'][:50] if chunk['content'] else "NULL"
            print(f"  {i}. ID={chunk['id']}, doc_id={chunk['document_id']}, chunk={chunk['chunk_index']}, content='{content_preview}...', model={chunk['embedding_model']}")

        # Check if there are any NULL embeddings
        null_embed = conn.execute(
            "SELECT COUNT(*) as cnt FROM public.document_chunks WHERE embedding IS NULL"
        ).fetchone()
        print(f"\n[TEST] Chunks with NULL embedding: {null_embed['cnt']}")


if __name__ == "__main__":
    test_insertion_debug()
