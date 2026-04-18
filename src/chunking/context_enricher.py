"""
Context Enricher — Attach breadcrumb metadata to each chunk so that
the LLM always knows the full hierarchical origin of the text.

Example output prefix:
  [Tài liệu: Nội quy lao động] > [Chương II: Kỷ luật lao động] > [Điều 15: Đi trễ]
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from src.chunking.vietnamese_chunker import (
    DocumentSection,
    SectionLevel,
    VietnameseDocumentParser,
)


class ContextEnricher:
    """Enrich document chunks with hierarchical breadcrumb context."""

    def __init__(
        self,
        context_depth: int = 3,
        prefix_enabled: bool = True,
        separator: str = " > ",
    ):
        """
        Args:
            context_depth: Maximum number of breadcrumb levels to include.
            prefix_enabled: Whether to prepend breadcrumb to page_content.
            separator: String separating breadcrumb levels.
        """
        self.context_depth = context_depth
        self.prefix_enabled = prefix_enabled
        self.separator = separator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich_sections(
        self,
        sections: List[DocumentSection],
        source_metadata: Dict[str, Any] | None = None,
    ) -> List[Document]:
        """Convert list of *DocumentSection* objects into LangChain Documents
        with enriched metadata and optional breadcrumb prefix.

        Args:
            sections: Flat list of leaf-level sections to convert.
            source_metadata: Extra metadata (e.g. filename, page_num) to
                             merge into every document.

        Returns:
            List of LangChain ``Document`` objects.
        """
        documents: List[Document] = []
        source_metadata = source_metadata or {}

        for section in sections:
            doc = self._section_to_document(section, source_metadata)
            if doc:
                documents.append(doc)

        return documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_breadcrumb(self, section: DocumentSection) -> str:
        """Build a human-readable breadcrumb string for *section*."""
        crumbs = section.breadcrumb()

        # Limit depth
        if len(crumbs) > self.context_depth:
            crumbs = crumbs[:1] + crumbs[-(self.context_depth - 1):]

        # Format each crumb in brackets
        formatted = [f"[{c}]" for c in crumbs if c]
        return self.separator.join(formatted)

    def _build_metadata(
        self,
        section: DocumentSection,
        breadcrumb: str,
        source_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build metadata dict for a LangChain Document."""
        meta: Dict[str, Any] = {
            **source_metadata,
            "section_level": section.level.name,
            "section_title": section.title,
            "breadcrumb": breadcrumb,
        }

        # Add full hierarchy path as list
        meta["hierarchy_path"] = section.breadcrumb()

        return meta

    def _section_to_document(
        self,
        section: DocumentSection,
        source_metadata: Dict[str, Any],
    ) -> Document | None:
        """Convert a single section to a LangChain Document."""
        content = section.full_content.strip()
        if not content:
            return None

        breadcrumb = self._build_breadcrumb(section)

        # Build page_content with optional breadcrumb prefix
        if self.prefix_enabled and breadcrumb:
            page_content = f"{breadcrumb}\n\n{content}"
        else:
            page_content = content

        metadata = self._build_metadata(section, breadcrumb, source_metadata)

        return Document(
            page_content=page_content,
            metadata=metadata,
        )
