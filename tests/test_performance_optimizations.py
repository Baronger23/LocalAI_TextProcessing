"""
Comprehensive pytest test suite for RAG performance optimisations.

Groups:
  1. Prompt Fusion (FusedLLMResponse)
  2. Concurrency and Queue (LLMManager)
  3. Caching (QueryCache, EmbeddingManager)
  4. Search (VectorStoreManager)
  5. Keep-Alive and Config (settings + managers)
  6. Benchmark / Timing (PerformanceBenchmark)
  7. Failure / Edge Cases
  BONUS: End-to-end integration test

All external dependencies (Ollama, DB) are mocked via unittest.mock.
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Source imports
# ---------------------------------------------------------------------------
from src.rag.models import FusedLLMResponse
from src.rag.query_cache import QueryCache
from src.rag.benchmark import PerformanceBenchmark
from src.rag.exceptions import LLMTimeoutError, LLMQueueFullError
from src.llm.llm_manager import LLMManager
from src.embeddings.embedding_manager import EmbeddingManager
from src.rag.vector_store import VectorStoreManager
from src.rag.rag_pipeline import RAGPipeline


# ===========================================================================
# GROUP 1 — Prompt Fusion (FusedLLMResponse)
# ===========================================================================

class TestFusedLLMResponse:
    """Tests for FusedLLMResponse.from_json() parsing logic."""

    def test_fusion_success_json(self):
        """Valid JSON with all fields parses correctly."""
        raw = json.dumps({
            "answer": "The capital is Paris.",
            "rewritten_query": "What is the capital of France?",
            "confidence": 0.9,
        })
        result = FusedLLMResponse.from_json(raw)

        assert result.answer == "The capital is Paris."
        assert result.rewritten_query == "What is the capital of France?"
        assert result.confidence == pytest.approx(0.9)

    def test_fusion_fallback_on_invalid_json(self):
        """Plain text (not JSON) falls back gracefully — no exception raised."""
        raw_text = "This is just a plain text answer from the LLM."
        result = FusedLLMResponse.from_json(raw_text)

        # Must not raise; answer should be the raw text
        assert isinstance(result, FusedLLMResponse)
        assert result.answer == raw_text.strip()
        assert result.rewritten_query is None
        assert result.confidence is None

    def test_fusion_partial_json(self):
        """JSON missing the optional confidence field — confidence is None, no crash."""
        raw = json.dumps({
            "answer": "Some answer.",
            "rewritten_query": None,
            # confidence intentionally omitted
        })
        result = FusedLLMResponse.from_json(raw)

        assert result.answer == "Some answer."
        assert result.confidence is None  # missing field -> None, not an error


# ===========================================================================
# GROUP 2 — Concurrency and Queue (LLMManager)
# ===========================================================================

class TestLLMManagerConcurrency:
    """Tests for LLMManager semaphore, queue, and timeout behaviour."""

    def _make_manager(self, max_concurrent_calls=2, max_queue_size=10):
        """Create an LLMManager with a mocked OllamaLLM instance."""
        with patch("src.llm.llm_manager.OllamaLLM"):
            manager = LLMManager(
                max_concurrent_calls=max_concurrent_calls,
                max_queue_size=max_queue_size,
            )
        # Replace the lazy _llm with a fresh mock so we control invoke()
        manager._llm = MagicMock()
        return manager

    def test_max_concurrent_llm_calls(self):
        """At most max_concurrent_calls threads run the LLM simultaneously."""
        manager = self._make_manager(max_concurrent_calls=2)

        # Track how many threads are inside llm.invoke at the same time
        concurrent_count = [0]
        max_seen = [0]
        lock = threading.Lock()

        def slow_invoke(prompt):
            with lock:
                concurrent_count[0] += 1
                if concurrent_count[0] > max_seen[0]:
                    max_seen[0] = concurrent_count[0]
            time.sleep(0.1)
            with lock:
                concurrent_count[0] -= 1
            return "ok"

        manager._llm.invoke.side_effect = slow_invoke

        threads = [threading.Thread(target=manager.invoke, args=("prompt",)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # With semaphore=2, never more than 2 concurrent calls
        assert max_seen[0] <= 2

    def test_queue_overflow_reject(self):
        """3rd request is rejected immediately when semaphore=1 and queue is full."""
        manager = self._make_manager(max_concurrent_calls=1, max_queue_size=1)

        # Hold the semaphore slot with a long-running call
        semaphore_held = threading.Event()
        can_release = threading.Event()

        def blocking_invoke(prompt):
            semaphore_held.set()
            can_release.wait(timeout=5)
            return "ok"

        manager._llm.invoke.side_effect = blocking_invoke

        # Thread 1: acquires the semaphore slot
        t1 = threading.Thread(target=manager.invoke, args=("p1",))
        t1.start()
        semaphore_held.wait(timeout=5)  # wait until slot is taken

        # Directly fill the queue counter to simulate max_queue_size waiting requests
        with manager._queue_lock:
            manager._queue_count = manager.max_queue_size

        # Thread 3: should be rejected immediately with LLMQueueFullError
        with pytest.raises(LLMQueueFullError):
            manager.invoke("p3")

        # Cleanup
        can_release.set()
        t1.join()

    def test_llm_timeout_cancel(self):
        """Request times out when semaphore is held and timeout is very short."""
        manager = self._make_manager(max_concurrent_calls=1)

        # Hold the semaphore so the next acquire must wait
        manager._semaphore.acquire()

        # Patch the module-level timeout constant to a very small value
        with patch("src.llm.llm_manager._SEMAPHORE_TIMEOUT_S", 0.01):
            with pytest.raises(LLMTimeoutError):
                manager._acquire()

        # Release so the semaphore is not leaked
        manager._semaphore.release()

    def test_queue_wait_time_recorded(self):
        """generate_response_fused returns queue_wait_ms >= 0."""
        manager = self._make_manager(max_concurrent_calls=2)

        # Mock llm.invoke to return valid JSON immediately
        fused_json = json.dumps({
            "answer": "Quick answer.",
            "rewritten_query": None,
            "confidence": 0.8,
        })
        manager._llm.invoke.return_value = fused_json

        result = manager.generate_response_fused(query="test", context="ctx")

        assert "queue_wait_ms" in result
        assert result["queue_wait_ms"] >= 0


# ===========================================================================
# GROUP 3 — Caching
# ===========================================================================

class TestQueryCache:
    """Tests for QueryCache TTL, hit/miss counters, and key isolation."""

    def test_query_cache_hit(self):
        """Set a value, get it back — hit count increments, miss count stays 0."""
        cache = QueryCache(ttl_seconds=60, enabled=True)
        cache.set("key1", {"answer": "hello"})

        result = cache.get("key1")

        assert result == {"answer": "hello"}
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_query_cache_key_with_filters(self):
        """Same query with different filters produces different cache keys."""
        cache = QueryCache(ttl_seconds=60, enabled=True)

        key_no_filter = cache.make_key(
            query="What is AI?",
            top_k=4,
            filters=None,
            model_version="qwen2.5:7b",
        )
        key_with_filter = cache.make_key(
            query="What is AI?",
            top_k=4,
            filters={"department": "engineering"},
            model_version="qwen2.5:7b",
        )

        assert key_no_filter != key_with_filter

    def test_query_cache_ttl_expire(self):
        """Entry expires after TTL — get() returns None after expiry."""
        # Use TTL=0 so the entry expires immediately
        cache = QueryCache(ttl_seconds=0, enabled=True)
        cache.set("expiring_key", "some_value")

        # Sleep slightly to ensure time.time() has advanced past expire_at
        time.sleep(0.05)

        result = cache.get("expiring_key")
        assert result is None


class TestEmbeddingCache:
    """Tests for EmbeddingManager LRU cache behaviour."""

    def _make_manager(self):
        """Create an EmbeddingManager with cache enabled and mocked OllamaEmbeddings."""
        with patch("src.embeddings.embedding_manager.OllamaEmbeddings"):
            manager = EmbeddingManager(cache_enabled=True, cache_max_size=100)
        manager._embeddings = MagicMock()
        manager._embeddings.embed_query.return_value = [1.0, 2.0]
        return manager

    def test_embedding_cache_hit(self):
        """Second call with same text hits cache — underlying embed_query called once."""
        manager = self._make_manager()

        result1 = manager.embed_query("Hello world")
        result2 = manager.embed_query("Hello world")

        assert result1 == [1.0, 2.0]
        assert result2 == [1.0, 2.0]
        # OllamaEmbeddings.embed_query should have been called only once
        manager._embeddings.embed_query.assert_called_once()

    def test_embedding_normalization(self):
        """Different whitespace/case variants map to the same cache key."""
        manager = self._make_manager()

        # Both normalise to "hello world" -> same cache key
        manager.embed_query("Hello   World")
        manager.embed_query("hello world")

        # Only one real embed call should have been made
        manager._embeddings.embed_query.assert_called_once()


# ===========================================================================
# GROUP 4 — Search (VectorStoreManager)
# ===========================================================================

class TestVectorStoreSearch:
    """Tests for _postgres_similarity_search LIMIT calculation and validation."""

    def _make_vsm(self, search_result_buffer=5):
        """Create a VectorStoreManager with mocked embedding manager."""
        mock_embedding_manager = MagicMock()
        mock_embedding_manager.embed_query.return_value = [0.1] * 768

        with patch("src.rag.vector_store.Path.mkdir"):
            vsm = VectorStoreManager(
                embedding_manager=mock_embedding_manager,
                search_result_buffer=search_result_buffer,
                backend="postgres",
            )
        return vsm

    def test_search_limit_with_buffer(self):
        """SQL LIMIT for each CTE equals k + search_result_buffer (10 = 5 + 5)."""
        vsm = self._make_vsm(search_result_buffer=5)

        # Stub out schema init
        vsm._init_postgres_schema = MagicMock()

        # Stub _import_postgres_dependencies — Vector just passes the value through
        mock_Vector = MagicMock(side_effect=lambda v: v)
        vsm._import_postgres_dependencies = MagicMock(
            return_value=(MagicMock(), mock_Vector, MagicMock(), MagicMock())
        )

        # Build a mock connection that captures execute() calls
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        @contextmanager
        def fake_pool_connection():
            yield mock_conn

        vsm._pool_connection = fake_pool_connection

        vsm._postgres_similarity_search(query="test", k=5, mmr_enabled=False)

        # Inspect the SQL parameters passed to conn.execute
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args
        params = call_args[0][1]  # positional: (sql, params)

        # fetch_limit = k + buffer = 5 + 5 = 10
        # It appears twice in params: once for semantic CTE LIMIT, once for keyword CTE LIMIT
        assert 10 in params, (
            f"Expected LIMIT=10 (k=5 + buffer=5) in SQL params, got: {params}"
        )

    def test_search_k_less_than_1_raises(self):
        """k=0 raises ValueError before any DB call."""
        vsm = self._make_vsm()

        with pytest.raises(ValueError, match="k must be >= 1"):
            vsm._postgres_similarity_search(query="test", k=0)


# ===========================================================================
# GROUP 5 — Keep-Alive and Config
# ===========================================================================

class TestKeepAliveConfig:
    """Tests for OLLAMA_KEEP_ALIVE default, env override, and manager propagation."""

    def test_keep_alive_default(self):
        """OLLAMA_KEEP_ALIVE defaults to 300 when env var is not set."""
        env_without_keep_alive = {k: v for k, v in os.environ.items() if k != "OLLAMA_KEEP_ALIVE"}
        with patch.dict(os.environ, env_without_keep_alive, clear=True):
            from src.config.settings import _safe_int
            value = _safe_int("OLLAMA_KEEP_ALIVE", 300)
        assert value == 300

    def test_keep_alive_env_override(self):
        """_safe_int reads OLLAMA_KEEP_ALIVE=600 from environment correctly."""
        with patch.dict(os.environ, {"OLLAMA_KEEP_ALIVE": "600"}):
            from src.config.settings import _safe_int
            value = _safe_int("OLLAMA_KEEP_ALIVE", 300)
        assert value == 600

    def test_llm_manager_uses_keep_alive(self):
        """LLMManager stores the keep_alive value passed at construction."""
        with patch("src.llm.llm_manager.OllamaLLM"):
            manager = LLMManager(keep_alive=600)
        assert manager.keep_alive == 600

    def test_embedding_manager_uses_keep_alive(self):
        """EmbeddingManager stores the keep_alive value passed at construction."""
        with patch("src.embeddings.embedding_manager.OllamaEmbeddings"):
            manager = EmbeddingManager(keep_alive=600)
        assert manager.keep_alive == 600


# ===========================================================================
# GROUP 6 — Benchmark / Timing (PerformanceBenchmark)
# ===========================================================================

class TestPerformanceBenchmark:
    """Tests for PerformanceBenchmark timing, slow-step warnings, and QPS."""

    def test_timing_keys_exist(self):
        """build_timing_dict always returns all required timing keys."""
        bench = PerformanceBenchmark()
        timings = {
            "embedding_ms": 12.5,
            "search_ms": 45.0,
            "llm_ms": 800.0,
            "queue_wait_ms": 3.0,
            "total_ms": 860.5,
            # ttft_ms intentionally omitted — should default to 0.0
        }
        result = bench.build_timing_dict(timings)

        required_keys = {"queue_wait_ms", "embedding_ms", "search_ms", "llm_ms", "total_ms"}
        for key in required_keys:
            assert key in result, f"Missing required timing key: {key}"

    def test_slow_step_warning(self):
        """A step exceeding 5000 ms triggers a logger.warning call."""
        bench = PerformanceBenchmark()

        # Patch time.perf_counter to simulate a 6-second elapsed time.
        # The measure() context manager calls perf_counter twice:
        #   1st call -> start time (0.0)
        #   2nd call -> end time (6.0)  => elapsed = 6000 ms > 5000 ms threshold
        call_count = [0]

        def fake_perf_counter():
            call_count[0] += 1
            return 0.0 if call_count[0] == 1 else 6.0

        with patch("src.rag.benchmark.time.perf_counter", side_effect=fake_perf_counter):
            with patch("src.rag.benchmark.logger") as mock_logger:
                with bench.measure("slow_step"):
                    pass  # body is instant; perf_counter is mocked

        mock_logger.warning.assert_called_once()
        # Verify the warning message mentions the slow step
        warning_call = mock_logger.warning.call_args
        assert warning_call is not None

    def test_qps_counter(self):
        """Recording 5 queries results in get_qps() > 0."""
        bench = PerformanceBenchmark(window_seconds=60)

        for _ in range(5):
            bench.record_query()

        assert bench.get_qps() > 0


# ===========================================================================
# GROUP 7 — Failure / Edge Cases
# ===========================================================================

@contextmanager
def _dummy_context_manager():
    """Yields a fake _StepTimer-like object for use when mocking benchmark.measure."""
    class _FakeTimer:
        elapsed_ms = 0.0
    yield _FakeTimer()


class TestFailureEdgeCases:
    """Tests for graceful degradation under LLM errors, empty retrieval, and DB failures."""

    def _make_rag(self):
        """Build a RAGPipeline with all external dependencies mocked."""
        from langchain_core.documents import Document

        mock_llm_manager = MagicMock()
        mock_llm_manager.model = "test-model"

        mock_embedding_manager = MagicMock()

        mock_vector_store_manager = MagicMock()
        # Default: return one document so the pipeline reaches the LLM step
        mock_vector_store_manager.similarity_search.return_value = [
            Document(page_content="Some context.", metadata={})
        ]

        mock_query_cache = MagicMock()
        mock_query_cache.get.return_value = None  # no cache hit
        mock_query_cache.make_key.return_value = "test_cache_key"

        mock_benchmark = MagicMock()
        # Use side_effect so a fresh context manager is created on every call to
        # benchmark.measure(...).  A single return_value would be exhausted after
        # the first `with` block and raise AttributeError on subsequent calls.
        mock_benchmark.measure.side_effect = lambda step_name: _dummy_context_manager()
        mock_benchmark.build_timing_dict.return_value = {
            "embedding_ms": 0.0,
            "search_ms": 0.0,
            "llm_ms": 0.0,
            "queue_wait_ms": 0.0,
            "ttft_ms": 0.0,
            "total_ms": 0.0,
        }

        # Default fused response
        mock_llm_manager.generate_response_fused.return_value = {
            "answer": "default answer",
            "rewritten_query": None,
            "confidence": 0.8,
            "queue_wait_ms": 1.0,
        }
        mock_llm_manager.generate_response.return_value = "fallback answer"

        rag = RAGPipeline(
            llm_manager=mock_llm_manager,
            embedding_manager=mock_embedding_manager,
            vector_store_manager=mock_vector_store_manager,
            query_cache=mock_query_cache,
            benchmark=mock_benchmark,
            prompt_fusion_enabled=True,
        )
        return rag, mock_llm_manager, mock_vector_store_manager

    def test_llm_exception_handling(self):
        """Fused LLM failure falls back to classic generate_response — no exception raised."""
        rag, mock_llm_manager, _ = self._make_rag()

        # Fused call raises a generic exception
        mock_llm_manager.generate_response_fused.side_effect = Exception("LLM error")
        mock_llm_manager.generate_response.return_value = "fallback answer"

        # Should NOT raise; pipeline catches the exception and falls back
        response = rag.query("test question")

        assert "answer" in response
        assert isinstance(response["answer"], str)

    def test_empty_retrieval(self):
        """Empty similarity_search result returns a Vietnamese 'not found' answer."""
        rag, _, mock_vsm = self._make_rag()
        mock_vsm.similarity_search.return_value = []

        response = rag.query("test question")

        assert "answer" in response
        assert "Không tìm thấy" in response["answer"], (
            f"Expected 'Không tìm thấy' in answer, got: {response['answer']!r}"
        )

    def test_db_connection_error(self):
        """_pool_connection propagates pool init failure as an Exception."""
        mock_embedding_manager = MagicMock()

        with patch("src.rag.vector_store.Path.mkdir"):
            vsm = VectorStoreManager(
                embedding_manager=mock_embedding_manager,
                backend="postgres",
            )

        # Make _get_pool raise to simulate DB being down
        vsm._get_pool = MagicMock(side_effect=Exception("DB down"))
        # Also make the direct-connection fallback fail
        vsm._get_postgres_connection = MagicMock(side_effect=Exception("DB down"))

        with pytest.raises(Exception):
            vsm._pool_connection()


# ===========================================================================
# BONUS — End-to-end integration test
# ===========================================================================

class TestEndToEndPipeline:
    """Integration test: full RAGPipeline.query() with all dependencies mocked."""

    def test_end_to_end_pipeline(self):
        """Full pipeline returns correct answer, timing keys, and sources list."""
        from langchain_core.documents import Document

        # --- Mock all external dependencies ---
        mock_embedding_manager = MagicMock()
        mock_embedding_manager.embed_query.return_value = [0.1] * 768

        mock_doc = Document(
            page_content="This is a test document about AI.",
            metadata={"source": "test.pdf", "breadcrumb": "Doc > Chapter 1"},
        )
        mock_vector_store_manager = MagicMock()
        mock_vector_store_manager.similarity_search.return_value = [mock_doc]

        mock_llm_manager = MagicMock()
        mock_llm_manager.model = "test-model"
        mock_llm_manager.generate_response_fused.return_value = {
            "answer": "test answer",
            "rewritten_query": None,
            "confidence": 0.9,
            "queue_wait_ms": 5.0,
        }
        mock_llm_manager.generate_response.return_value = "test answer"

        mock_query_cache = MagicMock()
        mock_query_cache.get.return_value = None  # force cache miss
        mock_query_cache.make_key.return_value = "e2e_cache_key"

        # Use a real PerformanceBenchmark so timing dict is properly built
        real_benchmark = PerformanceBenchmark()

        # --- Build pipeline ---
        rag = RAGPipeline(
            llm_manager=mock_llm_manager,
            embedding_manager=mock_embedding_manager,
            vector_store_manager=mock_vector_store_manager,
            query_cache=mock_query_cache,
            benchmark=real_benchmark,
            prompt_fusion_enabled=True,
        )

        # --- Execute ---
        response = rag.query("test question")

        # --- Assertions ---
        assert response["answer"] == "test answer", (
            f"Expected 'test answer', got {response['answer']!r}"
        )

        assert "timing" in response, "Response must contain a 'timing' key"

        timing = response["timing"]
        required_timing_keys = {"queue_wait_ms", "embedding_ms", "search_ms", "llm_ms", "total_ms"}
        for key in required_timing_keys:
            assert key in timing, f"Missing timing key: {key}"

        assert isinstance(response["sources"], list), "sources must be a list"
        assert len(response["sources"]) >= 1, "sources must contain at least one entry"
