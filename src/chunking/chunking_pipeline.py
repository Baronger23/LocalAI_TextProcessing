"""
Adaptive Chunking Pipeline — Orchestrator that combines Vietnamese
document structure parsing with context enrichment.

Flow:
  Raw Text → VietnameseDocumentParser.parse() → Adaptive Split →
  ContextEnricher.enrich() → List[Document]

Falls back to RecursiveCharacterTextSplitter when no Vietnamese
legal structure is detected.
"""
import re
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.chunking.vietnamese_chunker import (
    DocumentSection,
    SectionLevel,
    VietnameseDocumentParser,
)
from src.chunking.context_enricher import ContextEnricher
from src.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    CONTEXT_DEPTH,
    CONTEXT_PREFIX_ENABLED,
    CHUNK_STRATEGY,
)


class AdaptiveChunkingPipeline:
    """End-to-end pipeline: raw text → enriched LangChain Documents."""

    def __init__(
        self,
        max_chunk_size: int = MAX_CHUNK_SIZE,
        min_chunk_size: int = MIN_CHUNK_SIZE,
        context_depth: int = CONTEXT_DEPTH,
        prefix_enabled: bool = CONTEXT_PREFIX_ENABLED,
        strategy: str = CHUNK_STRATEGY,
        # Fallback splitter params
        fallback_chunk_size: int = CHUNK_SIZE,
        fallback_chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.strategy = strategy
        self.parser = VietnameseDocumentParser(
            max_chunk_size=max_chunk_size,
            min_chunk_size=min_chunk_size,
        )
        self.enricher = ContextEnricher(
            context_depth=context_depth,
            prefix_enabled=prefix_enabled,
        )
        self._fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=fallback_chunk_size,
            chunk_overlap=fallback_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        doc_title: str = "",
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Chunk raw text into enriched LangChain Documents.

        Args:
            text: Raw document text.
            doc_title: Document title (used as root breadcrumb).
            source_metadata: Extra metadata to attach to every chunk.

        Returns:
            List of enriched LangChain Documents ready for embedding.
        """
        source_metadata = source_metadata or {}

        # Strategy gate
        if self.strategy == "recursive":
            return self._fallback_chunk(text, source_metadata)

        # Try adaptive chunking
        if not self.parser.is_structured(text):
            return self._fallback_chunk(text, source_metadata)

        return self._adaptive_chunk(text, doc_title, source_metadata)

    def chunk_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """Chunk pre-loaded LangChain Documents (e.g. from loaders).

        Each Document's page_content is run through the adaptive pipeline.
        Metadata from the original document is preserved.
        """
        all_chunks: List[Document] = []

        for doc in documents:
            doc_title = self._extract_title(doc)
            source_meta = dict(doc.metadata)

            chunks = self.chunk_text(
                text=doc.page_content,
                doc_title=doc_title,
                source_metadata=source_meta,
            )
            all_chunks.extend(chunks)

        return all_chunks

    # ------------------------------------------------------------------
    # Adaptive chunking
    # ------------------------------------------------------------------

    def _adaptive_chunk(
        self,
        text: str,
        doc_title: str,
        source_metadata: Dict[str, Any],
    ) -> List[Document]:
        """Structure-aware chunking for Vietnamese legal documents."""
        # Parse into tree
        root = self.parser.parse(text, doc_title=doc_title)

        # Collect leaf-level sections (ĐIỀU level preferred)
        leaf_sections = self._collect_chunk_sections(root)

        # Adaptive splitting — split oversized, merge undersized
        final_sections = self._adaptive_split_and_merge(leaf_sections)

        # Enrich with context
        return self.enricher.enrich_sections(final_sections, source_metadata)

    def _collect_chunk_sections(
        self, root: DocumentSection,
    ) -> List[DocumentSection]:
        """Walk tree and collect sections at ĐIỀU level or below.

        If no ĐIỀU found, collect at CHƯƠNG level.
        If no CHƯƠNG found, collect at whatever the deepest level is.
        """
        sections: List[DocumentSection] = []
        self._collect_recursive(root, sections)

        if not sections:
            # If tree is flat (only root), return root itself
            sections = [root]

        return sections

    def _collect_recursive(
        self,
        node: DocumentSection,
        result: List[DocumentSection],
    ) -> None:
        """Recursively collect chunk-worthy sections.

        Strategy: prefer ĐIỀU as chunking unit. If a node IS an ĐIỀU
        or IS at a deeper level, collect it. Otherwise recurse into children.
        """
        if node.level >= SectionLevel.DIEU:
            # This is a leaf-level section — collect it directly
            result.append(node)
            return

        if not node.children:
            # No children — collect this node whatever its level
            if node.content.strip():
                result.append(node)
            return

        # Has children — check if any child is at DIEU level or deeper
        # If yes, recurse. Also collect any direct content as a standalone chunk.
        if node.content.strip() and node.level != SectionLevel.DOCUMENT:
            # Content directly under this section (before first child)
            preamble = DocumentSection(
                level=node.level,
                title=node.title + " (tổng quan)",
                content=node.content,
                parent=node.parent,
            )
            result.append(preamble)

        for child in node.children:
            self._collect_recursive(child, result)

    def _adaptive_split_and_merge(
        self,
        sections: List[DocumentSection],
    ) -> List[DocumentSection]:
        """Split oversized sections and merge tiny consecutive ones."""
        result: List[DocumentSection] = []

        for section in sections:
            # Split if too large
            split = self.parser.split_section_adaptive(section)
            result.extend(split)

        # Merge consecutive tiny sections that share the same parent
        merged = self._merge_tiny_sections(result)
        return merged

    def _merge_tiny_sections(
        self,
        sections: List[DocumentSection],
    ) -> List[DocumentSection]:
        """Merge consecutive small sections sharing the same parent."""
        if not sections:
            return sections

        min_size = self.parser.min_chunk_size
        max_size = self.parser.max_chunk_size
        merged: List[DocumentSection] = []
        buffer: Optional[DocumentSection] = None

        for section in sections:
            content_len = section.content_length

            if buffer is None:
                if content_len < min_size:
                    buffer = section
                else:
                    merged.append(section)
                continue

            # Check if can merge with buffer
            same_parent = (
                buffer.parent is not None
                and section.parent is not None
                and buffer.parent is section.parent
            )
            combined_len = buffer.content_length + content_len

            if same_parent and combined_len <= max_size:
                # Merge into buffer
                buffer = DocumentSection(
                    level=buffer.level,
                    title=buffer.title,
                    content=buffer.full_content + "\n\n" + section.full_content,
                    parent=buffer.parent,
                )
            else:
                # Flush buffer
                merged.append(buffer)
                if content_len < min_size:
                    buffer = section
                else:
                    buffer = None
                    merged.append(section)

        if buffer is not None:
            merged.append(buffer)

        return merged

    # ------------------------------------------------------------------
    # Fallback chunking
    # ------------------------------------------------------------------

    def _fallback_chunk(
        self,
        text: str,
        source_metadata: Dict[str, Any],
    ) -> List[Document]:
        """Use RecursiveCharacterTextSplitter for unstructured text."""
        doc = Document(page_content=text, metadata=source_metadata)
        chunks = self._fallback_splitter.split_documents([doc])
        return self._enrich_recursive_chunks_with_outline(chunks)

    # ------------------------------------------------------------------
    # Recursive fallback outline enrichment
    # ------------------------------------------------------------------

    _ACADEMIC_HEADING_RE = re.compile(
        r"^[\s•\-]*((?:Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế\s+)?chịu ảnh hưởng của\s+.+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    _NUMBERED_HEADING_RE = re.compile(
        r"^\s*(\d+(?:\.\d+){0,3})\.?\s+([^\s].*)$",
        re.MULTILINE
    )
    _CHAPTER_HEADING_RE = re.compile(
        r"^\s*((?:CHƯƠNG|Chương)\s+(?:[IVXLCDM]+|\d+)[:\.\s].+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    _SECTION_BOUNDARY_RE = re.compile(
        r"^\s*(?:CHƯƠNG|Chương)\s+(?:[IVXLCDM]+|\d+)[:\.\s].+"
        r"|^\s*(?:KẾT\s+LUẬN|TÀI\s+LIỆU\s+THAM\s+KHẢO|DANH\s+MỤC)\b",
        re.IGNORECASE | re.MULTILINE,
    )

    def _enrich_recursive_chunks_with_outline(
        self,
        chunks: List[Document],
    ) -> List[Document]:
        """Attach lightweight outline metadata to recursive chunks.

        This keeps the fast recursive strategy but preserves academic section
        headings in metadata and page_content so embeddings include structure.
        """
        if not chunks:
            return chunks

        enriched: List[Document] = []
        outline_titles: List[str] = []
        current_chapter = ""
        current_section = ""
        outline_chapter = ""

        for raw_chunk in chunks:
            for chunk in self._split_chunk_on_late_section_boundary(raw_chunk):
                enriched_chunk = self._enrich_single_recursive_chunk(
                    chunk=chunk,
                    outline_titles=outline_titles,
                    current_chapter=current_chapter,
                    current_section=current_section,
                )
                enriched.append(enriched_chunk["document"])
                current_chapter = enriched_chunk["current_chapter"]
                current_section = enriched_chunk["current_section"]
                if enriched_chunk["outline_chapter"] and not outline_chapter:
                    outline_chapter = enriched_chunk["outline_chapter"]

        if len(outline_titles) >= 2:
            outline_doc = self._build_outline_document(
                outline_titles=outline_titles,
                base_metadata=dict(chunks[0].metadata or {}),
                chapter_title=outline_chapter,
            )
            return [outline_doc] + enriched

        return enriched

    def _enrich_single_recursive_chunk(
        self,
        chunk: Document,
        outline_titles: List[str],
        current_chapter: str,
        current_section: str,
    ) -> Dict[str, Any]:
        """Attach outline metadata to one recursive chunk."""
        outline_chapter = ""
        text = chunk.page_content
        normalized_text = self._normalize_ocr_heading_text(text)
        chapter_match = self._CHAPTER_HEADING_RE.search(normalized_text)
        if chapter_match:
            detected_chapter = self._clean_heading(chapter_match.group(1))
            if detected_chapter != current_chapter:
                current_chapter = detected_chapter
                current_section = ""
        elif current_section and self._SECTION_BOUNDARY_RE.search(normalized_text):
            current_section = ""

        # Find all headings in this chunk (numbered headings and specific academic headings)
        numbered_matches = []
        for match in self._NUMBERED_HEADING_RE.finditer(normalized_text):
            if not self._is_valid_heading(match):
                continue
            num_part = match.group(1).strip()
            title_part = match.group(2).strip()
            full_heading = self._clean_heading(f"{num_part} {title_part}")
            numbered_matches.append(full_heading)

        academic_matches = [
            self._clean_heading(match)
            for match in self._ACADEMIC_HEADING_RE.findall(normalized_text)
        ]

        if numbered_matches:
            current_section = numbered_matches[-1]
            outline_chapter = current_chapter
            for heading in numbered_matches:
                if heading not in outline_titles:
                    outline_titles.append(heading)
        elif academic_matches:
            current_section = " | ".join(academic_matches)
            outline_chapter = current_chapter
            for heading in academic_matches:
                if heading not in outline_titles:
                    outline_titles.append(heading)

        metadata = dict(chunk.metadata or {})
        if current_chapter:
            metadata.setdefault("chapter_title", current_chapter)
        if current_section:
            metadata["section_title"] = current_section
            metadata["outline_path"] = self._join_outline_path(
                current_chapter, current_section
            )
            metadata.setdefault("chunk_type", "content")
            page_content = self._contextualize_chunk_content(
                text=text,
                chapter_title=current_chapter,
                section_title=current_section,
            )
        else:
            metadata.setdefault("outline_path", current_chapter or "")
            metadata.setdefault("chunk_type", "content")
            page_content = text

        return {
            "document": Document(page_content=page_content, metadata=metadata),
            "current_chapter": current_chapter,
            "current_section": current_section,
            "outline_chapter": outline_chapter,
        }

    def _split_chunk_on_late_section_boundary(self, chunk: Document) -> List[Document]:
        """Split a recursive chunk if a later chapter/reference boundary appears."""
        text = chunk.page_content or ""
        normalized_text = self._normalize_ocr_heading_text(text)
        
        all_headings = []
        for m in self._ACADEMIC_HEADING_RE.finditer(normalized_text):
            all_headings.append(m)
        for m in self._NUMBERED_HEADING_RE.finditer(normalized_text):
            if self._is_valid_heading(m):
                all_headings.append(m)
            
        if not all_headings:
            return [chunk]

        all_headings.sort(key=lambda m: m.start())
        last_section_end = all_headings[-1].end()

        for boundary_match in self._SECTION_BOUNDARY_RE.finditer(normalized_text):
            split_at = boundary_match.start()
            if split_at <= last_section_end + 20:
                continue
            if split_at <= 0 or split_at >= len(text) - 10:
                continue
            before = text[:split_at].rstrip()
            after = text[split_at:].lstrip()
            if not before or not after:
                continue
            metadata = dict(chunk.metadata or {})
            return [
                Document(page_content=before, metadata=metadata),
                Document(page_content=after, metadata=dict(chunk.metadata or {})),
            ]
        return [chunk]

    @staticmethod
    def _is_valid_heading(match: re.Match) -> bool:
        """Validate if a regex match is a genuine heading or just a list item."""
        num_part = match.group(1).strip()
        title_part = match.group(2).strip()
        if "." not in num_part:
            # Single digit heading (e.g. "6")
            if len(title_part) > 60:
                return False
            if title_part.endswith(".") or title_part.endswith(";") or title_part.endswith(","):
                return False
            if any(p in title_part for p in [". ", ", ", "; "]):
                return False
        return True

    @staticmethod
    def _clean_heading(heading: str) -> str:
        """Normalize heading whitespace."""
        return re.sub(r"\s+", " ", heading).strip()

    @classmethod
    def _normalize_ocr_heading_text(cls, text: str) -> str:
        """Normalize common PDF/OCR spacing artifacts before heading detection."""
        normalized = text.replace("Ƣ", "Ư").replace("ƣ", "ư")
        replacements = {
            "quan h ệ": "quan hệ",
            "đ ến": "đến",
            "ch ủ": "chủ",
            "th ể": "thể",
            "ảnh h ưởng": "ảnh hưởng",
            "M ạng": "Mạng",
            "l ưới": "lưới",
            "X ã": "Xã",
            "h ội": "hội",
            "L ý": "Lý",
            "thuy ết": "thuyết",
            "Vai tr ò": "Vai trò",
            "Hi ện": "Hiện",
            "th ực": "thực",
            "T ự": "Tự",
            "Ki ến": "Kiến",
            "t ạo": "tạo",
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        normalized = re.sub(r"chịu\s+ảnh\s+hưởng", "chịu ảnh hưởng", normalized)
        return normalized

    @staticmethod
    def _join_outline_path(chapter_title: str, section_title: str) -> str:
        """Build a compact outline path."""
        return " > ".join(part for part in (chapter_title, section_title) if part)

    @staticmethod
    def _contextualize_chunk_content(
        text: str,
        chapter_title: str,
        section_title: str,
    ) -> str:
        """Prefix chunk text with structural context used by embeddings."""
        prefix = f"Mục: {section_title}"
        if text.startswith(prefix):
            return text
        return f"{prefix}\n\n{text}"

    def _build_outline_document(
        self,
        outline_titles: List[str],
        base_metadata: Dict[str, Any],
        chapter_title: str,
    ) -> Document:
        """Create one compact outline chunk for broad/question-list retrieval."""
        metadata = dict(base_metadata)
        metadata.update(
            {
                "chunk_type": "outline",
                "section_title": "Tổng quan các mục chính",
                "outline_path": chapter_title or "Tổng quan các mục chính",
            }
        )
        if chapter_title:
            metadata["chapter_title"] = chapter_title

        lines = ["Các mục chính trong tài liệu:"]
        lines.extend(f"- {title}" for title in outline_titles)
        return Document(page_content="\n".join(lines), metadata=metadata)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(doc: Document) -> str:
        """Try to extract a meaningful title from document metadata."""
        meta = doc.metadata
        # Common metadata keys from various loaders
        for key in ("title", "source", "file_name", "file_path"):
            if key in meta and meta[key]:
                val = str(meta[key])
                # If it's a file path, use just the filename
                if "/" in val or "\\" in val:
                    val = val.replace("\\", "/").split("/")[-1]
                # Strip extension
                if "." in val:
                    val = val.rsplit(".", 1)[0]
                return val
        return ""
