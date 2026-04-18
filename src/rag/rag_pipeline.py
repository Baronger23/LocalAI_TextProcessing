"""
RAG Pipeline - Main orchestrator for the RAG system.
"""
from typing import List, Optional, Dict, Any
from pathlib import Path

from langchain_core.documents import Document

from src.config import DATA_DIR
from src.document_loader import DocumentProcessor
from src.embeddings import EmbeddingManager
from src.llm import LLMManager
from src.rag.vector_store import VectorStoreManager


class RAGPipeline:
    """Main RAG pipeline for document Q&A."""
    
    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        vector_store_manager: Optional[VectorStoreManager] = None,
        document_processor: Optional[DocumentProcessor] = None
    ):
        self.llm_manager = llm_manager or LLMManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.vector_store_manager = vector_store_manager or VectorStoreManager(
            embedding_manager=self.embedding_manager
        )
        self.document_processor = document_processor or DocumentProcessor()
    
    def load_documents(
        self,
        source: str,
        is_directory: bool = True
    ) -> int:
        """Load documents into the vector store."""
        # Process documents
        documents = self.document_processor.process_documents(
            source=source,
            is_directory=is_directory
        )
        
        if not documents:
            print("No documents found to load.")
            return 0
        
        # Add to vector store
        self.vector_store_manager.add_documents(documents)
        
        print(f"Successfully loaded {len(documents)} document chunks.")
        return len(documents)
    
    def query(
        self,
        question: str,
        k: int = 4,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query the RAG system."""
        # Retrieve relevant documents
        relevant_docs = self.vector_store_manager.similarity_search(
            query=question,
            k=k
        )
        
        if not relevant_docs:
            return {
                "answer": "Không tìm thấy tài liệu liên quan đến câu hỏi của bạn.",
                "sources": [],
                "context": ""
            }
        
        # Build context from retrieved documents
        # page_content already includes breadcrumb prefix from Context Enricher
        context = "\n\n---\n\n".join([
            doc.page_content for doc in relevant_docs
        ])
        
        # Generate response
        answer = self.llm_manager.generate_response(
            query=question,
            context=context,
            system_prompt=system_prompt
        )
        
        # Extract sources with enriched metadata
        sources = []
        for doc in relevant_docs:
            source_info = {
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata,
                "breadcrumb": doc.metadata.get("breadcrumb", ""),
            }
            sources.append(source_info)
        
        return {
            "answer": answer,
            "sources": sources,
            "context": context
        }
    
    def query_simple(self, question: str, k: int = 4) -> str:
        """Simple query returning just the answer."""
        result = self.query(question, k=k)
        return result["answer"]
    
    def chat(self, question: str) -> str:
        """Chat interface for quick queries."""
        return self.query_simple(question)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "vector_store": self.vector_store_manager.get_collection_stats(),
            "llm_model": self.llm_manager.model,
            "embedding_model": self.embedding_manager.model
        }
