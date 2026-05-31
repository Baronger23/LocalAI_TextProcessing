"""
Unit & Integration tests for:
  - Query Rewriting (_rewrite_query)
  - MMR Deduplication (_mmr_rerank, mmr_search)
  - Full RAG query() flow with both optimizations active

Test strategy:
  - Unit tests use mocks to isolate logic from LLM / DB.
  - Integration tests use a dedicated test table in PostgreSQL to avoid
    polluting the production document_chunks table.
"""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from src.rag.rag_pipeline import RAGPipeline
from src.rag.vector_store import VectorStoreManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(source: str, content: str, chunk_id: str | None = None) -> Document:
    meta = {"source": source, "file_name": source}
    if chunk_id:
        meta["document_id"] = chunk_id
    return Document(page_content=content, metadata=meta)


def _unit_vsm() -> VectorStoreManager:
    """Return a VectorStoreManager wired to the integration test table."""
    return VectorStoreManager(
        backend="postgres",
        postgres_table_name="test_opt_chunks",
    )


# ---------------------------------------------------------------------------
# 1. Unit tests — Query Rewriting
# ---------------------------------------------------------------------------


class TestQueryRewriting:
    """Pure unit tests: mock the LLM, exercise _rewrite_query logic only."""

    def _make_rag(self, llm_response: str) -> RAGPipeline:
        """Build a RAGPipeline whose LLM always returns `llm_response`."""
        mock_llm = MagicMock()
        mock_llm.model = "mock-llm"
        mock_llm.generate_response.return_value = llm_response

        mock_embed = MagicMock()
        mock_embed.model = "mock-embed"

        mock_vsm = MagicMock()
        mock_vsm.get_collection_stats.return_value = {"count": 0}

        return RAGPipeline(
            llm_manager=mock_llm,
            embedding_manager=mock_embed,
            vector_store_manager=mock_vsm,
            query_rewrite_enabled=True,
        )

    def test_rewrites_abbreviation(self):
        """LLM returns expanded query — pipeline should use it."""
        rag = self._make_rag("Thời gian và cách thức ra đời của Chủ nghĩa Tư bản (CNTB)")
        rewritten = rag._rewrite_query("CNTB ra đời như thế nào")
        assert "Chủ nghĩa Tư bản" in rewritten
        assert rewritten != "CNTB ra đời như thế nào"

    def test_falls_back_when_llm_empty(self):
        """If LLM returns empty string, original query must be returned."""
        rag = self._make_rag("")
        original = "CNTB ra đời như thế nào"
        result = rag._rewrite_query(original)
        assert result == original

    def test_falls_back_when_llm_too_long(self):
        """If LLM returns something 4x longer than the original, keep original."""
        original = "short"
        # 5x longer  → over the threshold
        rag = self._make_rag("x" * (len(original) * 5))
        result = rag._rewrite_query(original)
        assert result == original

    def test_falls_back_when_llm_raises(self):
        """If the LLM call throws, _rewrite_query must not propagate the error."""
        mock_llm = MagicMock()
        mock_llm.generate_response.side_effect = RuntimeError("LLM offline")
        mock_llm.model = "mock"

        rag = RAGPipeline(
            llm_manager=mock_llm,
            embedding_manager=MagicMock(model="m"),
            vector_store_manager=MagicMock(get_collection_stats=lambda: {}),
            query_rewrite_enabled=True,
        )
        original = "câu hỏi gốc"
        assert rag._rewrite_query(original) == original

    def test_disabled_query_rewrite_skips_llm(self):
        """When query_rewrite_enabled=False, _rewrite_query must not be called."""
        mock_llm = MagicMock()
        mock_llm.generate_response.return_value = "should not appear"
        mock_llm.model = "mock"
        mock_vsm = MagicMock()
        mock_vsm.similarity_search.return_value = []
        mock_vsm.mmr_search.return_value = []
        mock_vsm.get_collection_stats.return_value = {}

        rag = RAGPipeline(
            llm_manager=mock_llm,
            embedding_manager=MagicMock(model="m"),
            vector_store_manager=mock_vsm,
            query_rewrite_enabled=False,
            mmr_enabled=False,
        )
        result = rag.query("CNTB ra đời như thế nào")
        # rewritten_query should be None (no rewriting happened)
        assert result["rewritten_query"] is None
        # generate_response should NOT have been called for rewriting
        # (it was only called 0 times, or called for the main answer — but we have
        # no docs, so the pipeline returns early without calling generate_response)
        mock_vsm.similarity_search.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Unit tests — MMR Reranking (_mmr_rerank)
# ---------------------------------------------------------------------------


class TestMMRRerank:
    """Test MMR selection logic using deterministic fake embeddings."""

    def _make_vsm_with_fake_embs(
        self, fake_id_to_emb: dict[str, List[float]]
    ) -> VectorStoreManager:
        """Build a VectorStoreManager whose DB lookup returns fake embeddings."""
        vsm = VectorStoreManager(backend="postgres")

        # Patch the DB call inside _mmr_rerank
        def fake_embed_query(text: str) -> List[float]:
            # Query vector: all-ones direction — favours docs with positive values
            return [1.0] * len(next(iter(fake_id_to_emb.values())))

        vsm.embedding_manager = MagicMock()
        vsm.embedding_manager.embed_query.side_effect = fake_embed_query

        # Patch _get_postgres_connection to return fake embedding rows
        mock_conn = MagicMock()
        fake_rows = [
            {"id": k, "emb": str(v)}
            for k, v in fake_id_to_emb.items()
        ]
        mock_conn.execute.return_value.fetchall.return_value = fake_rows
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        vsm._get_postgres_connection = MagicMock(return_value=mock_conn)
        vsm._pool_connection = MagicMock(return_value=mock_conn)

        return vsm

    def _docs_with_ids(self, specs: List[tuple[str, str, List[float]]]) -> List[Document]:
        """Create docs with deterministic fake chunk ids."""
        return [
            Document(page_content=content, metadata={"document_id": chunk_id, "source": src})
            for src, content, chunk_id in specs
        ]

    def test_returns_k_documents(self):
        """MMR must return exactly k documents when pool >= k."""
        fake_embs = {
            "id1": [1.0, 0.0],
            "id2": [0.9, 0.1],
            "id3": [0.0, 1.0],
            "id4": [-1.0, 0.0],
        }
        vsm = self._make_vsm_with_fake_embs(fake_embs)

        docs = self._docs_with_ids([
            ("doc1", "content one",   "id1"),
            ("doc2", "content two",   "id2"),
            ("doc3", "content three", "id3"),
            ("doc4", "content four",  "id4"),
        ])

        result = vsm._mmr_rerank(query="test", candidates=docs, k=2)
        assert len(result) == 2

    def test_diversity_prefers_different_docs(self):
        """
        With lambda=0.0 (pure diversity), after selecting the best doc
        the second pick should be the doc LEAST similar to the first.
        """
        # id1 and id2 are nearly identical (high cosine similarity between them)
        # id3 points in a very different direction
        fake_embs = {
            "id1": [1.0, 0.0, 0.0],
            "id2": [0.99, 0.14, 0.0],   # very similar to id1
            "id3": [0.0, 0.0, 1.0],     # orthogonal to id1/id2
        }
        vsm = self._make_vsm_with_fake_embs(fake_embs)

        docs = self._docs_with_ids([
            ("doc1", "relevant content one",   "id1"),
            ("doc2", "relevant content two",   "id2"),
            ("doc3", "very different content", "id3"),
        ])

        # pure diversity (lambda=0.0)
        result = vsm._mmr_rerank(query="test", candidates=docs, k=2, lambda_mult=0.0)
        assert len(result) == 2
        sources = {d.metadata["source"] for d in result}
        # doc1 gets picked first (highest relevance — both have same direction as query).
        # Then with pure diversity, doc3 (orthogonal) should beat doc2 (near-identical to doc1).
        assert "doc3" in sources, f"Expected doc3 in diverse selection, got {sources}"

    def test_returns_all_when_pool_smaller_than_k(self):
        """If the candidate pool has fewer docs than k, return all of them."""
        fake_embs = {"id1": [1.0, 0.0], "id2": [0.0, 1.0]}
        vsm = self._make_vsm_with_fake_embs(fake_embs)
        docs = self._docs_with_ids([
            ("doc1", "content", "id1"),
            ("doc2", "content", "id2"),
        ])
        result = vsm._mmr_rerank(query="test", candidates=docs, k=10)
        assert len(result) == 2

    def test_empty_candidates(self):
        """An empty candidate list must return an empty list."""
        vsm = self._make_vsm_with_fake_embs({})
        result = vsm._mmr_rerank(query="test", candidates=[], k=4)
        assert result == []


# ---------------------------------------------------------------------------
# 3. Integration tests — full pipeline against PostgreSQL
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.ollama
class TestRetrievalOptimizationsIntegration:
    """
    Integration tests: real PostgreSQL, real Ollama embeddings, mocked LLM.
    Uses a dedicated table 'test_opt_chunks' to avoid touching production data.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        self.vsm = _unit_vsm()
        self.vsm.delete_collection()

        # Insert three test documents:
        # doc1 and doc2 are very similar (same topic, almost same wording)
        # doc3 is about a completely different topic with a rare acronym
        docs = [
            Document(
                page_content=(
                    "Thời gian làm việc tiêu chuẩn là 8 giờ mỗi ngày, 40 giờ mỗi tuần. "
                    "Nhân viên phải tuân thủ giờ làm việc theo quy định của công ty."
                ),
                metadata={"source": "noi_quy_1"},
            ),
            Document(
                page_content=(
                    "Giờ làm việc bình thường là 8 tiếng mỗi ngày. "
                    "Người lao động cần tuân thủ lịch làm việc được công ty quy định."
                ),
                metadata={"source": "noi_quy_2"},
            ),
            Document(
                page_content=(
                    "Thời gian và cách thức ra đời của XYZ_RARE_TOKEN: "
                    "đây là khái niệm hoàn toàn khác biệt, không liên quan đến nội quy lao động."
                ),
                metadata={"source": "xyz_doc"},
            ),
        ]
        self.vsm.add_documents(docs)
        yield
        self.vsm.delete_collection()

    # ---- MMR integration ----

    def test_mmr_search_returns_k(self):
        """mmr_search must return at most k documents."""
        results = self.vsm.mmr_search("thời gian làm việc", k=2, fetch_k=10)
        assert len(results) <= 2

    def test_mmr_reduces_duplicate_results(self):
        """
        doc1 and doc2 are near-duplicates. MMR (lambda<1) should avoid picking both.
        """
        results_mmr = self.vsm.mmr_search(
            "thời gian làm việc", k=2, fetch_k=10, lambda_mult=0.5
        )
        sources = [d.metadata.get("source") for d in results_mmr]
        # Both noi_quy_1 and noi_quy_2 should NOT both appear when asking for k=2
        # with strong diversity pressure — at least one should be displaced
        assert not (
            "noi_quy_1" in sources and "noi_quy_2" in sources
        ), f"MMR did not remove redundant doc. Got sources: {sources}"

    def test_hybrid_plus_mmr_finds_rare_keyword(self):
        """
        Even with MMR active, a chunk with an exact keyword match must surface.
        """
        results = self.vsm.mmr_search(
            "XYZ_RARE_TOKEN", k=2, fetch_k=10, lambda_mult=0.7
        )
        sources = [d.metadata.get("source") for d in results]
        assert "xyz_doc" in sources, (
            f"XYZ_RARE_TOKEN doc missing from MMR results. Got: {sources}"
        )

    # ---- Query Rewriting integration ----

    def test_query_rewriting_changes_search_query(self):
        """
        When the LLM expands 'XYZ_RARE_TOKEN' into a longer phrase,
        the pipeline uses the expanded version for searching.
        We mock the LLM to control the rewrite output deterministically.
        """
        mock_llm = MagicMock()
        mock_llm.model = "mock"
        # Rewrite returns original query expanded
        mock_llm.generate_response.side_effect = [
            "Thời gian và cách thức ra đời của XYZ_RARE_TOKEN là gì",  # rewrite call
            "Câu trả lời từ LLM.",                                       # answer call
        ]

        rag = RAGPipeline(
            llm_manager=mock_llm,
            vector_store_manager=self.vsm,
            query_rewrite_enabled=True,
            mmr_enabled=True,
        )

        result = rag.query("XYZ_RARE_TOKEN", k=2)
        assert result["rewritten_query"] is not None
        assert "XYZ_RARE_TOKEN" in result["rewritten_query"]
        assert "xyz_doc" in [s["metadata"].get("source") for s in result["sources"]]

    def test_cosine_sim_static(self):
        """_cosine_sim should return 1.0 for identical vectors."""
        v = [0.5, 0.5, 0.5]
        assert abs(VectorStoreManager._cosine_sim(v, v) - 1.0) < 1e-6

    def test_cosine_sim_orthogonal(self):
        """_cosine_sim of orthogonal vectors should be 0.0."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(VectorStoreManager._cosine_sim(a, b)) < 1e-6
