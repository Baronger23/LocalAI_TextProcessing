"""
Source package for RAG system.
"""
# ruff: noqa: I001
# Import order is intentional: importing src.llm before src.rag can trigger a
# circular import through src.rag.exceptions during package initialization.
from src.rag import RAGPipeline
from src.llm import LLMManager
from src.embeddings import EmbeddingManager
from src.document_loader import DocumentProcessor
from src.chunking import AdaptiveChunkingPipeline

__version__ = "1.0.0"
__all__ = [
    "RAGPipeline",
    "LLMManager",
    "EmbeddingManager",
    "DocumentProcessor",
    "AdaptiveChunkingPipeline",
]
