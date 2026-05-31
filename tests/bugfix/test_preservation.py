"""
Preservation Property Tests
============================
Spec: .kiro/specs/rag-chatbot-response-quality-fix/

These tests capture the CORRECT baseline behavior that MUST NOT change after
the fix is applied.  All 5 tests are expected to PASS on the current (unfixed)
code.

Property 2a — Valid JSON preservation:
    FusedLLMResponse.from_json() correctly parses valid JSON with a non-empty answer.

Property 2b — Code fence stripping preservation:
    JSON wrapped in markdown code fences is still parsed correctly.

Property 2c — Classic flow preservation:
    query_stream() with prompt_fusion_enabled=False streams tokens directly
    without JSON parsing.

Property 2d — Cache hit preservation:
    query_stream() with a cache hit yields words from the cached answer WITHOUT
    acquiring the semaphore.

Property 2e — Semaphore blocking preservation:
    With 2 concurrent requests holding the semaphore, a 3rd request is properly
    blocked/rejected.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**
"""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from src.llm.llm_manager import LLMManager
from src.rag.exceptions import LLMQueueFullError, LLMTimeoutError
from src.rag.models import FusedLLMResponse
from src.rag.rag_pipeline import RAGPipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_doc() -> Document:
    """Return a minimal fake Document for mocking similarity_search."""
    return Document(
        page_content="Nội dung tài liệu giả để kiểm tra.",
        metadata={"breadcrumb": "Chương 1 > Điều 1"},
    )


def _make_rag(
    llm_manager: LLMManager,
    mock_vsm: MagicMock,
    mock_cache: MagicMock,
    prompt_fusion_enabled: bool = False,
) -> RAGPipeline:
    """Create a RAGPipeline wired to the given mocks."""
    return RAGPipeline(
        llm_manager=llm_manager,
        vector_store_manager=mock_vsm,
        query_cache=mock_cache,
        prompt_fusion_enabled=prompt_fusion_enabled,
    )


# ---------------------------------------------------------------------------
# TestPreservation
# ---------------------------------------------------------------------------


class TestPreservation:
    """Preservation tests — all must PASS on unfixed code."""

    # ------------------------------------------------------------------
    # Property 2a — Valid JSON preservation
    # ------------------------------------------------------------------

    def test_2a_valid_json_no_rewritten_query(self):
        """
        Property 2a: from_json() correctly parses valid JSON with a non-empty answer
        and rewritten_query=null.

        **Validates: Requirements 3.2, 3.6**
        """
        raw = (
            '{"answer": "Theo Điều 5, người lao động có quyền nghỉ phép hàng năm...", '
            '"rewritten_query": null, "confidence": 0.9}'
        )
        result = FusedLLMResponse.from_json(raw)

        assert result.answer == "Theo Điều 5, người lao động có quyền nghỉ phép hàng năm...", (
            f"Property 2a: answer mismatch. Got: {result.answer!r}"
        )
        assert result.rewritten_query is None, (
            f"Property 2a: rewritten_query should be None. Got: {result.rewritten_query!r}"
        )
        assert result.confidence == 0.9, (
            f"Property 2a: confidence mismatch. Got: {result.confidence!r}"
        )

    def test_2a_valid_json_with_rewritten_query(self):
        """
        Property 2a: from_json() correctly parses valid JSON with a non-empty answer
        and a rewritten_query present.

        **Validates: Requirements 3.2, 3.6**
        """
        raw = (
            '{"answer": "Nội dung đầy đủ về quyền lao động...", '
            '"rewritten_query": "câu hỏi đã mở rộng", "confidence": 0.85}'
        )
        result = FusedLLMResponse.from_json(raw)

        assert result.answer == "Nội dung đầy đủ về quyền lao động...", (
            f"Property 2a: answer mismatch. Got: {result.answer!r}"
        )
        assert result.rewritten_query == "câu hỏi đã mở rộng", (
            f"Property 2a: rewritten_query mismatch. Got: {result.rewritten_query!r}"
        )
        assert result.confidence == 0.85, (
            f"Property 2a: confidence mismatch. Got: {result.confidence!r}"
        )

    # ------------------------------------------------------------------
    # Property 2b — Code fence stripping preservation
    # ------------------------------------------------------------------

    def test_2b_code_fence_stripping(self):
        """
        Property 2b: JSON wrapped in markdown code fences is still parsed correctly.

        **Validates: Requirements 3.2, 3.6**
        """
        raw = (
            '```json\n'
            '{"answer": "Nội dung đầy đủ về quyền lao động...", '
            '"rewritten_query": "câu hỏi mở rộng"}\n'
            '```'
        )
        result = FusedLLMResponse.from_json(raw)

        assert result.answer == "Nội dung đầy đủ về quyền lao động...", (
            f"Property 2b: answer mismatch after code fence strip. Got: {result.answer!r}"
        )
        assert result.rewritten_query == "câu hỏi mở rộng", (
            f"Property 2b: rewritten_query mismatch. Got: {result.rewritten_query!r}"
        )
        assert result.confidence is None, (
            f"Property 2b: confidence should be None (not in JSON). Got: {result.confidence!r}"
        )

    # ------------------------------------------------------------------
    # Property 2c — Classic flow preservation
    # ------------------------------------------------------------------

    def test_2c_classic_flow_streams_tokens_directly(self):
        """
        Property 2c: query_stream() with prompt_fusion_enabled=False streams tokens
        directly from llm_manager.stream() without JSON parsing.

        **Validates: Requirements 3.1, 3.3**
        """
        mock_tokens = ["Đây ", "là ", "câu ", "trả ", "lời."]

        llm_manager = LLMManager(max_concurrent_calls=2)
        fake_doc = _make_fake_doc()

        mock_vsm = MagicMock()
        mock_vsm.similarity_search.return_value = [fake_doc]

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # cache miss
        mock_cache.make_key.return_value = "test-cache-key-2c"

        rag = _make_rag(
            llm_manager=llm_manager,
            mock_vsm=mock_vsm,
            mock_cache=mock_cache,
            prompt_fusion_enabled=False,
        )

        # Patch llm_manager.stream() to yield our mock tokens
        with patch.object(llm_manager, "stream", return_value=iter(mock_tokens)):
            tokens: List[str] = list(rag.query_stream("câu hỏi kiểm tra"))

        # The collected tokens must contain the mocked stream output
        joined = "".join(tokens)
        for expected_word in mock_tokens:
            assert expected_word.strip() in joined, (
                f"Property 2c: expected token {expected_word!r} not found in output.\n"
                f"  Collected tokens: {tokens!r}\n"
                f"  Joined: {joined!r}"
            )

    # ------------------------------------------------------------------
    # Property 2d — Cache hit preservation
    # ------------------------------------------------------------------

    def test_2d_cache_hit_does_not_acquire_semaphore(self):
        """
        Property 2d: query_stream() with a cache hit yields words from the cached
        answer WITHOUT acquiring the semaphore.

        **Validates: Requirements 3.4**
        """
        cached_answer = "Câu trả lời đã cache."
        cached_response = {
            "answer": cached_answer,
            "sources": [],
            "context": "",
            "rewritten_query": None,
            "timing": {},
        }

        llm_manager = LLMManager(max_concurrent_calls=2)
        semaphore = llm_manager._semaphore

        mock_vsm = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_response  # cache HIT
        mock_cache.make_key.return_value = "test-cache-key-2d"

        rag = _make_rag(
            llm_manager=llm_manager,
            mock_vsm=mock_vsm,
            mock_cache=mock_cache,
            prompt_fusion_enabled=True,  # even with fusion enabled, cache hit skips LLM
        )

        slots_before = semaphore._value
        tokens: List[str] = list(rag.query_stream("câu hỏi đã cache"))
        slots_after = semaphore._value

        # Semaphore must NOT have been acquired
        assert slots_before == slots_after, (
            f"Property 2d: semaphore was acquired during cache hit.\n"
            f"  slots_before={slots_before}, slots_after={slots_after}"
        )

        # The yielded tokens must contain the cached answer
        joined = "".join(tokens).strip()
        assert "Câu trả lời đã cache" in joined, (
            f"Property 2d: cached answer not found in yielded tokens.\n"
            f"  Joined tokens: {joined!r}"
        )

    # ------------------------------------------------------------------
    # Property 2e — Semaphore blocking preservation
    # ------------------------------------------------------------------

    def test_2e_semaphore_blocking_rejects_third_request(self):
        """
        Property 2e: With 2 concurrent requests holding the semaphore, a 3rd request
        is properly blocked/rejected — either LLMQueueFullError is raised or an error
        token containing '❌' is yielded.

        **Validates: Requirements 3.5**
        """
        llm_manager = LLMManager(max_concurrent_calls=2, max_queue_size=1)
        semaphore = llm_manager._semaphore

        # Manually acquire both semaphore slots to simulate 2 active requests
        acquired_1 = semaphore.acquire(blocking=False)
        acquired_2 = semaphore.acquire(blocking=False)
        assert acquired_1 and acquired_2, "Could not acquire both semaphore slots for test setup"

        # Also fill the queue to simulate a full queue
        with llm_manager._queue_lock:
            llm_manager._queue_count = llm_manager.max_queue_size

        fake_doc = _make_fake_doc()
        mock_vsm = MagicMock()
        mock_vsm.similarity_search.return_value = [fake_doc]

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # cache miss
        mock_cache.make_key.return_value = "test-cache-key-2e"

        rag = _make_rag(
            llm_manager=llm_manager,
            mock_vsm=mock_vsm,
            mock_cache=mock_cache,
            prompt_fusion_enabled=True,
        )

        error_raised = False
        error_token_yielded = False
        tokens: List[str] = []

        try:
            for token in rag.query_stream("câu hỏi thứ 3"):
                tokens.append(token)
                if "❌" in token:
                    error_token_yielded = True
        except (LLMQueueFullError, LLMTimeoutError):
            error_raised = True
        finally:
            # Always release the manually acquired slots
            semaphore.release()
            semaphore.release()
            # Reset queue count
            with llm_manager._queue_lock:
                llm_manager._queue_count = 0

        assert error_raised or error_token_yielded, (
            f"Property 2e: expected LLMQueueFullError/LLMTimeoutError or an error token "
            f"containing '❌', but neither occurred.\n"
            f"  error_raised={error_raised}, error_token_yielded={error_token_yielded}\n"
            f"  Collected tokens: {tokens!r}"
        )
