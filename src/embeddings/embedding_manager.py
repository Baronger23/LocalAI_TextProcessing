"""
Embedding module using Ollama.

Supports:
  - Single query embedding (embed_query)
  - Batch document embedding (embed_documents_batched) with truncation and retry
"""
import time
from typing import List

from langchain_ollama import OllamaEmbeddings

from src.config import OLLAMA_BASE_URL, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE


class EmbeddingManager:
    """Manage embeddings using Ollama."""

    # Maximum characters per chunk before truncation
    _MAX_EMBED_CHARS = 8000
    _EMBED_RETRIES = 3

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        batch_size: int = EMBEDDING_BATCH_SIZE,
    ):
        self.model = model
        self.base_url = base_url
        self.batch_size = batch_size
        self._embeddings = None

    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url,
                keep_alive=0,  # Unload from VRAM immediately after use to avoid OOM with LLM
            )
        return self._embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (raw langchain call)."""
        return self.embeddings.embed_documents(texts)

    def embed_documents_batched(
        self,
        texts: List[str],
        batch_size: int | None = None,
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
