"""
In-memory query-answer cache with TTL expiry.

Cache key design:
    hash(normalized_query + str(top_k) + str(sorted_filters) + model_version)

Text normalisation (applied before hashing):
    lowercase → strip leading/trailing whitespace → collapse internal whitespace
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from typing import Any, Optional

from src.rag.models import CacheEntry

logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe in-memory cache for RAG query answers.

    Args:
        ttl_seconds:  How long (in seconds) a cached entry remains valid.
                      Default: 300 (5 minutes).
        enabled:      When ``False`` every ``get()`` returns ``None`` and
                      ``set()`` is a no-op.  Useful for disabling cache via
                      the ``QUERY_CACHE_ENABLED`` env var.
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        enabled: bool = True,
    ) -> None:
        self._ttl = ttl_seconds
        self._enabled = enabled
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Cache key
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalise text before hashing.

        Steps:
        1. Lowercase
        2. Strip leading/trailing whitespace
        3. Collapse multiple consecutive whitespace characters into a single space
        """
        lowered = text.lower().strip()
        return re.sub(r"\s+", " ", lowered)

    def make_key(
        self,
        query: str,
        top_k: int,
        filters: Optional[dict[str, Any]],
        model_version: str,
    ) -> str:
        """Build a deterministic cache key.

        The key encodes:
        - Normalised query text
        - ``top_k`` (different k → different result set)
        - Sorted filter dict (different filters → different result set)
        - Model version (different model → different embeddings / answers)

        Returns a 64-character hex SHA-256 digest.
        """
        normalised_query = self.normalize_text(query)

        # Serialise filters in a stable, sorted order so that
        # {"a": 1, "b": 2} and {"b": 2, "a": 1} produce the same key.
        if filters:
            sorted_filters = json.dumps(filters, sort_keys=True, ensure_ascii=False)
        else:
            sorted_filters = "null"

        raw = f"{normalised_query}|{top_k}|{sorted_filters}|{model_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Look up ``key`` in the cache.

        Returns the cached value if the entry exists and has not expired.
        Returns ``None`` on a miss or if the cache is disabled.
        Expired entries are deleted on access (lazy eviction).
        """
        if not self._enabled:
            return None

        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._store[key]
                self._misses += 1
                logger.debug("[query_cache] EXPIRED key=%s", key[:16])
                return None

            self._hits += 1
            logger.debug("[query_cache] HIT key=%s", key[:16])
            return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` with the configured TTL.

        No-op when the cache is disabled.
        """
        if not self._enabled:
            return

        expire_at = time.time() + self._ttl
        with self._lock:
            self._store[key] = CacheEntry(value=value, expire_at=expire_at)
        logger.debug("[query_cache] SET key=%s ttl=%ds", key[:16], self._ttl)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Return cache hit/miss counters.

        Returns:
            ``{"hits": N, "misses": N}``
        """
        with self._lock:
            return {"hits": self._hits, "misses": self._misses}

    def clear(self) -> None:
        """Remove all entries from the cache (useful for testing)."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
