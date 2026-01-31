"""
Tests for the RAG pipeline.
"""
import pytest
from src.rag import RAGPipeline
from src.llm import LLMManager
from src.embeddings import EmbeddingManager


class TestLLMManager:
    """Test LLM Manager functionality."""
    
    def test_llm_initialization(self):
        """Test LLM manager can be initialized."""
        llm = LLMManager()
        assert llm.model == "qwen2.5:7b"
    
    def test_llm_invoke(self):
        """Test LLM can generate response."""
        llm = LLMManager()
        response = llm.invoke("Xin chào")
        assert response is not None
        assert len(response) > 0


class TestEmbeddingManager:
    """Test Embedding Manager functionality."""
    
    def test_embedding_initialization(self):
        """Test embedding manager can be initialized."""
        embed = EmbeddingManager()
        assert embed.model == "nomic-embed-text:v1.5"
    
    def test_embed_query(self):
        """Test embedding generation."""
        embed = EmbeddingManager()
        result = embed.embed_query("Test embedding")
        assert isinstance(result, list)
        assert len(result) == 768  # Nomic embed dimension


class TestRAGPipeline:
    """Test RAG Pipeline functionality."""
    
    def test_pipeline_initialization(self):
        """Test RAG pipeline can be initialized."""
        rag = RAGPipeline()
        assert rag.llm_manager is not None
        assert rag.embedding_manager is not None
        assert rag.vector_store_manager is not None
    
    def test_get_stats(self):
        """Test getting pipeline stats."""
        rag = RAGPipeline()
        stats = rag.get_stats()
        assert "llm_model" in stats
        assert "embedding_model" in stats
        assert "vector_store" in stats
