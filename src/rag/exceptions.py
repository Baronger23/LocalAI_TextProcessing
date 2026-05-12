"""
Custom exceptions for the RAG performance optimisation layer.
"""


class LLMTimeoutError(Exception):
    """Raised when a request waits longer than the configured timeout (120 s by default)
    for the LLM semaphore to become available.

    This typically means all LLM slots are occupied and the queue is draining slowly.
    Consider increasing ``LLM_MAX_CONCURRENT_CALLS`` or reducing request rate.
    """


class LLMQueueFullError(Exception):
    """Raised immediately when the LLM semaphore queue has reached its maximum size
    (``LLM_MAX_QUEUE_SIZE``, default 10) and a new request arrives.

    The request is rejected without queuing to prevent unbounded latency growth.
    The caller should surface a "server busy" message to the user and retry later.
    """


class PoolTimeoutError(Exception):
    """Raised when the PostgreSQL connection pool cannot provide a connection within
    the configured wait timeout (30 s by default).

    This usually indicates the pool is exhausted under high concurrency.
    Consider increasing ``POSTGRES_POOL_MAX_SIZE``.
    """
