"""
Vector store module using ChromaDB.
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from src.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from src.embeddings import EmbeddingManager


class VectorStoreManager:
    """Manage vector store operations using ChromaDB."""
    
    def __init__(
        self,
        persist_directory: str = CHROMA_PERSIST_DIR,
        collection_name: str = CHROMA_COLLECTION_NAME,
        embedding_manager: Optional[EmbeddingManager] = None
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self._vector_store = None
        
        # Ensure persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def vector_store(self) -> Chroma:
        """Get or create vector store instance."""
        if self._vector_store is None:
            self._vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_manager.embeddings,
                persist_directory=self.persist_directory
            )
        return self._vector_store
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store."""
        return self.vector_store.add_documents(documents)
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Search for similar documents."""
        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4
    ) -> List[tuple]:
        """Search for similar documents with relevance scores."""
        return self.vector_store.similarity_search_with_score(
            query=query,
            k=k
        )
    
    def delete_collection(self):
        """Delete the entire collection."""
        self.vector_store.delete_collection()
        self._vector_store = None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        collection = self.vector_store._collection
        return {
            "name": collection.name,
            "count": collection.count()
        }
