"""
Data models for the RAG performance optimisation layer.

Defines:
  - TimingBreakdown  — per-step latency measurements returned in every query response.
  - FusedLLMResponse — structured output from the Prompt-Fusion LLM call.
  - CacheEntry       — a single TTL-aware entry stored in QueryCache.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import re
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TimingBreakdown
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class TimingBreakdown:
    """Latency (ms) for each step of the RAG query pipeline.

    All fields default to 0.0 so callers can populate only the steps that ran.
    """

    embedding_ms: float = 0.0
    """Time spent embedding the query vector."""

    search_ms: float = 0.0
    """Time spent executing the hybrid search SQL query."""

    llm_ms: float = 0.0
    """Time spent waiting for the LLM to generate the full response."""

    queue_wait_ms: float = 0.0
    """Time the request spent waiting in the LLM semaphore queue before being served."""

    ttft_ms: float = 0.0
    """Time To First Token — elapsed time until the first streaming token was emitted."""

    total_ms: float = 0.0
    """End-to-end wall-clock time from query receipt to answer delivery."""

    def to_dict(self) -> dict[str, float]:
        """Return a plain dict suitable for JSON serialisation."""
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# FusedLLMResponse
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class FusedLLMResponse:
    """Structured output produced by the Prompt-Fusion LLM call.

    The LLM is instructed to return JSON in the shape::

        {
            "answer": "...",
            "rewritten_query": "...",   # optional
            "confidence": 0.92          # optional float 0–1
        }

    If the LLM deviates from this format, :meth:`from_json` falls back to
    treating the entire raw text as the answer.
    """

    answer: str
    rewritten_query: Optional[str] = None
    confidence: Optional[float] = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    # Regex to extract the "answer" value from malformed/truncated JSON
    _ANSWER_REGEX = re.compile(r'"answer"\s*:\s*"((?:[^"\\]|\\.)+)"', re.DOTALL)

    @classmethod
    def _strip_code_fence(cls, text: str) -> str:
        """Remove markdown code fences (```json ... ``` or ``` ... ```)."""
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            # Drop first line (```json or ```) and last line (```)
            stripped = "\n".join(lines[1:-1]).strip()
        return stripped

    @classmethod
    def _clean_json_artifacts(cls, text: str) -> str:
        """Remove JSON syntax artifacts from a plain-text fallback.

        Strips code fences, then removes leading/trailing JSON structure
        characters so the caller receives readable Vietnamese text rather
        than raw JSON fragments.
        """
        cleaned = cls._strip_code_fence(text)

        # If the text looks like a JSON object, try to extract the "answer" field
        # using a regex before giving up and returning a default message.
        if cleaned.startswith("{") or '"answer":' in cleaned:
            match = cls._ANSWER_REGEX.search(cleaned)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 10:
                    return extracted
            # Could not extract meaningful content — return default message
            return "Không đủ thông tin để trả lời câu hỏi này."

        return cleaned

    @classmethod
    def from_json(cls, raw: str) -> "FusedLLMResponse":
        """Parse the LLM's raw output as JSON.

        Falls back to :meth:`from_raw_text` (and logs a WARNING) if:
        - ``raw`` is not valid JSON
        - the parsed object is not a dict
        - the ``"answer"`` key is missing or empty

        When JSON parse fails, attempts to extract the ``answer`` value via
        regex before falling back to :meth:`from_raw_text`.
        """
        cleaned = cls._strip_code_fence(raw)

        try:
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "FusedLLMResponse: JSON parse failed — attempting regex extraction. "
                "Raw output (first 200 chars): %r",
                raw[:200],
            )
            # Try to extract "answer" value from malformed JSON via regex
            match = cls._ANSWER_REGEX.search(cleaned)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 10:
                    logger.debug(
                        "FusedLLMResponse: regex extracted answer (%d chars).", len(extracted)
                    )
                    return cls(answer=extracted)
            return cls.from_raw_text(raw)

        if not isinstance(parsed, dict):
            logger.warning(
                "FusedLLMResponse: expected a JSON object, got %s — falling back to raw text.",
                type(parsed).__name__,
            )
            return cls.from_raw_text(raw)

        answer = str(parsed.get("answer", "")).strip()
        if not answer:
            logger.warning(
                "FusedLLMResponse: 'answer' field missing or empty — falling back to raw text."
            )
            return cls.from_raw_text(raw)

        rewritten_query: Optional[str] = parsed.get("rewritten_query") or None
        if rewritten_query:
            rewritten_query = str(rewritten_query).strip() or None

        raw_confidence = parsed.get("confidence")
        confidence: Optional[float] = None
        if raw_confidence is not None:
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = None

        return cls(
            answer=answer,
            rewritten_query=rewritten_query,
            confidence=confidence,
        )

    @classmethod
    def from_raw_text(cls, text: str) -> "FusedLLMResponse":
        """Treat ``text`` as the answer after cleaning JSON artifacts.

        Strips code fences and JSON fragment patterns so the user never sees
        raw ``{"answer":`` syntax or bare breadcrumb strings as the answer.
        If no meaningful content remains after cleanup, returns a default
        "không đủ thông tin" message.
        """
        cleaned = cls._clean_json_artifacts(text)
        if not cleaned:
            cleaned = "Không đủ thông tin để trả lời câu hỏi này."
        return cls(answer=cleaned)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict for inclusion in the query response."""
        return {
            "answer": self.answer,
            "rewritten_query": self.rewritten_query,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class CacheEntry:
    """A single TTL-aware entry stored in :class:`~src.rag.query_cache.QueryCache`.

    Args:
        value:     The cached payload (typically the full query response dict).
        expire_at: Unix timestamp (seconds) after which this entry is considered stale.
    """

    value: Any
    expire_at: float

    def is_expired(self) -> bool:
        """Return ``True`` if the current wall-clock time has passed ``expire_at``."""
        return time.time() > self.expire_at
