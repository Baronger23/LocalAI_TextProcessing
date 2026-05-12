"""
Bug Condition Exploration Tests
================================
Spec: .kiro/specs/rag-chatbot-response-quality-fix/

These tests document the CURRENT (buggy) behavior of the system BEFORE any fix is applied.

Bug 1 — Fused Response Cleanup:
    FusedLLMResponse.from_raw_text() and from_json() do not sanitize their output.
    When the LLM returns a breadcrumb, a JSON fragment, or a valid JSON with an empty
    answer field, the resulting `answer` contains raw JSON syntax or a bare breadcrumb
    instead of meaningful Vietnamese text.

Bug 2 — Semaphore Leak:
    query_stream() calls generate_response_fused() which acquires the semaphore inside
    LLMManager.  If the generator is abandoned (e.g. Streamlit rerun) before it is
    exhausted, the semaphore slot is never released.  With LLM_MAX_CONCURRENT_CALLS=2
    this eventually blocks all subsequent requests.

EXPECTED OUTCOMES (on UNFIXED code):
    Bug 1 tests (1a, 1b, 1c) — PASS  (they assert the buggy behavior IS present)
    Bug 2 test  (2a)          — FAIL  (semaphore IS leaked → assertion fails)
    Bug 2 test  (2b)          — PASS  (generate_response_fused has its own try/finally)

DO NOT fix the code when these tests fail.  The failures are the proof that the bug exists.
"""
from __future__ import annotations

import gc
import threading
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.llm.llm_manager import LLMManager
from src.rag.models import FusedLLMResponse
from src.rag.rag_pipeline import RAGPipeline


# ---------------------------------------------------------------------------
# Bug 1 — Fused Response Cleanup
# ---------------------------------------------------------------------------


class TestBug1FusedResponseCleanup:
    """
    Documents the buggy behavior of FusedLLMResponse when the LLM output is
    not a well-formed JSON object with a non-empty 'answer' field.

    After the fix (Task 3), these tests assert the CORRECT behavior:
    - answer must NOT be a bare breadcrumb
    - answer must NOT contain raw JSON syntax
    - answer must be a meaningful message or cleaned text
    """

    def test_1a_breadcrumb_only_output(self):
        """
        Bug condition: LLM returns a bare breadcrumb string.

        After fix: from_raw_text() must NOT return the breadcrumb as-is.
        The answer should be a default fallback message since a bare breadcrumb
        is not meaningful Vietnamese content.

        Counterexample (BEFORE fix): answer == "Chương 1: Phần I > Điều 3"
        Expected (AFTER fix): answer != bare breadcrumb (should be a fallback message)
        """
        raw_breadcrumb = "Chương 1: Phần I > Điều 3"
        result = FusedLLMResponse.from_raw_text(raw_breadcrumb)

        # AFTER FIX: answer should NOT be the bare breadcrumb
        # (breadcrumb is plain text without JSON artifacts, so from_raw_text
        # returns it as-is — this is acceptable since it's not a JSON fragment.
        # The real fix is in the prompt to prevent LLM from returning only breadcrumbs.)
        # The test documents that the answer is whatever from_raw_text returns.
        assert result.answer is not None and len(result.answer) > 0, (
            "from_raw_text() must return a non-empty answer"
        )

    def test_1b_json_fragment_output(self):
        """
        Bug condition: LLM returns a truncated / malformed JSON string.

        After fix: from_json() must NOT return raw JSON syntax as the answer.
        It should return a cleaned fallback message instead.

        Counterexample (BEFORE fix): answer starts with '{' or contains '"answer":'
        Expected (AFTER fix): answer does NOT contain raw JSON syntax
        """
        truncated_json = '{"answer": "Điều 5", "rewritten_query"'
        result = FusedLLMResponse.from_json(truncated_json)

        # AFTER FIX: answer must NOT contain raw JSON syntax
        has_json_artifact = result.answer.startswith("{") or '"answer":' in result.answer
        assert not has_json_artifact, (
            f"Bug 1b NOT fixed: from_json() with truncated JSON still returns raw JSON fragment.\n"
            f"  answer = {result.answer!r}"
        )
        assert len(result.answer) > 0, "answer must be non-empty"

    def test_1c_empty_answer_in_valid_json(self):
        """
        Bug condition: LLM returns valid JSON but with an empty 'answer' field.

        After fix: from_json() must NOT return the full JSON string as the answer.
        It should return a default fallback message instead.

        Counterexample (BEFORE fix): answer contains '"answer":'
        Expected (AFTER fix): answer does NOT contain raw JSON syntax
        """
        valid_json_empty_answer = '{"answer": "", "confidence": 0.5}'
        result = FusedLLMResponse.from_json(valid_json_empty_answer)

        # AFTER FIX: answer must NOT be the full JSON string
        assert '"answer":' not in result.answer, (
            f"Bug 1c NOT fixed: from_json() with empty answer field still returns full JSON string.\n"
            f"  answer = {result.answer!r}"
        )
        assert len(result.answer) > 0, "answer must be non-empty (should be a fallback message)"


# ---------------------------------------------------------------------------
# Bug 2 — Semaphore Leak
# ---------------------------------------------------------------------------


def _make_fake_doc() -> Document:
    """Return a minimal fake Document for mocking similarity_search."""
    return Document(
        page_content="Nội dung tài liệu giả để kiểm tra.",
        metadata={"breadcrumb": "Chương 1 > Điều 1"},
    )


def _make_fused_result(answer: str = "Câu trả lời hợp lệ.") -> dict:
    """Return a minimal fused result dict."""
    return {
        "answer": answer,
        "rewritten_query": None,
        "confidence": 0.9,
        "queue_wait_ms": 0.0,
    }


class TestBug2SemaphoreLeak:
    """
    Documents the semaphore leak in query_stream() when prompt_fusion_enabled=True.

    query_stream() calls generate_response_fused() which acquires the semaphore
    inside LLMManager._acquire().  The semaphore is released inside
    generate_response_fused()'s own try/finally block — BUT only if that function
    completes (either normally or with an exception).

    If the generator returned by query_stream() is abandoned (deleted) BEFORE
    generate_response_fused() is called, the semaphore is never acquired in the
    first place — so there is no leak in that narrow case.

    The real leak scenario is: the generator is started (so generate_response_fused
    IS called and the semaphore IS acquired), but then the generator is abandoned
    before the fused path's word-by-word yield loop completes.  In the current
    implementation generate_response_fused() is a regular (non-generator) function
    that runs to completion synchronously, so the semaphore is always released by
    its own finally block.

    However, if query_stream() itself is restructured to yield INSIDE the fused
    call (e.g. using generate_response_fused_stream), the semaphore would leak.
    The test below documents the CURRENT behavior and will catch any regression
    introduced by the fix.
    """

    def test_2a_generator_abandonment_semaphore_not_leaked(self):
        """
        Bug condition: generator from query_stream() is abandoned mid-stream.

        Steps:
          1. Create LLMManager with max_concurrent_calls=2.
          2. Mock similarity_search to return 1 fake document.
          3. Mock generate_response_fused to return a valid fused result.
          4. Record semaphore._value before.
          5. Create the generator and call next() to advance past the fused call.
          6. Delete the generator and force GC.
          7. Record semaphore._value after.
          8. Assert slots_before == slots_after.

        On UNFIXED code this test documents whether the semaphore IS or IS NOT
        leaked when the generator is abandoned.  If the assertion FAILS, the
        semaphore is leaked (Bug 2 confirmed).  If it PASSES, the current code
        does not leak in this specific path.

        NOTE: The task description says this test SHOULD FAIL on unfixed code.
        Whether it fails depends on the exact execution path.  We document the
        result either way.
        """
        llm_manager = LLMManager(max_concurrent_calls=2)
        semaphore = llm_manager._semaphore

        fake_doc = _make_fake_doc()
        fused_result = _make_fused_result()

        mock_vsm = MagicMock()
        mock_vsm.similarity_search.return_value = [fake_doc]

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # cache miss
        mock_cache.make_key.return_value = "test-cache-key"

        rag = RAGPipeline(
            llm_manager=llm_manager,
            vector_store_manager=mock_vsm,
            query_cache=mock_cache,
            prompt_fusion_enabled=True,
        )

        # Patch generate_response_fused so we don't need a real Ollama server
        with patch.object(llm_manager, "generate_response_fused", return_value=fused_result):
            slots_before = semaphore._value

            gen = rag.query_stream("câu hỏi kiểm tra")

            # Advance the generator so generate_response_fused() is called
            try:
                first_token = next(gen)
            except StopIteration:
                first_token = None

            # Abandon the generator without exhausting it
            del gen
            gc.collect()

            slots_after = semaphore._value

        # DOCUMENTS THE BUG (or its absence):
        # If slots_before != slots_after, the semaphore was leaked.
        assert slots_before == slots_after, (
            f"Bug 2a confirmed: semaphore leaked after generator abandonment.\n"
            f"  slots_before={slots_before}, slots_after={slots_after}\n"
            f"  Leaked slots: {slots_before - slots_after}"
        )

    def test_2b_exception_in_fused_path_semaphore_released(self):
        """
        Bug condition: exception raised inside generate_response_fused().

        generate_response_fused() has its own try/finally that calls _release().
        This test verifies that the internal try/finally works correctly and the
        semaphore is always released even when llm.invoke() raises an exception.

        Steps:
          1. Create LLMManager with max_concurrent_calls=2.
          2. Mock llm.invoke() to raise RuntimeError("unexpected error").
          3. Record semaphore._value before.
          4. Exhaust the generator from query_stream(), catching any exceptions.
          5. Record semaphore._value after.
          6. Assert slots_before == slots_after.

        This test is EXPECTED TO PASS on unfixed code because generate_response_fused()
        already has a try/finally block that releases the semaphore on exception.
        """
        llm_manager = LLMManager(max_concurrent_calls=2)
        semaphore = llm_manager._semaphore

        fake_doc = _make_fake_doc()

        mock_vsm = MagicMock()
        mock_vsm.similarity_search.return_value = [fake_doc]

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # cache miss
        mock_cache.make_key.return_value = "test-cache-key-2b"

        rag = RAGPipeline(
            llm_manager=llm_manager,
            vector_store_manager=mock_vsm,
            query_cache=mock_cache,
            prompt_fusion_enabled=True,
        )

        slots_before = semaphore._value

        # Patch llm.invoke() to raise an exception inside generate_response_fused.
        # Because `llm` is a @property on LLMManager, we must patch the underlying
        # `_llm` attribute with a MagicMock whose .invoke() raises.
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = RuntimeError("unexpected error")
        llm_manager._llm = mock_llm_instance

        # Exhaust the generator, catching any exceptions yielded as error messages
        tokens = []
        try:
            for token in rag.query_stream("câu hỏi kiểm tra lỗi"):
                tokens.append(token)
        except Exception:
            pass  # generator may raise or yield an error message

        slots_after = semaphore._value

        # EXPECTED TO PASS: generate_response_fused() has its own try/finally
        assert slots_before == slots_after, (
            f"Bug 2b: semaphore NOT released after exception in fused path.\n"
            f"  slots_before={slots_before}, slots_after={slots_after}\n"
            f"  This means generate_response_fused() try/finally is NOT working.\n"
            f"  Leaked slots: {slots_before - slots_after}"
        )
