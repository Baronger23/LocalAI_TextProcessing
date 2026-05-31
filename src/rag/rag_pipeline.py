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
    CACHE_TTL_SECONDS,
    DEFAULT_TOP_K,
    KEYWORD_SUPPLEMENT_ENABLED,
    KEYWORD_SUPPLEMENT_TOP_K,
    MAX_CONTEXT_CHARS,
    MMR_ENABLED,
    MMR_FETCH_K,
    MMR_LAMBDA,
    PROMPT_FUSION_ENABLED,
    QUERY_CACHE_ENABLED,
    QUERY_REWRITE_ENABLED,
    STREAMING_ENABLED,
)
from src.document_loader import DocumentProcessor
from src.embeddings import EmbeddingManager
from src.llm import LLMManager
from src.rag.benchmark import PerformanceBenchmark
from src.rag.exceptions import LLMQueueFullError, LLMTimeoutError
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
    # Thêm: chỉ định hạn mức / quy định trong hội thoại
    "hạn mức này",
    "han muc nay",
    "hạn mức đó",
    "han muc do",
    "mức này",
    "muc nay",
    "mức đó",
    "muc do",
    "quy định này",
    "quy dinh nay",
    "quy định đó",
    "quy dinh do",
    "chính sách này",
    "chinh sach nay",
    # Thêm: chỉ định thời gian gần đây trong hội thoại
    "nãy",
    "nay",
    "vừa",
    "vua",
    "trên",
    "tren",
    "đó",
    "do",
)

_FOLLOW_UP_TOKEN_MARKERS = {"no", "ho", "do", "tren", "nay", "vua"}

_HEADING_STOPWORDS = {
    "nhung", "mot", "so", "va", "hoac", "duoc", "tu", "sau",
    "tai", "khi", "nay", "do", "nao", "nhieu", "bao", "viec", "nghi",
    "nhan", "vien", "toi", "lam", "co", "khong", "phai", "theo", "voi",
    "day", "thang", "nam", "tuan", "gio", "phut", "giay"
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
        for msg in chat_history[-10:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = str(msg.get("content", "")).strip()
            if content:
                lines.append(f"{role}: {content[:700]}")
        return "\n".join(lines)

    def contextualize_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        rolling_summary: Optional[str] = None,
    ) -> str:
        """Rewrite vague follow-up questions into standalone retrieval queries.

        The gate is intentionally conservative so ordinary standalone questions
        do not pay an extra LLM call.

        Args:
            question: The user's current question.
            chat_history: Recent conversation turns for context resolution.
            rolling_summary: Optional short summary of the conversation so far.
                Injected into the rewrite prompt so the LLM can resolve
                references like "hạn mức này" or "chuyến công tác đó" correctly.
        """
        original = (question or "").strip()
        if not self._needs_contextual_rewrite(original, chat_history):
            return original

        history_text = self._format_rewrite_history(chat_history)
        if not history_text and not rolling_summary:
            return original

        summary_block = ""
        if rolling_summary and rolling_summary.strip():
            summary_block = f"""Tóm tắt hội thoại hiện tại:
{rolling_summary.strip()}

"""

        prompt = f"""Viết lại câu hỏi hiện tại thành một câu hỏi độc lập để tìm kiếm tài liệu.
Dựa vào tóm tắt và lịch sử hội thoại dưới đây. Không trả lời câu hỏi. Không thêm thông tin mới.
Thực hiện viết lại cụ thể: thay thế các từ chỉ định mơ hồ bằng giá trị thực tế từ ngữ cảnh.
Ví dụ: "hạn mức này" → "hạn mức phòng khách sạn 2.000.000 VND tại TP.HCM"
Ví dụ: "chật này" → tên chính sách cụ thể đang được nói đến.

{summary_block}Lịch sử gần nhất:
{history_text}

Câu hỏi hiện tại:
{original}

Câu hỏi độc lập (viết lại rõ ràng, thay thế từ chỉ định):"""

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
            is_bullet = stripped.startswith(("-", "•"))
            if is_bullet and len(stripped) < 50 and len(stripped.split()) < 8:
                candidates.append(stripped)
            elif "các công trình" in stripped.lower() or "chịu ảnh hưởng" in stripped.lower():
                candidates.append(stripped)
            elif re.match(r"^\s*\d+(?:\.\d+)*\.?\s+[A-ZÀ-Ỹ]", stripped):
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

    def _classify_chunk(self, doc: Document) -> str:
        """Classify chunk as 'outline', 'background', or 'direct' evidence."""
        metadata = doc.metadata or {}
        chunk_type = str(metadata.get("chunk_type") or "").lower()
        if chunk_type == "outline":
            return "outline"

        outline_keywords = {"tổng quan các mục chính", "tong quan cac muc chinh", "dàn ý", "dan y", "mục lục", "muc luc"}
        content_lower = (doc.page_content or "").lower()
        if any(kw in content_lower for kw in outline_keywords):
            return "outline"

        theory_keywords = {"lý thuyết", "khái niệm", "lý luận", "cơ sở lý luận", "background", "theory", "concept"}
        metadata_text = ""
        for key in ("section_title", "outline_path", "chapter_title", "breadcrumb"):
            metadata_text += " " + str(metadata.get(key) or "").lower()

        if any(kw in metadata_text for kw in theory_keywords):
            return "background"

        return "direct"

    def _select_context_documents(
        self,
        docs: List[Document],
        mode: str,
        question: Optional[str] = None,
    ) -> List[Document]:
        """Dedupe chunks and select based on quota (70% Direct, 20% Outline, 10% Background)

        with round-robin group balancing for Direct Evidence.
        """
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

        if not deduped:
            return []

        # Classification
        direct_chunks: List[Document] = []
        outline_chunks: List[Document] = []
        background_chunks: List[Document] = []

        for doc in deduped:
            ctype = self._classify_chunk(doc)
            if ctype == "outline":
                outline_chunks.append(doc)
            elif ctype == "background":
                background_chunks.append(doc)
            else:
                direct_chunks.append(doc)

        # Apply Group Balancing (Round-Robin) to Direct chunks
        direct_grouped: Dict[str, List[Document]] = {}
        direct_group_order: List[str] = []
        direct_ungrouped: List[Document] = []

        for doc in direct_chunks:
            metadata = doc.metadata or {}
            group = str(metadata.get("retrieval_group") or "").strip()
            if not group:
                group = self._infer_retrieval_group(doc)
            if not group:
                direct_ungrouped.append(doc)
                continue
            if group not in direct_grouped:
                direct_grouped[group] = []
                direct_group_order.append(group)
            direct_grouped[group].append(doc)

        balanced_direct: List[Document] = []
        max_per_group = 3
        per_group_counts = {g: 0 for g in direct_group_order}

        while True:
            added = False
            for group in direct_group_order:
                if direct_grouped[group] and per_group_counts[group] < max_per_group:
                    balanced_direct.append(direct_grouped[group].pop(0))
                    per_group_counts[group] += 1
                    added = True
            if not added:
                break

        # Append ungrouped or residual direct chunks
        remaining_direct = list(direct_ungrouped)
        for group in direct_group_order:
            remaining_direct.extend(direct_grouped[group])
        balanced_direct.extend(remaining_direct)

        # Quota allocation by characters
        max_chars = MAX_CONTEXT_CHARS
        direct_limit = int(max_chars * 0.70)
        outline_limit = int(max_chars * 0.20)
        theory_limit = int(max_chars * 0.10)

        selected_direct: List[Document] = []
        selected_outline: List[Document] = []
        selected_background: List[Document] = []

        def pack_group(chunks: List[Document], limit: int) -> tuple[List[Document], int]:
            packed: List[Document] = []
            current_len = 0
            for d in chunks:
                metadata = d.metadata or {}
                source = str(metadata.get("file_name") or metadata.get("source") or "unknown")
                part_len = len(source) + len(d.page_content) + 50
                if current_len + part_len <= limit:
                    packed.append(d)
                    current_len += part_len
                else:
                    break
            return packed, current_len

        selected_direct, direct_len = pack_group(balanced_direct, direct_limit)
        selected_outline, outline_len = pack_group(outline_chunks, outline_limit)
        selected_background, background_len = pack_group(background_chunks, theory_limit)

        # Fill remaining quota dynamically with unused chunks (prefer Direct)
        selected_ids = {id(d) for d in selected_direct + selected_outline + selected_background}
        remaining_all = []
        remaining_all.extend([d for d in balanced_direct if id(d) not in selected_ids])
        remaining_all.extend([d for d in outline_chunks if id(d) not in selected_ids])
        remaining_all.extend([d for d in background_chunks if id(d) not in selected_ids])

        total_len = direct_len + outline_len + background_len
        extra_limit = max_chars - total_len

        selected_extra = []
        if extra_limit > 0 and remaining_all:
            selected_extra, _ = pack_group(remaining_all, extra_limit)

        return selected_direct + selected_outline + selected_background + selected_extra

    def _build_context(self, docs: List[Document], mode: str, question: Optional[str] = None) -> str:
        """Pack retrieved chunks into a bounded, source-labeled context."""
        selected_docs = self._select_context_documents(docs, mode, question)
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
                "Với mỗi nhóm, chỉ nêu thông tin, quy định, số liệu hoặc luận điểm xuất hiện trong context của nhóm đó. "
                "Không gộp bỏ nhóm, không chuyển sang ngôn ngữ khác, không tự thêm thông tin ngoài context. "
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
    def _build_outline_seed_queries(question: str) -> List[str]:
        """Queries for discovering structural outline chunks before facets."""
        queries = [
            "Các mục chính trong tài liệu",
            "Tổng quan các mục chính",
        ]
        normalized = " ".join((question or "").split())
        if normalized:
            queries.append(normalized)
        return [query for query in dict.fromkeys(queries) if query]

    @staticmethod
    def _build_keyword_supplement_queries(question: str) -> List[str]:
        """Build lexical queries from the user's wording without answer hardcoding."""
        normalized = " ".join((question or "").split())
        queries = [normalized]
        tokens = [
            token
            for token in re.findall(r"[\wÀ-ỹ]+", normalized, flags=re.UNICODE)
            if len(token) >= 3
        ]
        if len(tokens) >= 6:
            queries.append(" ".join(tokens[:12]))
        return [query for query in dict.fromkeys(q for q in queries if q)]

    @staticmethod
    def _extract_proper_nouns(question: str) -> List[str]:
        """Extract capitalized tokens (proper nouns / author names / acronyms) from question.

        In Vietnamese academic questions, author names and specialized terms are
        typically written with initial capitals (e.g., "Acharya", "Weatherbee",
        "ARF", "ASEAN"). This heuristic collects such tokens so a dedicated
        entity-focused keyword search can be run to boost recall for specific names.

        Returns a list of unique capitalized tokens >= 3 chars, excluding common
        Vietnamese stop-words that happen to be capitalized at sentence start.
        """
        # Only words that are UNAMBIGUOUSLY function words in Vietnamese —
        # prepositions, conjunctions, pronouns — regardless of domain.
        # We intentionally exclude words like "Dong", "Hoa", "Van", "Quoc"
        # which could be part of company names, project codes, or person names
        # in non-academic documents (e.g., company policies, project files).
        vn_stop_caps = {
            # Vietnamese function words (with diacritics)
            "Các", "Những", "Theo", "Với", "Của", "Trong", "Về", "Và",
            "Hay", "Tại", "Khi", "Như", "Đây", "Này", "Đó", "Nào",
            "Có", "Không", "Được", "Sau", "Từ", "Bởi", "Vì", "Bằng",
            "Cho", "Đến", "Sao", "Vào", "Ra", "Lên", "Xuống",
            # Common Vietnamese sentence-starting words that should not trigger entity boost
            "Hạn", "Mức", "Thời", "Ngày", "Tháng", "Năm", "Người", "Nhân", "Việc",
            "Quy", "Chính", "Bản", "Bảng", "Đơn", "Hóa", "Tiền", "Danh", "Mục", "Sách",
            "Công", "Cấp", "Ty", "Phòng", "Ban", "Khối", "Hồ", "Sơ", "Chuyến", "Bay",
            "Hạng", "Vé", "Phụ", "Ăn", "Uống", "Khách", "Sạn", "Chi", "Phí", "Hoàn",
            "Ứng", "Yêu", "Cầu", "Tài", "Liệu", "Quyết", "Toán", "Thanh",
            # Common query pronouns and sentence starters
            "Tôi", "Hãy", "Anh", "Chị", "Bạn", "Thế", "Nếu", "Làm", "Nãy", "Đó",
            # Same words without diacritics (ASCII-transliterated queries)
            "Cac", "Nhung", "Theo", "Voi", "Cua", "Trong", "Ve", "Va",
            "Hay", "Tai", "Khi", "Nhu", "Day", "Nay", "Do", "Nao",
            "Co", "Khong", "Duoc", "Sau", "Tu", "Boi", "Vi", "Bang",
            "Cho", "Den", "Sao", "Vao", "Len",
            "Han", "Muc", "Thoi", "Ngay", "Thang", "Nam", "Nguoi", "Nhan", "Viec",
            "Quy", "Chinh", "Ban", "Bang", "Don", "Hoa", "Tien", "Danh", "Muc", "Sach",
            "Cong", "Cap", "Ty", "Phong", "Ban", "Khoi", "Ho", "So", "Chuyen", "Bay",
            "Hang", "Ve", "Phu", "An", "Uong", "Khach", "San", "Chi", "Phi", "Hoan",
            "Ung", "Yeu", "Cau", "Tai", "Lieu", "Quyet", "Toan", "Thanh",
            "Toi", "Hay", "Anh", "Chi", "Ban", "The", "Neu", "Lam", "Nay"
        }
        tokens = re.findall(r"[\wÀ-ỹ]+", question)
        seen: set[str] = set()
        result: List[str] = []
        for index, token in enumerate(tokens):
            if token and token[0].isupper():
                if token in vn_stop_caps or token in seen or len(token) < 3:
                    continue
                if index == 0 and not token.isupper():
                    next_token = tokens[1] if len(tokens) > 1 else ""
                    if not (next_token and next_token[0].isupper()):
                        continue
                seen.add(token)
                result.append(token)
        return result

    def _entity_boost_search(
        self,
        question: str,
        access_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Run a focused keyword search on proper nouns found in the question.

        When a question mentions specific authors, organizations, or technical
        terms (e.g., "Amitav Acharya", "Donald Weatherbee"), the hybrid search
        may rank general ASEAN chunks higher than the targeted ones because OR-
        tsquery weights common terms equally. This method issues a *separate*
        keyword-only search with just the capitalized entities, ensuring those
        chunks surface in the merged result set.

        Docs returned here are tagged with ``entity_boosted=True`` so that
        ``_retrieve_documents`` can pin them to the top of the final list after
        reranking, preventing the reranker from burying name-specific chunks.
        """
        keyword_search = getattr(self.vector_store_manager, "keyword_search", None)
        if keyword_search is None:
            return []
        proper_nouns = self._extract_proper_nouns(question)
        # Only run entity boost when there are specific named entities beyond
        # common acronyms that appear in every document.
        common_acronyms = {
            "ASEAN", "ARF", "EAS", "ADMM", "APEC", "CPTPP", "RCEP",
            "HCM", "VND", "HRBP", "KPI", "DPIA", "VPN", "CEO", "BOD",
            "HN", "TP", "USD", "PDF", "RAG", "FTS", "RRF", "MMR", "LLM",
            "MANAGER", "EMPLOYEE", "ADMIN", "DIRECTOR", "OFFICER", "STAFF",
            "DIGITAL", "COMPANY", "TNHH", "AN", "PHÁT",
            "QUY", "ĐỊNH", "CHÍNH", "SÁCH", "TÌNH", "HUỐNG", "HƯỚNG", "DẪN",
            "DOMESTIC", "MEAL", "FLIGHT", "CLASS", "CLAIM", "DEADLINE",
            "TRAVEL", "EXPENSE", "POLICY", "TRAVEL_EXPENSE_POLICY"
        }
        specific_nouns = [n for n in proper_nouns if n.upper() not in common_acronyms]
        if not specific_nouns:
            return []

        # Search each specific noun SEPARATELY — combining into one OR-tsquery
        # causes ts_rank to favour ASEAN-heavy chunks over name-specific ones.
        all_docs: List[Document] = []
        seen_ids: set = set()
        for noun in specific_nouns:
            try:
                docs = keyword_search(
                    query=noun,
                    k=3,
                    filter=access_filter,
                )
                for doc in docs:
                    doc_id = doc.metadata.get("chunk_id") or id(doc)
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        new_meta = dict(doc.metadata or {})
                        new_meta["entity_boosted"] = True
                        all_docs.append(Document(page_content=doc.page_content, metadata=new_meta))
            except Exception:
                logger.exception("[pipeline] Entity boost search failed for noun %r", noun)

        logger.debug(
            "[pipeline] entity_boost_search found %d docs for nouns=%s",
            len(all_docs), specific_nouns,
        )
        return all_docs


    def _outline_seed_search(
        self,
        question: str,
        mode: str,
        access_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Find outline/heading chunks first so broad queries can fan out by data."""
        if mode != "broad":
            return []
        keyword_search = getattr(self.vector_store_manager, "keyword_search", None)
        if keyword_search is None:
            return []

        results: List[Document] = []
        for seed_query in self._build_outline_seed_queries(question):
            try:
                docs = keyword_search(
                    query=seed_query,
                    k=max(4, min(8, self.keyword_supplement_top_k)),
                    filter=access_filter,
                )
            except Exception:
                logger.exception("[pipeline] Outline seed search failed for %r", seed_query)
                continue

            outline_docs = [
                doc for doc in docs
                if str((doc.metadata or {}).get("chunk_type") or "").lower() == "outline"
                or "các mục chính trong tài liệu" in (doc.page_content or "").lower()
            ]
            results = self._merge_documents(results, outline_docs or docs[:2])
        return results

    def _keyword_supplement_search(
        self,
        question: str,
        mode: str,
        access_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Run keyword-only retrieval to catch exact terms, anchors, and headings."""
        if not self.keyword_supplement_enabled:
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

    @classmethod
    def _metadata_evidence_text(cls, doc: Document) -> str:
        metadata = doc.metadata or {}
        parts = []
        for key in ("retrieval_group", "section_title", "outline_path", "chapter_title", "breadcrumb"):
            value = str(metadata.get(key) or "").strip()
            if value:
                parts.append(value)

        # Add translated terms to boost relevance of English metadata keys
        text = " ".join(parts).lower()
        translations = {
            "hcm hotel manager": "khach san hcm quan ly manager",
            "domestic meal": "phu cap an uong noi dia meal",
            "flight class": "hang ve may bay flight class",
            "claim deadline": "han chot thoi han nop ho so hoan ung claim deadline",
            "taxi receipt": "hoa don taxi receipt",
            "three_quotes": "ba bao gia three quotes",
            "po_before_invoice": "don dat hang truoc hoa don po before invoice",
            "advance_settlement": "tam ung hoan ung thanh toan advance settlement",
            "payment_term": "dieu khoan thanh toan han muc payment term",
            "evidence": "bang chung chung tu evidence",
            "exception": "ngoai le exception",
            "password": "mat khau password",
            "privileged_rotation": "xoay vong mat khau dac quyen privileged rotation",
            "screen_lock": "khoa man hinh screen lock",
            "postmortem": "kiem diem rut kinh nghiem postmortem",
            "evidence_freeze": "dong bang chung tu evidence freeze",
            "retention": "luu tru retention"
        }
        for eng, vie in translations.items():
            if eng in text:
                parts.append(vie)

        return " ".join(parts)

    @classmethod
    def _document_token_set(cls, doc: Document) -> set[str]:
        return cls._heading_tokens(
            f"{cls._metadata_evidence_text(doc)} {doc.page_content or ''}"
        )

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / max(1, len(left | right))

    @classmethod
    def _document_evidence_score(cls, question: str, doc: Document, mode: str) -> float:
        """Score merged candidates by structural match, citation pattern, entity match, and background penalty."""
        metadata = doc.metadata or {}
        query_tokens = cls._heading_tokens(question)
        content_tokens = cls._heading_tokens(doc.page_content or "")
        metadata_text = cls._metadata_evidence_text(doc)
        metadata_tokens = cls._heading_tokens(metadata_text)

        lexical_score = len(query_tokens & content_tokens)
        structural_token_score = len(query_tokens & metadata_tokens) * 2
        heading_score = 0
        for heading in cls._extract_candidate_headings(doc):
            heading_score = max(heading_score, cls._heading_relevance(question, heading))

        score = float(lexical_score + structural_token_score + heading_score * 3)
        score += float(metadata.get("keyword_score") or 0.0) * 2.0
        score += float(metadata.get("vector_score") or 0.0)
        score += float(metadata.get("similarity") or 0.0) * 4.0

        # 1. Citation pattern (+3.0)
        # Nhận diện trích dẫn học thuật dạng Tên tác giả + Năm, ví dụ: (Holsti, 1991), Katzenstein (1996), [Ruggie 1998]
        citation_pattern = r'\b([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)*)\s*(?:[\(\[,]\s*|\s+)(19\d{2}|20[0-2]\d)\b'
        if re.search(citation_pattern, doc.page_content or ""):
            score += 3.0

        # 2. Entity match (+8.0 max)
        # Dùng _extract_proper_nouns để trích xuất tên riêng (tác giả, acronym)
        # chính xác hơn regex cũ vốn ghép cụm từ dài không khớp.
        proper_nouns = cls._extract_proper_nouns(question)
        entity_match_count = 0
        content_lower = (doc.page_content or "").lower()
        for noun in proper_nouns:
            if noun.lower() in content_lower:
                entity_match_count += 1

        if entity_match_count > 0:
            score += min(8.0, entity_match_count * 4.0)

        # 3. Section match (+4.0)
        # Nếu metadata/heading khớp intent của query
        if query_tokens & metadata_tokens:
            score += 4.0

        # 4. Background penalty (-3.0)
        # Trừ điểm nếu chunk thuộc phần lý thuyết học thuật nền tảng mà câu hỏi không yêu cầu lý thuyết
        question_lower = question.lower()
        theory_keywords = {"lý thuyết", "khái niệm", "lý luận", "định nghĩa", "tổng quan", "theory", "concept", "background"}
        is_asking_theory = any(kw in question_lower for kw in theory_keywords)
        is_chunk_theory = any(kw in metadata_text.lower() for kw in theory_keywords)

        if not is_asking_theory and is_chunk_theory:
            score -= 3.0

        if mode == "broad":
            if metadata.get("retrieval_group"):
                score += 5.0
            if cls._infer_metadata_group(doc):
                score += 3.0
            if str(metadata.get("chunk_type") or "").lower() == "outline":
                score += 4.0

        # 5. Domain-specific document boost to resolve tie-breakers on boilerplate sections
        doc_name = metadata.get("file_name", "").lower()
        domain_boosts = {
            "travel_expense": {"khach san", "an uong", "cong tac", "may bay", "hoan ung", "taxi", "chi tieu"},
            "it_security": {"bao mat", "an ninh", "mat khau", "password", "vpn", "mfa", "truy cap", "firewall"},
            "remote_work": {"tu xa", "hybrid", "remote", "tai nha", "work from home"},
            "data_privacy": {"du lieu", "ca nhan", "rieng tu", "privacy", "dsar", "ro ri"}
        }
        normalized_q_lower = cls._normalize_query_text(question)
        for domain, keywords in domain_boosts.items():
            if domain in doc_name:
                if any(kw in normalized_q_lower for kw in keywords):
                    score += 5.0
                    break

        # 6. Penalty for legacy/noise/draft/archive documents unless explicitly queried
        is_query_asking_legacy = any(term in normalized_q_lower for term in ["cu", "legacy", "2024", "nhap", "draft", "luu tru", "archive"])
        if any(term in doc_name for term in ["legacy", "noise", "draft", "archive"]):
            if not is_query_asking_legacy:
                score -= 15.0

        return score

    def _rerank_retrieved_documents(
        self,
        question: str,
        docs: List[Document],
        mode: str,
    ) -> List[Document]:
        """Rerank after vector + keyword + facet merge using document evidence."""
        if not docs:
            return docs
        ranked = [
            (self._document_evidence_score(question, doc, mode), index, doc)
            for index, doc in enumerate(docs)
        ]
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [doc for _score, _index, doc in ranked]

    def _mmr_select_documents(
        self,
        question: str,
        docs: List[Document],
        limit: Optional[int] = None,
    ) -> List[Document]:
        """Lightweight lexical MMR over already-merged candidates."""
        if not self.mmr_enabled or len(docs) <= 2:
            return docs

        target = min(len(docs), limit or self.mmr_fetch_k or len(docs))
        remaining = list(docs)
        selected: List[Document] = []
        token_cache = {id(doc): self._document_token_set(doc) for doc in docs}
        relevance = {
            id(doc): self._document_evidence_score(question, doc, "broad")
            for doc in docs
        }

        while remaining and len(selected) < target:
            if not selected:
                best = max(remaining, key=lambda doc: relevance[id(doc)])
            else:
                best = max(
                    remaining,
                    key=lambda doc: (
                        self.mmr_lambda * relevance[id(doc)]
                        - (1.0 - self.mmr_lambda)
                        * max(
                            self._jaccard(token_cache[id(doc)], token_cache[id(chosen)])
                            for chosen in selected
                        )
                    ),
                )
            selected.append(best)
            remaining.remove(best)

        selected.extend(remaining)
        return selected

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

    def _retrieve_documents(
        self,
        retrieval_question: str,
        query_mode: str,
        top_k: int,
        access_filter: Optional[Dict[str, Any]] = None,
        original_question: Optional[str] = None,
    ) -> List[Document]:
        """Run hybrid, outline seed, facet, rerank, and auth filtering."""
        db_k = max(self.mmr_fetch_k if self.mmr_enabled else 35, top_k + 20)
        relevant_docs = self.vector_store_manager.similarity_search(
            query=retrieval_question,
            keyword_query=retrieval_question,
            k=db_k,
            filter=access_filter,
        )
        if original_question and original_question != retrieval_question:
            orig_docs = self.vector_store_manager.similarity_search(
                query=original_question,
                keyword_query=original_question,
                k=max(15, db_k // 2),
                filter=access_filter,
            )
            relevant_docs = self._merge_documents(relevant_docs, orig_docs)
        outline_seed_docs = self._outline_seed_search(
            retrieval_question,
            query_mode,
            access_filter=access_filter,
        )
        keyword_docs = self._keyword_supplement_search(
            retrieval_question,
            query_mode,
            access_filter=access_filter,
        )
        # Entity boost: run focused keyword search for proper nouns (author names,
        # acronyms) regardless of query mode so specific academic names are retrieved
        # even when they are outranked by common words in a broad OR-tsquery.
        entity_docs = self._entity_boost_search(
            retrieval_question,
            access_filter=access_filter,
        )
        facet_docs = self._decomposed_broad_search(
            retrieval_question,
            query_mode,
            seed_docs=self._merge_documents(outline_seed_docs, keyword_docs, relevant_docs),
            access_filter=access_filter,
        )

        if query_mode == "broad":
            merged_docs = self._merge_documents(
                facet_docs,
                outline_seed_docs,
                keyword_docs,
                entity_docs,
                relevant_docs,
            )
        else:
            merged_docs = self._merge_documents(relevant_docs, entity_docs, keyword_docs)

        authorized_docs = self._filter_authorized_documents(merged_docs, access_filter)

        reranked_docs = self._rerank_retrieved_documents(
            retrieval_question,
            authorized_docs,
            query_mode,
        )

        # Pin entity-boosted docs to the TOP of the ranked list.
        # The reranker tends to bury author-name-specific chunks behind high-overlap
        # generic chunks (e.g., all ASEAN docs share many query tokens).
        # By pinning them first we guarantee the LLM sees those chunks in context.
        if entity_docs:
            pinned = [d for d in reranked_docs if d.metadata.get("entity_boosted")]
            rest = [d for d in reranked_docs if not d.metadata.get("entity_boosted")]
            reranked_docs = pinned + rest

        # Store debug info for logging
        self._last_retrieval_debug = {
            "top_vector": relevant_docs,
            "top_keyword": keyword_docs,
            "after_rrf": authorized_docs,
            "after_rerank": reranked_docs
        }

        return reranked_docs[:top_k]

    def _print_query_debug(
        self,
        question: str,
        retrieval_question: str,
        context: str,
        answer: str
    ) -> None:
        debug_info = getattr(self, "_last_retrieval_debug", {})

        # Safe encoding print for Windows console
        def safe_print(msg: str):
            try:
                print(msg)
            except UnicodeEncodeError:
                # Fallback to ascii representation for console safety
                print(msg.encode('ascii', 'replace').decode())

        safe_print("\n" + "="*80)
        safe_print("🔍 [RAG DEBUG CONTEXT]")
        safe_print("="*80)
        safe_print(f"🔹 Question:\n{question}\n")
        safe_print(f"🔹 Contextual query:\n{retrieval_question or '(None)'}\n")

        safe_print(f"🔹 Top vector chunks ({len(debug_info.get('top_vector', []))}):")
        for i, d in enumerate(debug_info.get("top_vector", [])[:5]):
            source = d.metadata.get("file_name") or d.metadata.get("source") or "?"
            sec = d.metadata.get("section_title") or "?"
            sim = d.metadata.get('similarity') or d.metadata.get('vector_score') or 0.0
            safe_print(f"  [{i+1}] {source} (Section: {sec}) -> score={sim:.4f}")
            safe_print(f"      Text: {d.page_content[:150].strip()}...")

        safe_print(f"\n🔹 Top keyword chunks ({len(debug_info.get('top_keyword', []))}):")
        for i, d in enumerate(debug_info.get("top_keyword", [])[:5]):
            source = d.metadata.get("file_name") or d.metadata.get("source") or "?"
            sec = d.metadata.get("section_title") or "?"
            k_score = d.metadata.get('keyword_score', 0.0)
            safe_print(f"  [{i+1}] {source} (Section: {sec}) -> keyword_score={k_score:.4f}")
            safe_print(f"      Text: {d.page_content[:150].strip()}...")

        safe_print(f"\n🔹 Sau RRF ({len(debug_info.get('after_rrf', []))}):")
        for i, d in enumerate(debug_info.get("after_rrf", [])[:5]):
            source = d.metadata.get("file_name") or d.metadata.get("source") or "?"
            sec = d.metadata.get("section_title") or "?"
            sim = d.metadata.get('similarity') or d.metadata.get('vector_score') or 0.0
            safe_print(f"  [{i+1}] {source} (Section: {sec}) -> rrf_score={sim:.4f}")

        safe_print(f"\n🔹 Sau rerank ({len(debug_info.get('after_rerank', []))}):")
        for i, d in enumerate(debug_info.get("after_rerank", [])[:5]):
            source = d.metadata.get("file_name") or d.metadata.get("source") or "?"
            sec = d.metadata.get("section_title") or "?"
            sim = d.metadata.get('similarity') or d.metadata.get('vector_score') or 0.0
            safe_print(f"  [{i+1}] {source} (Section: {sec}) -> rerank_score={sim:.4f}")

        safe_print(f"\n🔹 Final packed context ({len(context)} chars):")
        safe_print(f"{context[:400].strip()}...\n[TRUNCATED]\n")

        safe_print(f"🔹 Answer:\n{answer}")
        safe_print("="*80 + "\n")

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
        rolling_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query the RAG system and return a complete response dict.

        Args:
            question:     The user's current question.
            k:            Number of documents to retrieve.
            system_prompt: Optional system instruction for the LLM.
            chat_history: Recent conversation turns for context resolution.
            rolling_summary: Short summary of the conversation so far — used
                to resolve references like "hạn mức này" in query rewriting.

        Returns:
            Dict with keys: ``answer``, ``sources``, ``context``,
            ``rewritten_query``, ``timing``.
        """
        total_start = time.perf_counter()
        timings: Dict[str, float] = {}
        retrieval_question = self.contextualize_question(
            question, chat_history, rolling_summary=rolling_summary
        )
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
            pass

        timings["embedding_ms"] = t_embed.elapsed_ms

        # ----------------------------------------------------------
        # Step 3 — Hybrid search
        # ----------------------------------------------------------
        with self.benchmark.measure("search") as t_search:
            relevant_docs = self._retrieve_documents(
                retrieval_question,
                query_mode,
                top_k,
                access_filter=access_filter,
                original_question=question,
            )
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
        packed_docs = self._select_context_documents(
            relevant_docs,
            query_mode,
            question=retrieval_question,
        )
        context = self._build_context(packed_docs, query_mode, question=retrieval_question)
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

        # Print debug context
        self._print_query_debug(
            question=question,
            retrieval_question=retrieval_question,
            context=context,
            answer=answer,
        )

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
        rolling_summary: Optional[str] = None,
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
        retrieval_question = self.contextualize_question(
            question, chat_history, rolling_summary=rolling_summary
        )
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
        relevant_docs = self._retrieve_documents(
            retrieval_question,
            query_mode,
            top_k,
            access_filter=access_filter,
        )
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
        packed_docs = self._select_context_documents(
            relevant_docs,
            query_mode,
            question=retrieval_question,
        )
        context = self._build_context(packed_docs, query_mode, question=retrieval_question)
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

        # Print debug context
        self._print_query_debug(
            question=question,
            retrieval_question=retrieval_question,
            context=context,
            answer=full_answer,
        )

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
        """Build the non-fused prompt string for streaming with an auto-generated answer plan."""
        # Answer Planner: Trích xuất các group từ context để định hướng cấu trúc câu trả lời của LLM
        groups = re.findall(r'\[GROUP:\s*(.*?)\]', context)
        unique_groups = []
        for g in groups:
            g_clean = g.strip()
            if g_clean and g_clean not in unique_groups:
                unique_groups.append(g_clean)

        planner_instruction = ""
        if unique_groups:
            planner_instruction = (
                "DÀN Ý CÂU TRẢ LỜI BẮT BUỘC:\n"
                "Bạn PHẢI trình bày câu trả lời theo cấu trúc phân đoạn rõ ràng sau:\n"
            )
            for i, group in enumerate(unique_groups, 1):
                planner_instruction += f"{i}. Phân tích nhóm: {group}\n"
                planner_instruction += f"   - Nêu đầy đủ các tác giả, tác phẩm, luận điểm trích dẫn trong phần [GROUP: {group}] của context.\n"
            planner_instruction += f"{len(unique_groups) + 1}. Nhận xét và đánh giá chung trong QHQT.\n"
            planner_instruction += "Lưu ý: Không bỏ sót bất kỳ nhóm nào ở trên trong bài viết của bạn.\n\n"

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

        # Chèn dàn ý bắt buộc vào system prompt
        if planner_instruction:
            system_prompt = f"{system_prompt}\n\n{planner_instruction}"

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
