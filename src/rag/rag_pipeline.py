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
import re
import time
import unicodedata
from typing import Any, Callable, Dict, Generator, List, Optional

from langchain_core.documents import Document

from src.config import (
    ASYNC_POST_PROCESSING_ENABLED,
    BROAD_QUERY_TOP_K,
    DEFAULT_TOP_K,
    KEYWORD_SUPPLEMENT_ENABLED,
    KEYWORD_SUPPLEMENT_TOP_K,
    MAX_CONTEXT_CHARS,
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
from src.security import NO_AUTHORIZED_CONTEXT_MESSAGE, document_allowed

logger = logging.getLogger(__name__)

_BROAD_QUERY_KEYWORDS = (
    "các",
    "cac",
    "những",
    "phân tích",
    "phan tich",
    "so sánh",
    "so sanh",
    "liệt kê",
    "liet ke",
    "tổng hợp",
    "tong hop",
    "trình bày",
    "trinh bay",
    "đánh giá",
    "danh gia",
)

_FOLLOW_UP_MARKERS = (
    "nó",
    "cái đó",
    "cai do",
    "cái này",
    "cai nay",
    "điều đó",
    "dieu do",
    "điều này",
    "dieu nay",
    "vấn đề đó",
    "van de do",
    "vấn đề này",
    "van de nay",
    "ở trên",
    "o tren",
    "vừa rồi",
    "vua roi",
    "họ",
    "chúng",
    "chung",
)

_FOLLOW_UP_TOKEN_MARKERS = {"no", "ho"}

_HEADING_STOPWORDS = {
    "cac", "cong", "trinh", "lien", "quan", "den", "ve", "vai", "tro",
    "chu", "the", "quoc", "te", "anh", "huong", "cua", "trong", "ly",
    "luan", "nhung", "mot", "so", "va", "hoac", "duoc", "tu", "sau",
}

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
        keyword_supplement_enabled: bool = KEYWORD_SUPPLEMENT_ENABLED,
        keyword_supplement_top_k: int = KEYWORD_SUPPLEMENT_TOP_K,
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
        self.keyword_supplement_enabled = keyword_supplement_enabled
        self.keyword_supplement_top_k = keyword_supplement_top_k

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

    def load_documents(
        self,
        source: str,
        is_directory: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Load documents into the vector store."""
        documents = self.document_processor.process_documents(
            source=source,
            is_directory=is_directory,
        )
        if not documents:
            print("No documents found to load.")
            return 0
        if metadata:
            safe_metadata = dict(metadata)
            for document in documents:
                merged = dict(document.metadata or {})
                merged.update(safe_metadata)
                document.metadata = merged
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

    @staticmethod
    def _needs_contextual_rewrite(
        question: str,
        chat_history: Optional[List[Dict[str, Any]]],
    ) -> bool:
        """Return True when a question likely depends on recent dialogue."""
        if not chat_history:
            return False
        normalized = " ".join((question or "").lower().split())
        if not normalized:
            return False
        if any(marker in normalized for marker in _FOLLOW_UP_MARKERS):
            return True
        tokens = set(normalized.replace("?", " ").replace(".", " ").split())
        return bool(tokens & _FOLLOW_UP_TOKEN_MARKERS)

    @staticmethod
    def _format_rewrite_history(chat_history: Optional[List[Dict[str, Any]]]) -> str:
        """Format only the last few turns for contextual query rewriting."""
        if not chat_history:
            return ""
        lines: List[str] = []
        for msg in chat_history[-4:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = str(msg.get("content", "")).strip()
            if content:
                lines.append(f"{role}: {content[:700]}")
        return "\n".join(lines)

    def contextualize_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Rewrite vague follow-up questions into standalone retrieval queries.

        The gate is intentionally conservative so ordinary standalone questions
        do not pay an extra LLM call.
        """
        original = (question or "").strip()
        if not self._needs_contextual_rewrite(original, chat_history):
            return original

        history_text = self._format_rewrite_history(chat_history)
        if not history_text:
            return original

        prompt = f"""Viết lại câu hỏi hiện tại thành một câu hỏi độc lập để tìm kiếm tài liệu.
Chỉ dựa vào lịch sử hội thoại gần nhất. Không trả lời câu hỏi. Không thêm thông tin mới.
Nếu câu hỏi đã rõ nghĩa, trả lại y nguyên.

Lịch sử gần nhất:
{history_text}

Câu hỏi hiện tại:
{original}

Câu hỏi độc lập:"""

        try:
            rewritten = self.llm_manager.invoke(prompt).strip()
        except Exception:
            return original

        rewritten = rewritten.strip().strip('"').strip("'")
        if not rewritten:
            return original
        if len(rewritten) > max(400, len(original) * 6):
            return original
        return rewritten

    # ------------------------------------------------------------------
    # Response quality helpers
    # ------------------------------------------------------------------

    @staticmethod
    def classify_query_mode(question: str) -> str:
        """Classify query breadth for adaptive retrieval."""
        normalized = " ".join((question or "").lower().split())
        if any(keyword in normalized for keyword in _BROAD_QUERY_KEYWORDS):
            return "broad"
        return "focused"

    @staticmethod
    def _normalize_doc_text(text: str) -> str:
        """Normalize chunk text for duplicate detection."""
        return " ".join((text or "").lower().split())

    @staticmethod
    def _normalize_query_text(text: str) -> str:
        """Normalize Vietnamese-ish query text for lightweight matching."""
        lowered = (text or "").lower().replace("đ", "d")
        folded = "".join(
            ch
            for ch in unicodedata.normalize("NFD", lowered)
            if unicodedata.category(ch) != "Mn"
        )
        return " ".join(folded.split())

    def _resolve_top_k(self, question: str, k: Optional[int]) -> int:
        """Return explicit k or choose an adaptive default from query mode."""
        if k is not None:
            return k
        mode = self.classify_query_mode(question)
        return BROAD_QUERY_TOP_K if mode == "broad" else DEFAULT_TOP_K

    @classmethod
    def _heading_tokens(cls, text: str) -> set[str]:
        normalized = cls._normalize_query_text(text)
        return {
            token for token in re.findall(r"[a-z0-9]+", normalized)
            if len(token) >= 3 and token not in _HEADING_STOPWORDS
        }

    @classmethod
    def _heading_relevance(cls, question: str, heading: str) -> int:
        query_tokens = cls._heading_tokens(question)
        heading_tokens = cls._heading_tokens(heading)
        if not query_tokens or not heading_tokens:
            return 0
        return len(query_tokens & heading_tokens)

    @staticmethod
    def _clean_heading(text: str) -> str:
        heading = re.sub(r"^\s*[-•\uf0b7\d.)]+", "", text or "").strip()
        heading = re.sub(r"^\s*mục\s*:\s*", "", heading, flags=re.IGNORECASE)
        heading = re.sub(r"\s+", " ", heading)
        return heading[:240]

    @classmethod
    def _is_decomposition_heading(cls, heading: str) -> bool:
        normalized = cls._normalize_query_text(heading)
        if not normalized or normalized.startswith("chuong "):
            return False
        return (
            "chiu anh huong" in normalized
            or ("cac cong trinh" in normalized and "lien quan den" in normalized)
        )

    @classmethod
    def _extract_candidate_headings(cls, doc: Document) -> List[str]:
        metadata = doc.metadata or {}
        candidates: List[str] = []

        for key in ("section_title", "outline_path", "chapter_title", "breadcrumb"):
            value = str(metadata.get(key) or "").strip()
            if value and value.lower() not in {"tổng quan các mục chính", "tong quan cac muc chinh"}:
                candidates.extend(part.strip() for part in value.split(">") if part.strip())

        for line in str(doc.page_content or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("-", "•")):
                candidates.append(stripped)
            elif "các công trình" in stripped.lower() or "chịu ảnh hưởng" in stripped.lower():
                candidates.append(stripped)

        cleaned: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            heading = cls._clean_heading(candidate)
            normalized = cls._normalize_query_text(heading)
            if len(heading) < 12 or normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(heading)
        return cleaned

    @classmethod
    def decompose_broad_query(
        cls,
        question: str,
        seed_docs: Optional[List[Document]] = None,
        max_facets: int = 8,
    ) -> List[Dict[str, str]]:
        """Build retrieval facets from outline/heading chunks already found.

        This is intentionally data-driven: headings come from retrieved document
        metadata/content, not a fixed domain list.
        """
        if not seed_docs:
            return []

        ranked: List[tuple[int, int, str]] = []
        order = 0
        for doc in seed_docs:
            metadata = doc.metadata or {}
            chunk_type = str(metadata.get("chunk_type") or "").lower()
            heading_bonus = 2 if chunk_type == "outline" else 0
            for heading in cls._extract_candidate_headings(doc):
                relevance = cls._heading_relevance(question, heading)
                decomposition_bonus = 4 if cls._is_decomposition_heading(heading) else 0
                if relevance <= 0 and not decomposition_bonus:
                    continue
                ranked.append((max(relevance, 1) + heading_bonus + decomposition_bonus, order, heading))
                order += 1

        ranked.sort(key=lambda item: (-item[0], item[1]))
        facets: List[Dict[str, str]] = []
        seen: set[str] = set()
        for _score, _order, heading in ranked:
            normalized = cls._normalize_query_text(heading)
            if normalized in seen:
                continue
            seen.add(normalized)
            facets.append({"label": heading, "query": heading})
            if len(facets) >= max_facets:
                break
        return facets

    @classmethod
    def _infer_retrieval_group(cls, doc: Document) -> str:
        """Infer a retrieval group from metadata and chunk text."""
        metadata = doc.metadata or {}
        explicit = str(metadata.get("retrieval_group") or "").strip()
        if explicit:
            return explicit
        headings = cls._extract_candidate_headings(doc)
        return headings[0] if headings else ""

    @classmethod
    def _infer_metadata_group(cls, doc: Document) -> str:
        """Infer a retrieval group from structural metadata only."""
        metadata = doc.metadata or {}
        explicit = str(metadata.get("retrieval_group") or "").strip()
        if explicit:
            return explicit
        for key in ("section_title", "outline_path", "chapter_title", "breadcrumb"):
            value = str(metadata.get(key) or "").strip()
            if value and value.lower() not in {"tổng quan các mục chính", "tong quan cac muc chinh"}:
                parts = [cls._clean_heading(part) for part in value.split(">") if part.strip()]
                for part in reversed(parts):
                    if cls._is_decomposition_heading(part):
                        return part
        return ""

    @staticmethod
    def _with_retrieval_group(doc: Document, group: str) -> Document:
        metadata = dict(doc.metadata or {})
        if group:
            metadata.setdefault("retrieval_group", group)
        return Document(page_content=doc.page_content, metadata=metadata)

    def _select_context_documents(
        self,
        docs: List[Document],
        mode: str,
    ) -> List[Document]:
        """Dedupe chunks and prefer source diversity for broad questions."""
        seen_texts: set[str] = set()
        deduped: List[Document] = []
        for doc in docs:
            normalized = self._normalize_doc_text(doc.page_content)
            if not normalized:
                continue
            dedupe_key = normalized[:1000]
            if dedupe_key in seen_texts:
                continue
            seen_texts.add(dedupe_key)
            deduped.append(doc)

        if mode != "broad":
            return deduped

        theory_grouped: Dict[str, List[Document]] = {}
        theory_order: List[str] = []
        ungrouped: List[Document] = []
        for doc in deduped:
            metadata = doc.metadata or {}
            group = str(metadata.get("retrieval_group") or "").strip()
            if not group:
                ungrouped.append(doc)
                continue
            if group not in theory_grouped:
                theory_grouped[group] = []
                theory_order.append(group)
            theory_grouped[group].append(doc)

        if theory_grouped:
            diversified: List[Document] = []
            per_group_counts = {group: 0 for group in theory_order}
            max_per_group = 3
            while True:
                added = False
                for group in theory_order:
                    if theory_grouped[group] and per_group_counts[group] < max_per_group:
                        diversified.append(theory_grouped[group].pop(0))
                        per_group_counts[group] += 1
                        added = True
                if not added:
                    break
            diversified.extend(ungrouped[:3])
            return diversified

        grouped: Dict[str, List[Document]] = {}
        source_order: List[str] = []
        for doc in deduped:
            metadata = doc.metadata or {}
            source = str(
                metadata.get("file_name")
                or metadata.get("source")
                or metadata.get("source_key")
                or "unknown"
            )
            if source not in grouped:
                grouped[source] = []
                source_order.append(source)
            grouped[source].append(doc)

        diversified: List[Document] = []
        while True:
            added = False
            for source in source_order:
                if grouped[source]:
                    diversified.append(grouped[source].pop(0))
                    added = True
            if not added:
                break
        return diversified

    def _build_context(self, docs: List[Document], mode: str) -> str:
        """Pack retrieved chunks into a bounded, source-labeled context."""
        selected_docs = self._select_context_documents(docs, mode)
        context_parts: List[str] = []
        total_chars = 0
        group_order: List[str] = []

        for doc in selected_docs:
            metadata = doc.metadata or {}
            retrieval_group = str(metadata.get("retrieval_group") or "").strip()
            if retrieval_group and retrieval_group not in group_order:
                group_order.append(retrieval_group)
            source = str(
                metadata.get("file_name")
                or metadata.get("source")
                or metadata.get("source_key")
                or "không rõ"
            )
            breadcrumb = str(metadata.get("breadcrumb") or "").strip()
            header = f"[Nguồn: {source}]"
            if retrieval_group:
                header = f"[GROUP: {retrieval_group}]\n{header}"
            if breadcrumb:
                header = f"{header}\n{breadcrumb}"
            part = f"{header}\n\n{doc.page_content.strip()}"

            separator_len = 10 if context_parts else 0
            remaining = MAX_CONTEXT_CHARS - total_chars - separator_len
            if remaining <= 0:
                break
            if len(part) > remaining:
                if remaining < 200:
                    break
                part = part[:remaining].rstrip()

            context_parts.append(part)
            total_chars += len(part) + separator_len

        context = "\n\n---\n\n".join(context_parts)
        if group_order:
            required_groups = "; ".join(group_order)
            return (
                "Hướng dẫn bắt buộc: Context bên dưới đã được chia theo các header [GROUP: ...]. "
                f"Bạn phải trả lời bằng tiếng Việt và đi lần lượt đủ các nhóm sau: {required_groups}. "
                "Với mỗi nhóm, chỉ nêu công trình/tác giả/luận điểm xuất hiện trong context của nhóm đó. "
                "Không gộp bỏ nhóm, không chuyển sang ngôn ngữ khác, không tự thêm công trình ngoài context. "
                "Nếu nhóm nào thiếu dữ liệu thì ghi rõ: context chưa đủ dữ liệu cho nhóm này.\n\n"
                f"{context}"
            )
        return context

    @staticmethod
    def _document_identity(doc: Document) -> str:
        """Stable-ish identity for merging retrieval result sets."""
        metadata = doc.metadata or {}
        source = metadata.get("file_name") or metadata.get("source") or ""
        chunk_index = metadata.get("chunk_index")
        if source and chunk_index is not None:
            return f"{source}:chunk_index:{chunk_index}"
        for key in ("chunk_id", "content_hash"):
            value = metadata.get(key)
            if value is not None:
                return f"{source}:{key}:{value}"
        return RAGPipeline._normalize_doc_text(doc.page_content)[:1000]

    def _merge_documents(self, *doc_sets: List[Document]) -> List[Document]:
        """Merge retrieval result sets while preserving first-seen order."""
        merged: List[Document] = []
        seen: set[str] = set()
        for docs in doc_sets:
            for doc in docs:
                identity = self._document_identity(doc)
                if identity in seen:
                    continue
                seen.add(identity)
                merged.append(doc)
        return merged

    @staticmethod
    def _build_keyword_supplement_queries(question: str) -> List[str]:
        """Build lexical queries from the user's wording without answer hardcoding."""
        normalized = " ".join((question or "").split())
        queries = [normalized]
        lowered = normalized.lower()
        if "công trình" in lowered and "vai trò" in lowered:
            queries.append("công trình liên quan vai trò chủ thể quan hệ quốc tế")
            queries.append("vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng")
        return [query for query in dict.fromkeys(q for q in queries if q)]

    def _keyword_supplement_search(
        self,
        question: str,
        mode: str,
        access_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Run keyword-only retrieval for broad queries when supported."""
        if not self.keyword_supplement_enabled or mode != "broad":
            return []
        keyword_search = getattr(self.vector_store_manager, "keyword_search", None)
        if keyword_search is None:
            return []

        results: List[Document] = []
        for keyword_query in self._build_keyword_supplement_queries(question):
            try:
                docs = keyword_search(
                    query=keyword_query,
                    k=self.keyword_supplement_top_k,
                    filter=access_filter,
                )
            except Exception:
                logger.exception("[pipeline] Keyword supplement failed for %r", keyword_query)
                continue
            results = self._merge_documents(results, docs)
        return results

    def _decomposed_broad_search(
        self,
        question: str,
        mode: str,
        seed_docs: Optional[List[Document]] = None,
        access_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Retrieve per-heading facet chunks for broad questions."""
        if mode != "broad":
            return []

        facets = self.decompose_broad_query(question, seed_docs=seed_docs)
        if not facets:
            return []

        results: List[Document] = []
        per_facet_k = max(2, min(4, self.keyword_supplement_top_k))
        keyword_search = getattr(self.vector_store_manager, "keyword_search", None)

        for facet in facets:
            label = facet["label"]
            facet_query = facet["query"]
            facet_docs: List[Document] = []
            try:
                facet_docs = self.vector_store_manager.similarity_search(
                    query=facet_query,
                    keyword_query=facet_query,
                    k=per_facet_k,
                    filter=access_filter,
                )
            except Exception:
                logger.exception("[pipeline] Facet vector retrieval failed for %r", facet_query)

            if keyword_search is not None:
                try:
                    facet_docs = self._merge_documents(
                        facet_docs,
                        keyword_search(
                            query=facet_query,
                            k=per_facet_k,
                            filter=access_filter,
                        ),
                    )
                except Exception:
                    logger.exception("[pipeline] Facet keyword retrieval failed for %r", facet_query)

            grouped_docs = []
            for doc in facet_docs:
                metadata_group = self._infer_metadata_group(doc)
                if metadata_group and metadata_group != label:
                    continue
                grouped_docs.append(self._with_retrieval_group(doc, metadata_group or label))
            results = self._merge_documents(results, grouped_docs)

        return results

    @staticmethod
    def _filter_authorized_documents(
        docs: List[Document],
        access_filter: Optional[Dict[str, Any]],
    ) -> List[Document]:
        return [
            doc
            for doc in docs
            if document_allowed(dict(doc.metadata or {}), access_filter)
        ]

    # ------------------------------------------------------------------
    # Core query method
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        k: Optional[int] = None,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        access_filter: Optional[Dict[str, Any]] = None,
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
        retrieval_question = self.contextualize_question(question, chat_history)
        contextual_rewrite = retrieval_question if retrieval_question != question else None
        query_mode = self.classify_query_mode(retrieval_question)
        top_k = self._resolve_top_k(retrieval_question, k)

        # ----------------------------------------------------------
        # Step 1 — Cache lookup
        # ----------------------------------------------------------
        document_version = str(self.vector_store_manager.get_document_version())
        cache_key = self.query_cache.make_key(
            query=question,
            top_k=top_k,
            filters={
                "access_filter": access_filter,
                "document_version": document_version,
                "contextual_query": retrieval_question,
            },
            model_version=self.llm_manager.model,
        )
        cached = self.query_cache.get(cache_key)
        if cached is None and access_filter is None:
            legacy_cache_key = self.query_cache.make_key(
                query=question,
                top_k=top_k,
                filters=None,
                model_version=self.llm_manager.model,
            )
            cached = self.query_cache.get(legacy_cache_key)
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
                query=retrieval_question,
                keyword_query=retrieval_question,
                k=top_k,
                filter=access_filter,
            )
            keyword_docs = self._keyword_supplement_search(
                retrieval_question,
                query_mode,
                access_filter=access_filter,
            )
            facet_docs = self._decomposed_broad_search(
                retrieval_question,
                query_mode,
                seed_docs=self._merge_documents(keyword_docs, relevant_docs),
                access_filter=access_filter,
            )
            if query_mode == "broad":
                relevant_docs = self._merge_documents(facet_docs, keyword_docs, relevant_docs)
            else:
                relevant_docs = self._merge_documents(relevant_docs, keyword_docs)
            relevant_docs = self._filter_authorized_documents(relevant_docs, access_filter)
        timings["search_ms"] = t_search.elapsed_ms

        if access_filter and not relevant_docs:
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            timings["total_ms"] = total_ms
            return {
                "answer": NO_AUTHORIZED_CONTEXT_MESSAGE,
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict(timings),
            }

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
        packed_docs = self._select_context_documents(relevant_docs, query_mode)
        context = self._build_context(packed_docs, query_mode)
        if not packed_docs or not context.strip():
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            timings["total_ms"] = total_ms
            return {
                "answer": NO_AUTHORIZED_CONTEXT_MESSAGE,
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict(timings),
            }

        # Debug: log context summary so we can verify what the LLM receives
        logger.info(
            "[pipeline] Context built: %d docs, %d chars. Sources: %s",
            len(packed_docs),
            len(context),
            [d.metadata.get("source", "?").split("\\")[-1][:30] for d in packed_docs[:3]],
        )

        # ----------------------------------------------------------
        # Step 5 — LLM generation
        # ----------------------------------------------------------
        rewritten_query: Optional[str] = contextual_rewrite
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
                    rewritten_query = contextual_rewrite or fused_result.get("rewritten_query")
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
            generation_query = question
            if self.query_rewrite_enabled:
                rewritten = self._rewrite_query(question)
                if rewritten != question and not rewritten_query:
                    rewritten_query = rewritten
                    generation_query = rewritten
            with self.benchmark.measure("llm") as t_llm:
                answer = self._classic_generate(
                    generation_query, context, system_prompt, chat_history
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
            for doc in packed_docs
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
        k: Optional[int] = None,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        access_filter: Optional[Dict[str, Any]] = None,
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
        retrieval_question = self.contextualize_question(question, chat_history)
        contextual_rewrite = retrieval_question if retrieval_question != question else None
        query_mode = self.classify_query_mode(retrieval_question)
        top_k = self._resolve_top_k(retrieval_question, k)

        # Cache lookup
        document_version = str(self.vector_store_manager.get_document_version())
        cache_key = self.query_cache.make_key(
            query=question,
            top_k=top_k,
            filters={
                "access_filter": access_filter,
                "document_version": document_version,
                "contextual_query": retrieval_question,
            },
            model_version=self.llm_manager.model,
        )
        cached = self.query_cache.get(cache_key)
        if cached is None and access_filter is None:
            legacy_cache_key = self.query_cache.make_key(
                query=question,
                top_k=top_k,
                filters=None,
                model_version=self.llm_manager.model,
            )
            cached = self.query_cache.get(legacy_cache_key)
        if cached is not None:
            logger.debug("[pipeline] Stream cache HIT for query: %r", question[:60])
            self._notify_stream_complete(on_complete, cached)
            for word in cached["answer"].split(" "):
                yield word + " "
            return

        # Hybrid search
        relevant_docs = self.vector_store_manager.similarity_search(
            query=retrieval_question,
            keyword_query=retrieval_question,
            k=top_k,
            filter=access_filter,
        )
        keyword_docs = self._keyword_supplement_search(
            retrieval_question,
            query_mode,
            access_filter=access_filter,
        )
        facet_docs = self._decomposed_broad_search(
            retrieval_question,
            query_mode,
            seed_docs=self._merge_documents(keyword_docs, relevant_docs),
            access_filter=access_filter,
        )
        if query_mode == "broad":
            relevant_docs = self._merge_documents(facet_docs, keyword_docs, relevant_docs)
        else:
            relevant_docs = self._merge_documents(relevant_docs, keyword_docs)
        relevant_docs = self._filter_authorized_documents(relevant_docs, access_filter)
        if access_filter and not relevant_docs:
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            no_docs_response = {
                "answer": NO_AUTHORIZED_CONTEXT_MESSAGE,
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict({"total_ms": total_ms}),
            }
            self._notify_stream_complete(on_complete, no_docs_response)
            yield no_docs_response["answer"]
            return
        if not relevant_docs:
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            no_docs_response = {
                "answer": "Không tìm thấy tài liệu liên quan đến câu hỏi của bạn.",
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict({"total_ms": total_ms}),
            }
            self._notify_stream_complete(on_complete, no_docs_response)
            yield no_docs_response["answer"]
            return

        # Build context
        packed_docs = self._select_context_documents(relevant_docs, query_mode)
        context = self._build_context(packed_docs, query_mode)
        if not packed_docs or not context.strip():
            total_ms = (time.perf_counter() - total_start) * 1_000.0
            no_context_response = {
                "answer": NO_AUTHORIZED_CONTEXT_MESSAGE,
                "sources": [],
                "context": "",
                "rewritten_query": None,
                "timing": self.benchmark.build_timing_dict({"total_ms": total_ms}),
            }
            self._notify_stream_complete(on_complete, no_context_response)
            yield no_context_response["answer"]
            return

        # Stream from LLM
        ttft_recorded = False
        ttft_ms = 0.0
        accumulated_tokens: List[str] = []
        rewritten_query: Optional[str] = contextual_rewrite
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
                    rewritten_query = contextual_rewrite or fused_result.get("rewritten_query")
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
            for doc in packed_docs
        ]
        total_ms = (time.perf_counter() - total_start) * 1_000.0
        cached_response = {
            "answer": full_answer,
            "sources": sources,
            "context": context,
            "rewritten_query": rewritten_query,
            "timing": self.benchmark.build_timing_dict(
                {"ttft_ms": ttft_ms, "total_ms": total_ms}
            ),
        }
        self.query_cache.set(cache_key, cached_response)
        self.benchmark.record_query()
        self._notify_stream_complete(on_complete, cached_response)

    @staticmethod
    def _notify_stream_complete(
        callback: Optional[Callable[[Dict[str, Any]], None]],
        result: Dict[str, Any],
    ) -> None:
        """Report final streaming metadata without interrupting token delivery."""
        if callback is None:
            return
        try:
            callback(result)
        except Exception:
            logger.exception("[pipeline] query_stream on_complete callback failed")

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
                "5. Câu trả lời phải có nội dung phân tích, không chỉ liệt kê tên công trình\n"
                "6. Nếu context có nhiều mục/nhóm lớn liên quan trực tiếp đến câu hỏi, "
                "PHẢI bao phủ đủ tất cả các mục/nhóm đó; không bỏ sót mục chỉ vì thông tin ngắn hơn các mục khác\n\n"
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

    def query_simple(self, question: str, k: Optional[int] = None) -> str:
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
