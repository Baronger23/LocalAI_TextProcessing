"""
Performance benchmarking utilities for the RAG pipeline.

Provides:
  - PerformanceBenchmark — context-manager-based step timer, QPS counter,
    and timing-dict builder.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

# Steps that exceed this threshold trigger a WARNING log.
_SLOW_STEP_THRESHOLD_MS = 5_000.0


class PerformanceBenchmark:
    """Measure per-step latency and track queries-per-second.

    Usage::

        bench = PerformanceBenchmark()

        timings: dict[str, float] = {}

        with bench.measure("embedding") as t:
            vector = embed(query)
        timings["embedding_ms"] = t.elapsed_ms

        bench.record_query()
        print(bench.get_qps())
    """

    def __init__(self, window_seconds: int = 60) -> None:
        self._window_seconds = window_seconds
        # Stores Unix timestamps (float) of recent queries for QPS calculation.
        self._query_timestamps: deque[float] = deque()

    # ------------------------------------------------------------------
    # Step timing
    # ------------------------------------------------------------------

    @contextmanager
    def measure(self, step_name: str) -> Generator["_StepTimer", None, None]:
        """Context manager that measures the wall-clock time of a pipeline step.

        Logs the elapsed time at DEBUG level on exit.
        Logs a WARNING if the step exceeds ``_SLOW_STEP_THRESHOLD_MS`` (5 000 ms).

        Yields a :class:`_StepTimer` whose ``elapsed_ms`` attribute is populated
        after the ``with`` block exits.

        Example::

            with bench.measure("llm_generation") as t:
                answer = llm.invoke(prompt)
            timing["llm_ms"] = t.elapsed_ms
        """
        timer = _StepTimer(step_name)
        start = time.perf_counter()
        try:
            yield timer
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1_000.0
            timer.elapsed_ms = elapsed_ms

            logger.debug("[benchmark] %s: %.1f ms", step_name, elapsed_ms)

            if elapsed_ms > _SLOW_STEP_THRESHOLD_MS:
                logger.warning(
                    "[benchmark] SLOW STEP — %s took %.1f ms (threshold: %.0f ms)",
                    step_name,
                    elapsed_ms,
                    _SLOW_STEP_THRESHOLD_MS,
                )

    # ------------------------------------------------------------------
    # QPS counter
    # ------------------------------------------------------------------

    def record_query(self) -> None:
        """Record that a query was processed right now.

        Call this once per completed query to keep the rolling-window counter
        accurate.
        """
        now = time.time()
        self._query_timestamps.append(now)
        self._evict_old_timestamps(now)

    def get_qps(self) -> float:
        """Return the number of queries processed per second in the rolling window.

        The window size is ``window_seconds`` (default 60 s).
        Returns 0.0 if no queries have been recorded yet.
        """
        now = time.time()
        self._evict_old_timestamps(now)
        count = len(self._query_timestamps)
        if count == 0:
            return 0.0
        return count / self._window_seconds

    def _evict_old_timestamps(self, now: float) -> None:
        """Remove timestamps older than the rolling window from the left of the deque."""
        cutoff = now - self._window_seconds
        while self._query_timestamps and self._query_timestamps[0] < cutoff:
            self._query_timestamps.popleft()

    # ------------------------------------------------------------------
    # Timing dict builder
    # ------------------------------------------------------------------

    def build_timing_dict(self, timings: dict[str, float]) -> dict[str, Any]:
        """Merge caller-supplied step timings into a standardised timing dict.

        Ensures all required keys are present (defaulting to 0.0) and that
        all values are non-negative floats.

        Required keys: ``embedding_ms``, ``search_ms``, ``llm_ms``,
        ``queue_wait_ms``, ``ttft_ms``, ``total_ms``.

        Args:
            timings: Dict of ``{key: elapsed_ms}`` collected during the query.

        Returns:
            A complete timing dict safe to include in the query response.
        """
        required_keys = (
            "embedding_ms",
            "search_ms",
            "llm_ms",
            "queue_wait_ms",
            "ttft_ms",
            "total_ms",
        )
        result: dict[str, float] = {}
        for key in required_keys:
            raw = timings.get(key, 0.0)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0.0
            result[key] = max(0.0, value)

        return result


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

class _StepTimer:
    """Mutable container populated by :meth:`PerformanceBenchmark.measure`."""

    __slots__ = ("step_name", "elapsed_ms")

    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        self.elapsed_ms: float = 0.0
