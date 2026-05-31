"""
Background task executor for post-response processing.

After the LLM answer has been returned to the user, tasks such as rolling-summary
update and user-memory extraction are submitted here so they run in background
threads without blocking the next user query.
"""
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Default timeout (seconds) before a background task is considered hung.
_DEFAULT_TIMEOUT_S = 60


class PostResponseTaskExecutor:
    """Submit fire-and-forget background tasks after the RAG answer is delivered.

    Tasks run in a shared :class:`~concurrent.futures.ThreadPoolExecutor`.
    Exceptions raised inside tasks are caught and logged at ERROR level so they
    never crash the main Streamlit thread.

    Args:
        timeout_seconds: Maximum wall-clock time (seconds) a task may run before
                         it is considered timed-out and a WARNING is logged.
                         The task is not forcibly killed (Python threads cannot be
                         killed externally), but the executor stops waiting for it.
        max_workers:     Maximum number of background threads.  Defaults to 4.
    """

    def __init__(
        self,
        timeout_seconds: int = _DEFAULT_TIMEOUT_S,
        max_workers: int = 4,
    ) -> None:
        self._timeout = timeout_seconds
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="post_response",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        task_name: str = "background_task",
        **kwargs: Any,
    ) -> None:
        """Submit ``fn(*args, **kwargs)`` to run in a background thread.

        Returns immediately — the caller does not wait for the task to finish.

        If the task raises an exception it is logged at ERROR level.
        If the task exceeds ``timeout_seconds`` a WARNING is logged.

        Args:
            fn:        The callable to execute in the background.
            *args:     Positional arguments forwarded to ``fn``.
            task_name: Human-readable label used in log messages.
            **kwargs:  Keyword arguments forwarded to ``fn``.
        """
        future: Future = self._executor.submit(fn, *args, **kwargs)
        # Attach a done-callback to handle errors and timeouts asynchronously.
        future.add_done_callback(
            lambda f: self._handle_done(f, task_name)
        )
        # Also schedule a timeout watcher in a separate thread so we can log
        # if the task runs too long without blocking the caller.
        self._executor.submit(self._watch_timeout, future, task_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _handle_done(future: Future, task_name: str) -> None:
        """Callback invoked when a background task completes (success or failure)."""
        exc = future.exception()
        if exc is not None:
            logger.error(
                "[post_response] Task '%s' raised an exception: %s",
                task_name,
                exc,
                exc_info=exc,
            )
        else:
            logger.debug("[post_response] Task '%s' completed successfully.", task_name)

    def _watch_timeout(self, future: Future, task_name: str) -> None:
        """Wait for ``future`` up to ``timeout_seconds``; log WARNING if it times out."""
        try:
            future.result(timeout=self._timeout)
        except FuturesTimeoutError:
            logger.warning(
                "[post_response] Task '%s' exceeded timeout of %d s.",
                task_name,
                self._timeout,
            )
        except Exception:
            # Exception already handled by _handle_done callback.
            pass

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the executor, optionally waiting for pending tasks."""
        self._executor.shutdown(wait=wait)
