"""
Embedding module using Ollama.

Supports:
  - Single query embedding (embed_query) with optional LRU cache
  - Batch document embedding (embed_documents_batched) with truncation and retry
"""
import hashlib
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import List, Optional

from langchain_ollama import OllamaEmbeddings

from src.config import (
    OLLAMA_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    OLLAMA_KEEP_ALIVE,
    EMBEDDING_CACHE_ENABLED,
    EMBEDDING_CACHE_MAX_SIZE,
)

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manage embeddings using Ollama with optional LRU cache."""

    # Maximum characters per chunk before truncation
    _MAX_EMBED_CHARS = 3000
    _EMBED_RETRIES = 3

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        keep_alive: int = OLLAMA_KEEP_ALIVE,
        cache_enabled: bool = EMBEDDING_CACHE_ENABLED,
        cache_max_size: int = EMBEDDING_CACHE_MAX_SIZE,
    ):
        self.model = model
        self.base_url = base_url
        self.batch_size = batch_size
        self.keep_alive = keep_alive
        self.cache_enabled = cache_enabled
        self.cache_max_size = cache_max_size

        self._embeddings = None

        # LRU cache: OrderedDict[cache_key, vector]
        # Thread-safe via _cache_lock
        if self.cache_enabled:
            self._cache: OrderedDict[str, List[float]] = OrderedDict()
            self._cache_lock = threading.Lock()
        else:
            self._cache = None
            self._cache_lock = None

    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url,
                keep_alive=self.keep_alive,
            )
        return self._embeddings

    # ------------------------------------------------------------------
    # Text normalisation & cache key
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalise text before hashing.

        Steps:
        1. Lowercase
        2. Strip leading/trailing whitespace
        3. Collapse multiple consecutive whitespace characters into a single space
        """
        lowered = text.lower().strip()
        return re.sub(r"\s+", " ", lowered)

    @staticmethod
    def _cache_key(normalized_text: str) -> str:
        """Return a 16-character hex digest of the normalised text."""
        digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        return digest[:16]

    # ------------------------------------------------------------------
    # Embedding with cache
    # ------------------------------------------------------------------

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text with optional LRU cache lookup."""
        if not self.cache_enabled or self._cache is None:
            # Cache disabled — call Ollama directly
            return self.embeddings.embed_query(text)

        # Normalise and compute cache key
        normalized = self._normalize_text(text)
        key = self._cache_key(normalized)

        # Try cache lookup
        with self._cache_lock:
            if key in self._cache:
                # Move to end (LRU)
                self._cache.move_to_end(key)
                vector = self._cache[key]
                logger.debug("[embedding_cache] HIT key=%s", key)
                return vector

        # Cache miss — call Ollama
        logger.debug("[embedding_cache] MISS key=%s", key)
        vector = self.embeddings.embed_query(text)

        # Store in cache
        with self._cache_lock:
            self._cache[key] = vector
            self._cache.move_to_end(key)
            # Evict oldest if over max size
            if len(self._cache) > self.cache_max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug("[embedding_cache] EVICT key=%s", evicted_key)

        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (raw langchain call)."""
        return self.embeddings.embed_documents(texts)

    def embed_documents_batched(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """Embed documents in batches with truncation and retry.

        Args:
            texts: List of text strings to embed.
            batch_size: Override the default batch size. If None, uses self.batch_size.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        bs = batch_size or self.batch_size
        all_vectors: List[List[float]] = []

        # Truncate all texts upfront
        truncated = [t[: self._MAX_EMBED_CHARS] for t in texts]

        # Process in batches
        for i in range(0, len(truncated), bs):
            batch = truncated[i : i + bs]
            vectors = self._embed_batch_with_retry(batch)
            all_vectors.extend(vectors)

        return all_vectors

    def _embed_batch_with_retry(self, batch: List[str]) -> List[List[float]]:
        """Embed a single batch with exponential backoff retry."""
        last_exc: Exception | None = None
        for attempt in range(1, self._EMBED_RETRIES + 1):
            try:
                return self.embeddings.embed_documents(batch)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._EMBED_RETRIES:
                    time.sleep(2 ** attempt)  # 2s, 4s backoff
        raise RuntimeError(
            f"Batch embedding failed after {self._EMBED_RETRIES} attempts: {last_exc}"
        ) from last_exc
