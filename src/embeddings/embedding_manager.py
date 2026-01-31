"""
Embedding module using Ollama.
"""
from typing import List
from langchain_ollama import OllamaEmbeddings

from src.config import OLLAMA_BASE_URL, EMBEDDING_MODEL


class EmbeddingManager:
    """Manage embeddings using Ollama."""
    
    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL
    ):
        self.model = model
        self.base_url = base_url
        self._embeddings = None
    
    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url
            )
        return self._embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        return self.embeddings.embed_documents(texts)
