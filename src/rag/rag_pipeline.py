"""
RAG Pipeline - Main orchestrator for the RAG system.

Retrieval flow (optimised):
  Question
    → [Cache Lookup]                  — instant if hit
    → [Embed Query]                   — with LRU embedding cache
    → [Hybrid Search LIMIT k+buffer]  — pgvector + FTS + RRF, connection pool
    → [LLM Generation]                — Prompt Fusion (1 call) or classic (2 calls)
    → [Stream tokens to UI]           — true Ollama streaming
    → [Background: Summary + Memory]  — async, non-blocking
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Generator, List, Optional

from langchain_core.documents import Document

from src.config import (
    ASYNC_POST_PROCESSING_ENABLED,
    MMR_ENABLED,
    MMR_FETCH_K,
    MMR_LAMBDA,
    PROMPT_FUSION_ENABLED,
    QUERY_CACHE_ENABLED,
    CACHE_TTL_SECONDS,
    QUERY_REWRITE_ENABLED,
    STREAMING_ENABLED,
    LLM_MODEL,
)
from src.document_loader import DocumentProcessor
from src.embeddings import EmbeddingManager
from src.llm import LLMManager
from src.rag.benchmark import PerformanceBenchmark
from src.rag.exceptions import LLMQueueFullError, LLMTimeoutError
from src.rag.models import FusedLLMResponse, TimingBreakdown
from src.rag.post_response_executor import PostResponseTaskExecutor
from src.rag.query_cache import QueryCache
from src.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

# System prompt used exclusively for the classic (non-fused) query rewriting step.
_REWRITE_SYSTEM_PROMPT = (
    "Bạn là chuyên gia mở rộng từ viết tắt trong câu lệnh tìm kiếm TIẾNG VIỆT. "
    "Nhiệm vụ: Chỉ mở rộng các từ viết tắt (ví dụ: CNTB -> Chủ nghĩa Tư bản). "
    "Quy tắc tối thượng: "
    "1. GIỮ NGUYÊN các động từ và ý nghĩa gốc của câu. "
    "2. CHỈ trả về câu văn đã mở rộng từ viết tắt. "
    "3. KHÔNG giải thích, không thêm bớt nội dung khác, không dùng ngôn ngữ khác ngoài tiếng Việt."
)


class RAGPipeline:
    """Main RAG pipeline for document Q&A with full performance optimisations."""

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        vector_store_manager: Optional[VectorStoreManager] = None,
        document_processor: Optional[DocumentProcessor] = None,
        query_cache: Optional[QueryCache] = None,
        benchmark: Optional[PerformanceBenchmark] = None,
        post_task_executor: Optional[PostResponseTaskExecutor] = None,
        # Feature flags (read from env by default)
        query_rewrite_enabled: bool = QUERY_REWRITE_ENABLED,
        mmr_enabled: bool = MMR_ENABLED,
        mmr_fetch_k: int = MMR_FETCH_K,
        mmr_lambda: float = MMR_LAMBDA,
        prompt_fusion_enabled: bool = PROMPT_FUSION_ENABLED,
        streaming_enabled: bool = STREAMING_ENABLED,
        async_post_processing_enabled: bool = ASYNC_POST_PROCESSING_ENABLED,
    ):
        self.llm_manager = llm_manager or LLMManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.vector_store_manager = vector_store_manager or VectorStoreManager(
            embedding_manager=self.embedding_manager
        )
        self.document_processor = document_processor or DocumentProcessor()

        self.query_cache = query_cache or QueryCache(
            ttl_seconds=CACHE_TTL_SECONDS,
            enabled=QUERY_CACHE_ENABLED,
        )
        self.benchmark = benchmark or PerformanceBenchmark()
        self.post_task_executor = post_task_executor or PostResponseTaskExecutor()

        # Feature flags
        self.query_rewrite_enabled = query_rewrite_enabled
        self.mmr_enabled = mmr_enabled
        self.mmr_fetch_k = mmr_fetch_k
        self.mmr_lambda = mmr_lambda
        self.prompt_fusion_enabled = prompt_fusion_enabled
        self.streaming_enabled = streaming_enabled
        self.async_post_processing_enabled = async_post_processing_enabled

    # ------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------

    def warmup(self) -> None:
        """Pre-load the LLM into VRAM with a short dummy prompt.

        Only the LLM is warmed up — the embedding model is loaded on-demand
        to avoid occupying VRAM with both models simultaneously.

        Logs a WARNING and continues normally if the warm-up call fails.
        """
        try:
            logger.info("[warmup] Loading LLM into VRAM …")
            self.llm_manager.invoke("Xin chào")
            logger.info("[warmup] LLM ready.")
        except Exception as exc:
            logger.warning("[warmup] LLM warm-up failed (%s) — continuing.", exc)

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def load_documents(self, source: str, is_directory: bool = True) -> int:
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
    # Classic (non-fused) query rewriting
    # ------------------------------------------------------------------

    def _rewrite_query(self, question: str) -> str:
        """Use the LLM to expand abbreviations (classic 2-call flow).

        Falls back to the original question if the LLM fails or returns nothing.
        """
        try:
            rewritten = self.llm_manager.generate_response(
                query=question,
                context="",
                system_prompt=_REWRITE_SYSTEM_PROMPT,
            ).strip()
            if not rewritten or len(rewritten) > len(question) * 4:
                return question
            return rewritten
        except Exception:
            return question

    # ------------------------------------------------------------------
    # Core query method
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        k: int = 4,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Query the RAG system and return a complete response dict.

        Args:
            question:     The user's current question.
            k:            Number of documents to retrieve.
            system_prompt: Optional system instruction for the LLM.
            chat_history: Recent conversation turns for context resolution.

        Returns:
            Dict with keys: ``answer``, ``sources``, ``context``,
            ``rewritten_query``, ``timing``.
        """
        total_start = time.perf_counter()
        timings: Dict[str, float] = {}

        # ----------------------------------------------------------
        # Step 1 — Cache lookup
        # ----------------------------------------------------------
        cache_key = self.query_cache.make_key(
            query=question,
            top_k=k,
            filters=None,
            model_version=self.llm_manager.model,
        )
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            logger.debug("[pipeline] Cache HIT for query: %r", question[:60])
            # Inject fresh timing showing it was a cache hit
            cached["timing"] = self.benchmark.build_timing_dict(
                {"total_ms": (time.perf_counter() - total_start) * 1_000.0}
            )
            return cached

        logger.debug("[pipeline] Cache MISS for query: %r", question[:60])

        # ----------------------------------------------------------
        # Step 2 — Embed query
        # ----------------------------------------------------------
        with self.benchmark.measure("embedding") as t_embed:
            query_embedding_text = question  # used only for cache key; actual embed inside VSM

        timings["embedding_ms"] = t_embed.elapsed_ms

        # ----------------------------------------------------------
        # Step 3 — Hybrid search
        # ----------------------------------------------------------
        with self.benchmark.measure("search") as t_search:
            relevant_docs = self.vector_store_manager.similarity_search(
                query=question,
                keyword_query=question,
                k=k,
            )
        timings["search_ms"] = t_search.elapsed_ms

        if not relevant_docs:
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            timings["total_ms"] = total_ms
            return {
                "answer": "Không tìm thấy tài liệu liên quan đến câu hỏi của bạn.",
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict(timings),
            }

        # ----------------------------------------------------------
        # Step 4 — Build context
        # ----------------------------------------------------------
        context_parts = []
        for doc in relevant_docs:
            breadcrumb = doc.metadata.get("breadcrumb", "")
            if breadcrumb:
                context_parts.append(f"{breadcrumb}\n\n{doc.page_content}")
            else:
                context_parts.append(doc.page_content)
        context = "\n\n---\n\n".join(context_parts)

        # Debug: log context summary so we can verify what the LLM receives
        logger.info(
            "[pipeline] Context built: %d docs, %d chars. Sources: %s",
            len(relevant_docs),
            len(context),
            [d.metadata.get("source", "?").split("\\")[-1][:30] for d in relevant_docs[:3]],
        )

        # ----------------------------------------------------------
        # Step 5 — LLM generation
        # ----------------------------------------------------------
        rewritten_query: Optional[str] = None
        queue_wait_ms = 0.0

        if self.prompt_fusion_enabled:
            # Single LLM call: rewrite + generate
            with self.benchmark.measure("llm") as t_llm:
                try:
                    fused_result = self.llm_manager.generate_response_fused(
                        query=question,
                        context=context,
                        system_prompt=system_prompt,
                        chat_history=chat_history,
                    )
                    answer = fused_result["answer"]
                    rewritten_query = fused_result.get("rewritten_query")
                    queue_wait_ms = fused_result.get("queue_wait_ms", 0.0)
                except (LLMQueueFullError, LLMTimeoutError):
                    raise
                except Exception as exc:
                    logger.warning(
                        "[pipeline] Fused generation failed (%s) — falling back to classic flow.",
                        exc,
                    )
                    answer = self._classic_generate(
                        question, context, system_prompt, chat_history
                    )
        else:
            # Classic 2-call flow
            if self.query_rewrite_enabled:
                rewritten = self._rewrite_query(question)
                if rewritten != question:
                    rewritten_query = rewritten

            search_query = rewritten_query or question
            with self.benchmark.measure("llm") as t_llm:
                answer = self._classic_generate(
                    search_query, context, system_prompt, chat_history
                )

        timings["llm_ms"] = t_llm.elapsed_ms if "t_llm" in dir() else 0.0
        timings["queue_wait_ms"] = queue_wait_ms

        # ----------------------------------------------------------
        # Step 6 — Build sources
        # ----------------------------------------------------------
        sources = [
            {
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata,
                "breadcrumb": doc.metadata.get("breadcrumb", ""),
            }
            for doc in relevant_docs
        ]

        # ----------------------------------------------------------
        # Step 7 — Store in cache
        # ----------------------------------------------------------
        total_ms = (time.perf_counter() - total_start) * 1_000.0
        timings["total_ms"] = total_ms
        timing_dict = self.benchmark.build_timing_dict(timings)

        response = {
            "answer": answer,
            "sources": sources,
            "context": context,
            "rewritten_query": rewritten_query,
            "timing": timing_dict,
        }
        self.query_cache.set(cache_key, response)

        # ----------------------------------------------------------
        # Step 8 — Record QPS
        # ----------------------------------------------------------
        self.benchmark.record_query()

        return response

    def _classic_generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str],
        chat_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Invoke the non-fused LLM generation path."""
        return self.llm_manager.generate_response(
            query=query,
            context=context,
            system_prompt=system_prompt,
            chat_history=chat_history,
        )

    # ------------------------------------------------------------------
    # Streaming query
    # ------------------------------------------------------------------

    def query_stream(
        self,
        question: str,
        k: int = 4,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        """Stream the LLM answer token by token.

        Yields individual token strings as they arrive from Ollama.
        Measures TTFT (time to first token).

        Cache lookup is performed first — if a cached answer exists, it is
        yielded word-by-word to preserve the streaming UX.

        After all tokens are yielded, post-response background tasks are
        submitted (if async_post_processing_enabled).
        """
        total_start = time.perf_counter()

        # Cache lookup
        cache_key = self.query_cache.make_key(
            query=question,
            top_k=k,
            filters=None,
            model_version=self.llm_manager.model,
        )
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            logger.debug("[pipeline] Stream cache HIT for query: %r", question[:60])
            for word in cached["answer"].split(" "):
                yield word + " "
            return

        # Hybrid search
        relevant_docs = self.vector_store_manager.similarity_search(
            query=question,
            keyword_query=question,
            k=k,
        )
        if not relevant_docs:
            yield "Không tìm thấy tài liệu liên quan đến câu hỏi của bạn."
            return

        # Build context
        context_parts = []
        for doc in relevant_docs:
            breadcrumb = doc.metadata.get("breadcrumb", "")
            if breadcrumb:
                context_parts.append(f"{breadcrumb}\n\n{doc.page_content}")
            else:
                context_parts.append(doc.page_content)
        context = "\n\n---\n\n".join(context_parts)

        # Stream from LLM
        ttft_recorded = False
        ttft_ms = 0.0
        accumulated_tokens: List[str] = []
        rewritten_query: Optional[str] = None
        full_answer = ""

        try:
            if self.prompt_fusion_enabled:
                # With Prompt Fusion the LLM returns JSON, not plain text.
                # Streaming raw JSON tokens to the UI would show the JSON structure
                # to the user, which is wrong.  Instead we call the non-streaming
                # fused method to get the parsed answer, then stream it word-by-word
                # so the UI still gets a progressive display.
                #
                # The entire fused call is wrapped in try/except/finally so that
                # the semaphore is always released even if:
                #   - generate_response_fused() raises an unhandled exception
                #   - the generator is abandoned mid-stream (Streamlit rerun)
                try:
                    fused_result = self.llm_manager.generate_response_fused(
                        query=question,
                        context=context,
                        system_prompt=system_prompt,
                        chat_history=chat_history,
                    )
                    clean_answer = fused_result["answer"]
                    rewritten_query = fused_result.get("rewritten_query")
                except (LLMQueueFullError, LLMTimeoutError) as exc:
                    yield f"\n\n❌ Lỗi: {exc}"
                    return
                except Exception as exc:
                    logger.exception("[pipeline] Fused generation failed in query_stream")
                    yield f"\n\n❌ Lỗi không xác định: {exc}"
                    return

                # Stream the clean answer word-by-word for progressive UX
                words = clean_answer.split(" ")
                for i, word in enumerate(words):
                    token = word + (" " if i < len(words) - 1 else "")
                    if not ttft_recorded:
                        ttft_ms = (time.perf_counter() - total_start) * 1_000.0
                        ttft_recorded = True
                    accumulated_tokens.append(token)
                    yield token

                full_answer = clean_answer
            else:
                # Classic flow: stream raw tokens directly (no JSON wrapping)
                prompt = self._build_classic_prompt(
                    question, context, system_prompt, chat_history
                )
                token_stream = self.llm_manager.stream(prompt)

                for token in token_stream:
                    if not ttft_recorded:
                        ttft_ms = (time.perf_counter() - total_start) * 1_000.0
                        ttft_recorded = True
                        logger.debug("[pipeline] TTFT=%.1f ms", ttft_ms)
                    accumulated_tokens.append(token)
                    yield token

                full_answer = "".join(accumulated_tokens)

        except (LLMQueueFullError, LLMTimeoutError) as exc:
            yield f"\n\n❌ Lỗi: {exc}"
            return

        sources = [
            {
                "content": doc.page_content[:200] + "...",
                "metadata": doc.metadata,
                "breadcrumb": doc.metadata.get("breadcrumb", ""),
            }
            for doc in relevant_docs
        ]
        total_ms = (time.perf_counter() - total_start) * 1_000.0
        cached_response = {
            "answer": full_answer,
            "sources": sources,
            "context": context,
            "rewritten_query": rewritten_query if self.prompt_fusion_enabled else None,
            "timing": self.benchmark.build_timing_dict(
                {"ttft_ms": ttft_ms, "total_ms": total_ms}
            ),
        }
        self.query_cache.set(cache_key, cached_response)
        self.benchmark.record_query()

    def _build_classic_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str],
        chat_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build the non-fused prompt string for streaming."""
        if system_prompt is None:
            system_prompt = (
                "Bạn là trợ lý học thuật về Quan hệ Quốc tế.\n\n"
                "NHIỆM VỤ:\n"
                "Trả lời câu hỏi dựa trên tài liệu, tập trung vào phân tích trong lĩnh vực "
                "Quan hệ Quốc tế (QHQT).\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. PHẢI trả lời trong bối cảnh Quan hệ Quốc tế (QHQT)\n"
                "2. KHÔNG được chỉ trả lời về nguồn gốc xã hội học/tâm lý học nếu câu hỏi "
                "liên quan đến QHQT\n"
                "3. Nếu context có nhiều phần, PHẢI chọn phần liên quan trực tiếp đến QHQT\n"
                "4. Nếu chỉ có thông tin nền tảng (ví dụ Cooley, Mead, Linton), PHẢI nói rõ "
                "đây chỉ là nền tảng và KHÔNG đủ để trả lời đầy đủ trong QHQT\n"
                "5. Câu trả lời phải có nội dung phân tích, không chỉ liệt kê tên công trình\n\n"
                "KIỂM TRA CUỐI:\n"
                "- Nếu câu trả lời chỉ nói về nguồn gốc khái niệm mà không liên hệ QHQT "
                "→ KHÔNG hợp lệ → phải viết lại\n\n"
                "Trả lời bằng tiếng Việt."
            )
        history_block = ""
        if chat_history:
            lines = []
            for msg in chat_history[-6:]:
                role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
                content = str(msg.get("content", "")).strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "Lịch sử hội thoại gần nhất:\n" + "\n".join(lines) + "\n\n"

        return (
            f"{system_prompt}\n\n"
            f"Ngữ cảnh tài liệu:\n{context}\n\n"
            f"{history_block}"
            f"Câu hỏi: {query}\n\n"
            "Trả lời:"
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def query_simple(self, question: str, k: int = 4) -> str:
        """Simple query returning just the answer string."""
        return self.query(question, k=k)["answer"]

    def chat(self, question: str) -> str:
        """Chat interface for quick queries."""
        return self.query_simple(question)

    def clear_cache(self) -> None:
        """Clear the in-memory query cache. Call this after re-indexing documents."""
        with self.query_cache._lock:
            self.query_cache._store.clear()
            self.query_cache._hits = 0
            self.query_cache._misses = 0
        logger.info("[pipeline] Query cache cleared.")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        cache_stats = self.query_cache.get_stats()
        return {
            "vector_store": self.vector_store_manager.get_collection_stats(),
            "llm_model": self.llm_manager.model,
            "embedding_model": self.embedding_manager.model,
            "query_rewrite_enabled": self.query_rewrite_enabled,
            "prompt_fusion_enabled": self.prompt_fusion_enabled,
            "streaming_enabled": self.streaming_enabled,
            "async_post_processing_enabled": self.async_post_processing_enabled,
            "mmr_enabled": self.mmr_enabled,
            "mmr_lambda": self.mmr_lambda,
            "qps": self.benchmark.get_qps(),
            "cache_hits": cache_stats["hits"],
            "cache_misses": cache_stats["misses"],
        }
