"""
RAG Pipeline - Main orchestrator for the RAG system.

Retrieval flow:
  Question
    → [Optional] Query Rewriting  (LLM expands abbreviations / clarifies intent)
    → Hybrid Search  (pgvector + FTS + RRF)
    → [Optional] MMR Reranking    (remove redundant chunks)
    → LLM generation
"""
from typing import List, Optional, Dict, Any
from pathlib import Path

from langchain_core.documents import Document

from src.config import (
    DATA_DIR,
    MMR_ENABLED,
    MMR_FETCH_K,
    MMR_LAMBDA,
    QUERY_REWRITE_ENABLED,
)
from src.document_loader import DocumentProcessor
from src.embeddings import EmbeddingManager
from src.llm import LLMManager
from src.rag.vector_store import VectorStoreManager

# System prompt used exclusively for query rewriting — intentionally concise
_REWRITE_SYSTEM_PROMPT = (
    "Bạn là chuyên gia mở rộng từ viết tắt trong câu lệnh tìm kiếm TIẾNG VIỆT. "
    "Nhiệm vụ: Chỉ mở rộng các từ viết tắt (ví dụ: CNTB -> Chủ nghĩa Tư bản). "
    "Quy tắc tối thượng: "
    "1. GIỮ NGUYÊN các động từ và ý nghĩa gốc của câu (ví dụ: 'ra đời' phải giữ là 'ra đời', không được đổi thành 'hoạt động'). "
    "2. CHỈ trả về câu văn đã mở rộng từ viết tắt. "
    "3. KHÔNG giải thích, không thêm bớt nội dung khác, không dùng ngôn ngữ khác ngoài tiếng Việt."
)


class RAGPipeline:
    """Main RAG pipeline for document Q&A."""

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        vector_store_manager: Optional[VectorStoreManager] = None,
        document_processor: Optional[DocumentProcessor] = None,
        query_rewrite_enabled: bool = QUERY_REWRITE_ENABLED,
        mmr_enabled: bool = MMR_ENABLED,
        mmr_fetch_k: int = MMR_FETCH_K,
        mmr_lambda: float = MMR_LAMBDA,
    ):
        self.llm_manager = llm_manager or LLMManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.vector_store_manager = vector_store_manager or VectorStoreManager(
            embedding_manager=self.embedding_manager
        )
        self.document_processor = document_processor or DocumentProcessor()

        self.query_rewrite_enabled = query_rewrite_enabled
        self.mmr_enabled = mmr_enabled
        self.mmr_fetch_k = mmr_fetch_k
        self.mmr_lambda = mmr_lambda

    # ------------------------------------------------------------------
    # Query Rewriting
    # ------------------------------------------------------------------

    def _rewrite_query(self, question: str) -> str:
        """Use the LLM to expand abbreviations and clarify the search intent.

        Falls back to the original question if the LLM fails or returns nothing.
        """
        try:
            rewritten = self.llm_manager.generate_response(
                query=question,
                context="",          # No document context needed for rewriting
                system_prompt=_REWRITE_SYSTEM_PROMPT,
            ).strip()
            # Safety: if the model returns something very long or empty, keep original
            if not rewritten or len(rewritten) > len(question) * 4:
                return question
            return rewritten
        except Exception:
            return question

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def load_documents(
        self,
        source: str,
        is_directory: bool = True
    ) -> int:
        """Load documents into the vector store."""
        documents = self.document_processor.process_documents(
            source=source,
            is_directory=is_directory,
        )

        if not documents:
            print("No documents found to load.")
            return 0

        self.vector_store_manager.add_documents(documents)
        print(f"Successfully loaded {len(documents)} document chunks.")
        return len(documents)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        k: int = 4,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Query the RAG system with optional Query Rewriting and MMR.

        Args:
            question: The user's current question.
            k: Number of documents to retrieve.
            system_prompt: Optional system instruction for the LLM.
            chat_history: Recent conversation turns for context resolution
                          (e.g. resolving "ngày đó", "ông ấy", etc.).

        Returns a dict with keys: answer, sources, context, rewritten_query.
        """
        # Step 1 — Query Rewriting
        search_query = question
        rewritten_query: Optional[str] = None
        if self.query_rewrite_enabled:
            rewritten = self._rewrite_query(question)
            if rewritten != question:
                rewritten_query = rewritten
                search_query = rewritten

        # Step 2 — Retrieve (Hybrid Search)
        # We use the REWRITTEN query for Semantic Search (Vector)
        # and the ORIGINAL query for Keyword Search (FTS) to catch abbreviations.
        relevant_docs = self.vector_store_manager.similarity_search(
            query=search_query,      # Semantic (Rewritten)
            keyword_query=question,  # Keyword (Original)
            k=k,
        )

        # MMR is disabled for now to simplify and match previous behavior
        # (Alternatively, you can keep it but we start with raw hybrid results)

        if not relevant_docs:
            return {
                "answer": "Không tìm thấy tài liệu liên quan đến câu hỏi của bạn.",
                "sources": [],
                "context": "",
                "rewritten_query": rewritten_query,
            }

        # Step 3 — Build context (inject breadcrumb for LLM without polluting embeddings)
        context_parts = []
        for doc in relevant_docs:
            breadcrumb = doc.metadata.get("breadcrumb", "")
            if breadcrumb:
                context_parts.append(f"{breadcrumb}\n\n{doc.page_content}")
            else:
                context_parts.append(doc.page_content)

        context = "\n\n---\n\n".join(context_parts)

        # Step 4 — LLM generation
        answer = self.llm_manager.generate_response(
            query=search_query,   # Use rewritten query so LLM knows expanded terms
            context=context,
            system_prompt=system_prompt,
            chat_history=chat_history,
        )

        # Step 5 — Build sources metadata
        sources = [
            {
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata,
                "breadcrumb": doc.metadata.get("breadcrumb", ""),
            }
            for doc in relevant_docs
        ]

        return {
            "answer": answer,
            "sources": sources,
            "context": context,
            "rewritten_query": rewritten_query,
        }

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def query_simple(self, question: str, k: int = 4) -> str:
        """Simple query returning just the answer string."""
        return self.query(question, k=k)["answer"]

    def chat(self, question: str) -> str:
        """Chat interface for quick queries."""
        return self.query_simple(question)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "vector_store": self.vector_store_manager.get_collection_stats(),
            "llm_model": self.llm_manager.model,
            "embedding_model": self.embedding_manager.model,
            "query_rewrite_enabled": self.query_rewrite_enabled,
            "mmr_enabled": self.mmr_enabled,
            "mmr_lambda": self.mmr_lambda,
        }
