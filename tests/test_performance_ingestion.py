"""
Production-Grade Ingestion Pipeline Tests (TDD - RED Phase)

Test suite covering:
  1. Dual-layer hash deduplication (file + chunk level)
  2. Batch embedding
  3. Bulk insert with ON CONFLICT DO NOTHING
  4. Race condition safety
  5. Retry safety
  6. Partial failure resilience
  7. Idempotency
  8. Parallel file parsing

All tests are written BEFORE implementation.
Expected: ALL FAIL initially → ALL PASS after implementation.
"""
from __future__ import annotations

import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.embeddings import EmbeddingManager
from src.rag.vector_store import VectorStoreManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_TABLE = "test_perf_chunks"


def _make_doc(content: str, source: str = "test.pdf", **extra_meta) -> Document:
    meta = {"source": source, "file_name": source, "file_path": f"/tmp/{source}"}
    meta.update(extra_meta)
    return Document(page_content=content, metadata=meta)


def _content_hash(text: str) -> str:
    """SHA256 hash of text — matches the implementation we expect."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_vsm() -> VectorStoreManager:
    """Create a VectorStoreManager using the dedicated test table."""
    return VectorStoreManager(
        backend="postgres",
        postgres_table_name=TEST_TABLE,
    )


def _count_chunks(vsm: VectorStoreManager) -> int:
    """Count rows in the test chunks table."""
    with vsm._get_postgres_connection() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {vsm.postgres_schema}.{vsm.postgres_table_name}"
        ).fetchone()
        return int(row["cnt"]) if row else 0


def _get_chunk_hashes(vsm: VectorStoreManager) -> list[str]:
    """Get all content_hash values from the test table."""
    with vsm._get_postgres_connection() as conn:
        rows = conn.execute(
            f"SELECT content_hash FROM {vsm.postgres_schema}.{vsm.postgres_table_name} "
            f"WHERE content_hash IS NOT NULL"
        ).fetchall()
        return [r["content_hash"] for r in rows]


# ---------------------------------------------------------------------------
# Fixture: clean test table before/after each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_test_table():
    """Ensure test table is clean before and after each test."""
    vsm = _make_vsm()
    vsm.delete_collection()
    yield
    vsm.delete_collection()


# ===========================================================================
# TEST 1 — File-level Hash Deduplication
# ===========================================================================

class TestFileHashDedup:
    """Upload the same file twice → second upload skips embedding entirely."""

    def test_file_hash_dedup_skips_reupload(self):
        """When the same documents (same content) are added twice,
        the second call should NOT create new embeddings."""
        vsm = _make_vsm()

        docs = [
            _make_doc("Nội quy lao động điều 1: Giờ làm việc.", source="noi_quy.pdf"),
            _make_doc("Nội quy lao động điều 2: Nghỉ phép.", source="noi_quy.pdf"),
        ]

        # First upload
        ids_1 = vsm.add_documents(docs)
        count_after_first = _count_chunks(vsm)

        # Second upload — same content
        ids_2 = vsm.add_documents(docs)
        count_after_second = _count_chunks(vsm)

        # Should not create new rows
        assert count_after_first == count_after_second, (
            f"File dedup failed: first={count_after_first}, second={count_after_second}. "
            f"Expected no new rows on re-upload."
        )


# ===========================================================================
# TEST 2 — Chunk-level Hash Deduplication
# ===========================================================================

class TestChunkHashDedup:
    """10 chunks, 5 are duplicates → only 5 new embeddings created."""

    def test_chunk_dedup_skips_existing(self):
        vsm = _make_vsm()

        unique_docs = [_make_doc(f"Unique content chunk {i}") for i in range(5)]
        duplicate_docs = [_make_doc(f"Unique content chunk {i}") for i in range(5)]

        # Insert unique chunks
        vsm.add_documents(unique_docs)
        count_after_unique = _count_chunks(vsm)
        assert count_after_unique == 5, f"Expected 5 chunks, got {count_after_unique}"

        # Insert mix of unique + duplicates (same content)
        mixed_docs = duplicate_docs + [_make_doc(f"Brand new chunk {i}") for i in range(5)]
        vsm.add_documents(mixed_docs)
        count_after_mixed = _count_chunks(vsm)

        # Should only have 10 total (5 original + 5 brand new), not 15
        assert count_after_mixed == 10, (
            f"Chunk dedup failed: expected 10 total, got {count_after_mixed}"
        )

    def test_content_hash_is_stored(self):
        """Each chunk must have a content_hash stored in the DB."""
        vsm = _make_vsm()
        docs = [_make_doc("Test hash storage content")]
        vsm.add_documents(docs)

        hashes = _get_chunk_hashes(vsm)
        assert len(hashes) == 1, f"Expected 1 hash, got {len(hashes)}"
        assert hashes[0] == _content_hash("Test hash storage content"), (
            f"Hash mismatch: {hashes[0]}"
        )


# ===========================================================================
# TEST 3 — Batch Embedding
# ===========================================================================

class TestBatchEmbedding:
    """Embedding manager should support batched embedding calls."""

    def test_embed_documents_batched_returns_correct_count(self):
        """embed_documents_batched should return one vector per input text."""
        em = EmbeddingManager()

        texts = [f"Test batch text number {i}" for i in range(10)]
        # This method should exist after implementation
        assert hasattr(em, 'embed_documents_batched'), (
            "EmbeddingManager missing embed_documents_batched method"
        )

        vectors = em.embed_documents_batched(texts, batch_size=4)
        assert len(vectors) == 10, f"Expected 10 vectors, got {len(vectors)}"
        # Each vector should have dimension 768 (nomic-embed-text)
        assert len(vectors[0]) == 768, f"Expected dim 768, got {len(vectors[0])}"

    def test_batch_embedding_truncates_long_text(self):
        """Texts longer than _MAX_EMBED_CHARS should be truncated, not crash."""
        em = EmbeddingManager()
        long_text = "A" * 50000  # Way over 8000 char limit
        vectors = em.embed_documents_batched([long_text], batch_size=1)
        assert len(vectors) == 1, "Should handle long text gracefully"


# ===========================================================================
# TEST 4 — Bulk Insert ON CONFLICT DO NOTHING
# ===========================================================================

class TestBulkInsert:
    """Insert 100 chunks with potential hash collisions → no crash, no duplicate."""

    def test_bulk_insert_no_duplicate_on_conflict(self):
        vsm = _make_vsm()

        # Create docs with intentional content overlap
        docs_batch1 = [_make_doc(f"Shared content {i}") for i in range(50)]
        docs_batch2 = [_make_doc(f"Shared content {i}") for i in range(50)]  # same content
        extra_docs = [_make_doc(f"Extra content {i}") for i in range(50)]

        vsm.add_documents(docs_batch1)
        count_1 = _count_chunks(vsm)
        assert count_1 == 50

        # This should NOT crash and should NOT create duplicates
        vsm.add_documents(docs_batch2 + extra_docs)
        count_2 = _count_chunks(vsm)
        assert count_2 == 100, (
            f"Bulk insert dedup failed: expected 100, got {count_2}"
        )


# ===========================================================================
# TEST 5 — Race Condition Safety
# ===========================================================================

class TestRaceCondition:
    """Two threads upload the same data simultaneously → no duplicates, no crash."""

    def test_concurrent_upload_no_crash_no_duplicate(self):
        vsm = _make_vsm()
        docs = [_make_doc(f"Concurrent chunk {i}") for i in range(10)]

        errors = []

        def upload_worker():
            try:
                # Each worker uses its own VSM instance (own DB connection)
                worker_vsm = _make_vsm()
                worker_vsm.add_documents(docs)
            except Exception as e:
                errors.append(e)

        # Run 2 concurrent uploads
        threads = [threading.Thread(target=upload_worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)

        # No errors should have occurred
        assert len(errors) == 0, f"Concurrent upload crashed: {errors}"

        # Should have exactly 10 chunks (not 20)
        count = _count_chunks(vsm)
        assert count == 10, (
            f"Race condition created duplicates: expected 10, got {count}"
        )


# ===========================================================================
# TEST 6 — Retry Safety (no duplicate on retry)
# ===========================================================================

class TestRetrySafety:
    """Embedding fails mid-batch → retry does not create duplicates."""

    def test_retry_after_partial_failure_no_duplicate(self):
        vsm = _make_vsm()

        docs = [_make_doc(f"Retry test chunk {i}") for i in range(5)]

        # First attempt: insert normally
        vsm.add_documents(docs)
        count_1 = _count_chunks(vsm)
        assert count_1 == 5

        # Second attempt: simulate retry (same docs again)
        vsm.add_documents(docs)
        count_2 = _count_chunks(vsm)
        assert count_2 == 5, (
            f"Retry created duplicates: expected 5, got {count_2}"
        )


# ===========================================================================
# TEST 7 — Partial Failure Resilience
# ===========================================================================

class TestPartialFailure:
    """10 files, 1 file fails → 9 files still succeed."""

    def test_one_file_failure_does_not_block_others(self):
        from src.document_loader import DocumentProcessor

        processor = DocumentProcessor()

        # Create real test files: 9 valid .txt files + 1 invalid
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 9 valid text files
            for i in range(9):
                fpath = os.path.join(tmpdir, f"valid_{i}.txt")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"Valid document content for file {i}. " * 20)

            # Create 1 file that will cause an error (binary garbage as .pdf)
            bad_path = os.path.join(tmpdir, "bad_file.pdf")
            with open(bad_path, "wb") as f:
                f.write(b"\x00\x01\x02\x03INVALID_PDF_CONTENT")

            # Process directory — should NOT throw, should return docs from 9 valid files
            docs = processor.load_directory(tmpdir)

            # Should have loaded at least 9 documents (from txt files)
            assert len(docs) >= 9, (
                f"Partial failure: expected >= 9 docs from valid files, got {len(docs)}"
            )


# ===========================================================================
# TEST 8 — Idempotency
# ===========================================================================

class TestIdempotency:
    """Running the same ingestion twice produces identical DB state."""

    def test_double_ingest_same_result(self):
        vsm = _make_vsm()

        docs = [
            _make_doc("Idempotent chunk alpha", source="idem.pdf"),
            _make_doc("Idempotent chunk beta", source="idem.pdf"),
            _make_doc("Idempotent chunk gamma", source="idem.pdf"),
        ]

        # First run
        vsm.add_documents(docs)
        count_1 = _count_chunks(vsm)
        hashes_1 = sorted(_get_chunk_hashes(vsm))

        # Second run — exact same data
        vsm.add_documents(docs)
        count_2 = _count_chunks(vsm)
        hashes_2 = sorted(_get_chunk_hashes(vsm))

        assert count_1 == count_2, (
            f"Idempotency failed on count: {count_1} vs {count_2}"
        )
        assert hashes_1 == hashes_2, "Idempotency failed on hashes"


# ===========================================================================
# TEST 9 — Parallel File Parsing
# ===========================================================================

class TestParallelParsing:
    """Multiple files parsed concurrently → all succeed."""

    def test_parallel_load_directory(self):
        from src.document_loader import DocumentProcessor
        import tempfile
        import os

        processor = DocumentProcessor()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 5 text files
            for i in range(5):
                fpath = os.path.join(tmpdir, f"parallel_{i}.txt")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"Parallel processing test document {i}. " * 50)

            start = time.time()
            docs = processor.load_directory(tmpdir)
            elapsed = time.time() - start

            assert len(docs) >= 5, (
                f"Parallel parsing: expected >= 5 docs, got {len(docs)}"
            )
            # Just log elapsed time for awareness (no hard assertion on speed)
            print(f"Parallel parsing of 5 files took {elapsed:.2f}s")
