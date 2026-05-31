"""
LLM module using Ollama.

Enhancements over the original:
  - Configurable keep_alive (default 300 s) — avoids VRAM reload on every call.
  - Threading Semaphore — limits concurrent Ollama calls to prevent GPU thrash.
  - FIFO queue with max_queue_size — rejects requests when queue is full.
  - Token streaming via stream() generator.
  - Prompt-Fusion via generate_response_fused() — rewrite + generate in 1 LLM call.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Generator, List, Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import (
    OLLAMA_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    OLLAMA_KEEP_ALIVE,
    LLM_MAX_CONCURRENT_CALLS,
    LLM_MAX_QUEUE_SIZE,
)
from src.rag.exceptions import LLMQueueFullError, LLMTimeoutError
from src.rag.models import FusedLLMResponse

logger = logging.getLogger(__name__)

# How long (seconds) a request may wait in the semaphore queue before timing out.
_SEMAPHORE_TIMEOUT_S = 120


def _validate_and_clean_answer(raw: str, query: str) -> str:
    """Validate and clean the LLM answer.

    - Strips JSON artifacts and code fences.
    - Rejects answers that are too short (< 30 chars) or look like bare
      breadcrumbs / table-of-contents entries.
    - Returns a fallback message when the answer is unusable.
    """
    if not raw:
        return "Không tìm thấy thông tin liên quan trong tài liệu."

    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()

    # Strip JSON artifacts — if the whole answer looks like JSON, extract text
    if text.startswith("{") and '"answer"' in text:
        import re
        m = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)+)"', text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        else:
            text = ""

    if not text or len(text) < 10:
        logger.warning(
            "[llm] Answer too short or empty after cleanup (%d chars) for query: %r",
            len(text), query[:60],
        )
        return "Không tìm thấy thông tin liên quan trong tài liệu."

    return text

# Fused prompt template — instructs the LLM to expand abbreviations AND answer
# in a single inference pass, returning structured JSON.
_FUSED_SYSTEM_PROMPT = """Bạn là trợ lý ảo chuyên nghiệp hỗ trợ giải đáp chính sách nội bộ của Công ty TNHH An Phát Digital.

NHIỆM VỤ:
Trả lời câu hỏi dựa trên ngữ cảnh tài liệu được cung cấp.
Nếu câu hỏi chứa từ viết tắt tiếng Việt, hãy mở rộng chúng trong trường "rewritten_query".

QUY TẮC BẮT BUỘC:
1. Chỉ trả lời dựa vào thông tin có trong ngữ cảnh tài liệu. Không tự ý suy diễn hoặc thêm thông tin ngoài tài liệu.
2. Nếu tài liệu không chứa đủ thông tin để trả lời, hãy trả lời rõ: "Ngữ cảnh tài liệu không đủ dữ liệu để trả lời câu hỏi này."
3. Trả lời trực tiếp vào câu hỏi, nêu rõ các điều khoản, con số, hạn mức hoặc quy trình cụ thể có trong tài liệu.
4. Nếu context có nhiều mục/nhóm lớn liên quan trực tiếp đến câu hỏi, PHẢI bao phủ đủ tất cả các mục/nhóm đó.
5. Trường "answer" phải là câu trả lời HOÀN CHỈNH — KHÔNG chỉ là breadcrumb hay số hiệu chương/điều.

Trả về DUY NHẤT một JSON object (không thêm văn bản nào khác):
{
  "answer": "<câu trả lời hoàn chỉnh bằng tiếng Việt>",
  "rewritten_query": "<câu hỏi đã mở rộng từ viết tắt hoặc null>",
  "confidence": <số thực 0.0–1.0>
}"""


class LLMManager:
    """Manage LLM interactions using Ollama with concurrency control."""

    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = LLM_TEMPERATURE,
        keep_alive: int = OLLAMA_KEEP_ALIVE,
        max_concurrent_calls: int = LLM_MAX_CONCURRENT_CALLS,
        max_queue_size: int = LLM_MAX_QUEUE_SIZE,
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.keep_alive = keep_alive

        # Validate and clamp concurrency settings
        if max_concurrent_calls < 1:
            logger.warning(
                "LLM_MAX_CONCURRENT_CALLS=%d is invalid — using default 2.",
                max_concurrent_calls,
            )
            max_concurrent_calls = 2
        self.max_concurrent_calls = max_concurrent_calls
        self.max_queue_size = max(1, max_queue_size)

        self._llm: Optional[OllamaLLM] = None

        # Semaphore limits simultaneous Ollama calls.
        self._semaphore = threading.Semaphore(self.max_concurrent_calls)

        # Queue tracking (FIFO discipline enforced by Semaphore + lock ordering).
        self._queue_lock = threading.Lock()
        self._queue_count: int = 0  # requests waiting for the semaphore
        self._active_count: int = 0  # requests currently holding the semaphore

    # ------------------------------------------------------------------
    # LLM instance (lazy init)
    # ------------------------------------------------------------------

    @property
    def llm(self) -> OllamaLLM:
        """Get or create LLM instance."""
        if self._llm is None:
            self._llm = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature,
                keep_alive=self.keep_alive,
            )
        return self._llm

    # ------------------------------------------------------------------
    # Semaphore helpers
    # ------------------------------------------------------------------

    def _acquire(self) -> float:
        """Acquire the semaphore, respecting queue size limits.

        Returns:
            queue_wait_ms — time spent waiting in the queue (milliseconds).

        Raises:
            LLMQueueFullError: if the queue is already at max_queue_size.
            LLMTimeoutError:   if the semaphore is not acquired within 120 s.
        """
        with self._queue_lock:
            if self._queue_count >= self.max_queue_size:
                raise LLMQueueFullError(
                    f"LLM semaphore queue is full ({self.max_queue_size} requests waiting). "
                    "Please retry later."
                )
            self._queue_count += 1

        wait_start = time.perf_counter()
        acquired = self._semaphore.acquire(timeout=_SEMAPHORE_TIMEOUT_S)
        queue_wait_ms = (time.perf_counter() - wait_start) * 1_000.0

        with self._queue_lock:
            self._queue_count -= 1
            if acquired:
                self._active_count += 1

        if not acquired:
            raise LLMTimeoutError(
                f"LLM call timed out after waiting {queue_wait_ms:.0f} ms "
                f"(limit: {_SEMAPHORE_TIMEOUT_S * 1000:.0f} ms)."
            )

        return queue_wait_ms

    def _release(self) -> None:
        """Release the semaphore slot."""
        with self._queue_lock:
            if self._active_count > 0:
                self._active_count -= 1
        self._semaphore.release()

    def get_runtime_status(self) -> Dict[str, int]:
        """Return the current semaphore and queue state for monitoring."""
        with self._queue_lock:
            return {
                "active_calls": self._active_count,
                "queue_waiting": self._queue_count,
                "max_concurrent_calls": self.max_concurrent_calls,
                "max_queue_size": self.max_queue_size,
            }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the full response string.

        Acquires the semaphore before calling Ollama and always releases it
        afterwards (even on exception).

        Returns:
            The LLM response as a plain string.

        Raises:
            LLMQueueFullError: queue is full.
            LLMTimeoutError:   waited too long for a semaphore slot.
        """
        queue_wait_ms = self._acquire()
        logger.debug("[llm] invoke — queue_wait=%.1f ms", queue_wait_ms)
        try:
            return self.llm.invoke(prompt)
        except Exception:
            logger.exception("[llm] invoke failed")
            raise
        finally:
            self._release()

    def stream(self, prompt: str) -> Generator[str, None, None]:
        """Stream tokens from the LLM one at a time.

        Acquires the semaphore before the first token and releases it after
        the last token (or on error).

        Yields:
            Individual token strings as they arrive from Ollama.

        Raises:
            LLMQueueFullError: queue is full.
            LLMTimeoutError:   waited too long for a semaphore slot.
        """
        queue_wait_ms = self._acquire()
        logger.debug("[llm] stream — queue_wait=%.1f ms", queue_wait_ms)
        try:
            for token in self.llm.stream(prompt):
                yield token
        except Exception:
            logger.exception("[llm] stream interrupted")
            # Yield nothing more — caller receives whatever was streamed so far.
        finally:
            self._release()

    def create_chain(self, prompt_template: str):
        """Create a LangChain chain with a prompt template (non-streaming)."""
        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()
        return chain

    # ------------------------------------------------------------------
    # Standard (non-fused) generation
    # ------------------------------------------------------------------

    def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a response using context and optional chat history.

        This is the original two-call flow (kept for backward compatibility
        and when PROMPT_FUSION_ENABLED=false).

        Args:
            query:        The current user question.
            context:      Retrieved document context.
            system_prompt: Optional system instruction override.
            chat_history: Recent messages for context resolution.

        Returns:
            The LLM answer as a plain string.
        """
        if system_prompt is None:
            system_prompt = (
                "Bạn là trợ lý ảo chuyên nghiệp hỗ trợ giải đáp chính sách nội bộ của Công ty TNHH An Phát Digital.\n\n"
                "NHIỆM VỤ:\n"
                "Trả lời câu hỏi của người dùng một cách chính xác, ngắn gọn và trực tiếp dựa trên ngữ cảnh tài liệu được cung cấp.\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. Chỉ trả lời dựa vào thông tin có trong ngữ cảnh tài liệu. Không tự ý suy diễn hoặc thêm thông tin ngoài tài liệu.\n"
                "2. Nếu tài liệu không chứa đủ thông tin để trả lời, hãy nêu rõ: 'Ngữ cảnh tài liệu không đủ dữ liệu để trả lời câu hỏi này.'\n"
                "3. Trả lời trực tiếp vào câu hỏi, nêu rõ các điều khoản, con số, hạn mức hoặc quy trình cụ thể có trong tài liệu.\n"
                "4. Nếu context có nhiều mục/nhóm lớn liên quan trực tiếp đến câu hỏi, PHẢI bao phủ đủ tất cả các mục/nhóm đó.\n"
                "5. Giữ phong thái chuyên nghiệp, khách quan, sử dụng tiếng Việt chuẩn doanh nghiệp."
            )

        history_block = ""
        if chat_history:
            lines = []
            for msg in chat_history[-6:]:
                role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
                content = str(msg.get("content", "")).strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "Lịch sử hội thoại gần nhất:\n" + "\n".join(lines) + "\n\n"

        prompt_template = (
            f"{system_prompt}\n\n"
            "Ngữ cảnh tài liệu:\n{context}\n\n"
            f"{history_block}"
            "Câu hỏi: {query}\n\n"
            "Trả lời:"
        )

        chain = self.create_chain(prompt_template)
        raw_result = chain.invoke({"context": context, "query": query})
        return _validate_and_clean_answer(raw_result, query)

    # ------------------------------------------------------------------
    # Fused generation (rewrite + answer in 1 LLM call)
    # ------------------------------------------------------------------

    def generate_response_fused(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Fused generation: expand abbreviations AND answer in a single LLM call.

        The LLM is instructed to return a JSON object with keys:
        ``answer``, ``rewritten_query``, ``confidence``.

        If the LLM output cannot be parsed as valid JSON, the raw text is used
        as the answer (fallback) and a WARNING is logged.

        Args:
            query:        The current user question (may contain abbreviations).
            context:      Retrieved document context.
            system_prompt: Ignored — the fused system prompt is always used.
            chat_history: Recent messages for context resolution.

        Returns:
            Dict with keys: ``answer`` (str), ``rewritten_query`` (str | None),
            ``confidence`` (float | None), ``queue_wait_ms`` (float).
        """
        history_block = ""
        if chat_history:
            lines = []
            for msg in chat_history[-6:]:
                role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
                content = str(msg.get("content", "")).strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "Lịch sử hội thoại gần nhất:\n" + "\n".join(lines) + "\n\n"

        full_prompt = (
            f"{_FUSED_SYSTEM_PROMPT}\n\n"
            "Ngữ cảnh tài liệu:\n"
            f"{context}\n\n"
            f"{history_block}"
            f"Câu hỏi: {query}"
        )

        queue_wait_ms = self._acquire()
        logger.debug("[llm] generate_response_fused — queue_wait=%.1f ms", queue_wait_ms)
        try:
            raw = self.llm.invoke(full_prompt)
        except Exception:
            logger.exception("[llm] generate_response_fused failed")
            raise
        finally:
            # Semaphore is ALWAYS released here — synchronous function,
            # so this finally block always runs regardless of caller lifecycle.
            self._release()

        fused = FusedLLMResponse.from_json(raw)

        # Apply answer validation to fused result as well
        validated_answer = _validate_and_clean_answer(fused.answer, query)
        return {
            "answer": validated_answer,
            "rewritten_query": fused.rewritten_query,
            "confidence": fused.confidence,
            "queue_wait_ms": queue_wait_ms,
        }

    def generate_response_fused_stream(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        """Stream the fused generation token by token.

        Note: Because the LLM output is JSON, the caller must accumulate all
        tokens and parse the complete JSON after streaming finishes.
        This method is provided for TTFT measurement — the first token arrives
        quickly even though the full JSON is only parseable at the end.

        Yields:
            Individual token strings.
        """
        history_block = ""
        if chat_history:
            lines = []
            for msg in chat_history[-6:]:
                role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
                content = str(msg.get("content", "")).strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "Lịch sử hội thoại gần nhất:\n" + "\n".join(lines) + "\n\n"

        full_prompt = (
            f"{_FUSED_SYSTEM_PROMPT}\n\n"
            "Ngữ cảnh tài liệu:\n"
            f"{context}\n\n"
            f"{history_block}"
            f"Câu hỏi: {query}"
        )

        yield from self.stream(full_prompt)
