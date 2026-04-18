"""
Adaptive Chunking Pipeline — Orchestrator that combines Vietnamese
document structure parsing with context enrichment.

Flow:
  Raw Text → VietnameseDocumentParser.parse() → Adaptive Split →
  ContextEnricher.enrich() → List[Document]

Falls back to RecursiveCharacterTextSplitter when no Vietnamese
legal structure is detected.
"""
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
        return self._fallback_splitter.split_documents([doc])

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
