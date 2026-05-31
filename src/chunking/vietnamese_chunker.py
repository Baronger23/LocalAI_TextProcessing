"""
Vietnamese Document Chunker — Adaptive chunking engine using Regex-based
structure detection for Vietnamese legal/regulatory documents.

Supports hierarchical structures:
  PHẦN (Part) > CHƯƠNG (Chapter) > MỤC (Section) > ĐIỀU (Article) >
  KHOẢN (Clause) > ĐIỂM (Point)
"""
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Tuple


class SectionLevel(IntEnum):
    """Hierarchical level of a document section, lower = higher in tree."""
    DOCUMENT = 0
    PHAN = 1       # Phần
    CHUONG = 2     # Chương
    MUC = 3        # Mục
    DIEU = 4       # Điều
    KHOAN = 5      # Khoản
    DIEM = 6       # Điểm


@dataclass
class DocumentSection:
    """A single node in the document hierarchy tree."""
    level: SectionLevel
    title: str                              # e.g. "Chương I: Quy định chung"
    content: str = ""                       # Text body belonging to this section
    children: List["DocumentSection"] = field(default_factory=list)
    parent: Optional["DocumentSection"] = field(default=None, repr=False)

    @property
    def full_content(self) -> str:
        """All text under this section, including children recursively."""
        parts = []
        if self.content.strip():
            parts.append(self.content.strip())
        for child in self.children:
            child_full = child.full_content
            if child_full:
                parts.append(child_full)
        return "\n".join(parts)

    @property
    def content_length(self) -> int:
        return len(self.full_content)

    def breadcrumb(self) -> List[str]:
        """Return list of titles from root to this node."""
        chain: List[str] = []
        node: Optional[DocumentSection] = self
        while node is not None:
            if node.title:
                chain.append(node.title)
            node = node.parent
        chain.reverse()
        return chain


# ---------------------------------------------------------------------------
# Regex patterns for Vietnamese document structure headings
# ---------------------------------------------------------------------------

# Pattern for PHẦN (Part): "Phần I", "PHẦN THỨ NHẤT", "Phần 1" etc.
_PHAN_RE = re.compile(
    r"^\s*(?:PHẦN|Phần)\s+"
    r"(?:THỨ\s+)?(?:[IVXLCDM]+|thứ\s+\w+|\d+)"
    r"[:\.\s]*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern for CHƯƠNG (Chapter): "Chương I", "CHƯƠNG II", "Chương 1" etc.
_CHUONG_RE = re.compile(
    r"^\s*(?:CHƯƠNG|Chương)\s+"
    r"(?:[IVXLCDM]+|\d+)"
    r"[:\.\s]*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern for MỤC (Section): "Mục 1", "MỤC I" etc.
_MUC_RE = re.compile(
    r"^\s*(?:MỤC|Mục)\s+"
    r"(?:[IVXLCDM]+|\d+)"
    r"[:\.\s]*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern for ĐIỀU (Article): "Điều 1", "ĐIỀU 15" etc.
_DIEU_RE = re.compile(
    r"^\s*(?:ĐIỀU|Điều)\s+(\d+)"
    r"[:\.\s]*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern for KHOẢN (Clause): starts with "1.", "2.", "3." etc. at line start
_KHOAN_RE = re.compile(
    r"^\s*(\d+)\.\s+(.*)$",
    re.MULTILINE,
)

# Pattern for ĐIỂM (Point): starts with "a)", "b)", "a.", "b." etc.
_DIEM_RE = re.compile(
    r"^\s*([a-zđ])[)\.]\s+(.*)$",
    re.MULTILINE,
)


# Ordered from highest to lowest priority
_HEADING_PATTERNS: List[Tuple[SectionLevel, re.Pattern]] = [
    (SectionLevel.PHAN, _PHAN_RE),
    (SectionLevel.CHUONG, _CHUONG_RE),
    (SectionLevel.MUC, _MUC_RE),
    (SectionLevel.DIEU, _DIEU_RE),
]


class VietnameseDocumentParser:
    """Parse Vietnamese legal/regulatory text into a hierarchical tree."""

    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 200,
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str, doc_title: str = "") -> DocumentSection:
        """Parse raw text into a *DocumentSection* tree.

        Returns the root node whose children represent the top-level
        structural elements found in the document.
        """
        root = DocumentSection(
            level=SectionLevel.DOCUMENT,
            title=doc_title,
        )

        # Step 1 — find all heading positions
        headings = self._detect_headings(text)

        if not headings:
            # No structure detected — return whole text as single section
            root.content = text
            return root

        # Step 2 — split text into segments between headings
        segments = self._split_by_headings(text, headings)

        # Step 3 — build tree from segments
        self._build_tree(root, segments)

        return root

    def is_structured(self, text: str) -> bool:
        """Quick check whether *text* looks like a structured Vietnamese doc."""
        headings = self._detect_headings(text)
        return len(headings) >= 2

    # ------------------------------------------------------------------
    # Heading detection
    # ------------------------------------------------------------------

    def _detect_headings(
        self, text: str,
    ) -> List[Tuple[int, int, SectionLevel, str]]:
        """Return sorted list of (start, end, level, matched_line)."""
        results: List[Tuple[int, int, SectionLevel, str]] = []

        for level, pattern in _HEADING_PATTERNS:
            for m in pattern.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                if line_end == -1:
                    line_end = len(text)
                matched_line = text[line_start:line_end].strip()
                results.append((m.start(), m.end(), level, matched_line))

        # Sort by position in text
        results.sort(key=lambda x: x[0])
        return results

    def _split_by_headings(
        self,
        text: str,
        headings: List[Tuple[int, int, SectionLevel, str]],
    ) -> List[Tuple[SectionLevel, str, str]]:
        """Split *text* into (level, heading_title, body) segments."""
        segments: List[Tuple[SectionLevel, str, str]] = []

        # Text before first heading → preamble
        first_heading_start = headings[0][0]
        preamble = text[:first_heading_start].strip()
        if preamble:
            segments.append((SectionLevel.DOCUMENT, "", preamble))

        for i, (start, end, level, heading_line) in enumerate(headings):
            # Body runs from end of heading match to start of next heading
            if i + 1 < len(headings):
                body_end = headings[i + 1][0]
            else:
                body_end = len(text)

            # Find actual line end of heading for body start
            line_end = text.find("\n", end)
            if line_end == -1 or line_end > body_end:
                body_start = end
            else:
                body_start = line_end + 1

            body = text[body_start:body_end].strip()
            segments.append((level, heading_line, body))

        return segments

    # ------------------------------------------------------------------
    # Tree building
    # ------------------------------------------------------------------

    def _build_tree(
        self,
        root: DocumentSection,
        segments: List[Tuple[SectionLevel, str, str]],
    ) -> None:
        """Attach segments to *root* respecting hierarchy."""
        current_parent = root

        for level, title, body in segments:
            node = DocumentSection(level=level, title=title, content=body)

            if level == SectionLevel.DOCUMENT:
                # Preamble — attach directly to root content
                root.content = (root.content + "\n" + body).strip()
                continue

            # Walk up the tree to find the correct parent
            parent = current_parent
            while parent is not root and parent.level >= level:
                parent = parent.parent  # type: ignore[assignment]

            node.parent = parent
            parent.children.append(node)
            current_parent = node

    # ------------------------------------------------------------------
    # Adaptive splitting helpers
    # ------------------------------------------------------------------

    def split_section_adaptive(
        self, section: DocumentSection,
    ) -> List[DocumentSection]:
        """Split a section into chunk-sized pieces when it exceeds max size.

        Uses KHOẢN / ĐIỂM sub-patterns for splitting long sections.
        """
        full = section.full_content
        if len(full) <= self.max_chunk_size:
            return [section]

        # Try to split by Khoản first
        sub_sections = self._split_by_sub_patterns(
            full, SectionLevel.KHOAN, _KHOAN_RE,
        )
        if len(sub_sections) > 1:
            return self._merge_small_sections(
                sub_sections, section, SectionLevel.KHOAN,
            )

        # Try to split by Điểm
        sub_sections = self._split_by_sub_patterns(
            full, SectionLevel.DIEM, _DIEM_RE,
        )
        if len(sub_sections) > 1:
            return self._merge_small_sections(
                sub_sections, section, SectionLevel.DIEM,
            )

        # Last resort — split by paragraphs
        return self._split_by_paragraphs(section)

    def _split_by_sub_patterns(
        self,
        text: str,
        level: SectionLevel,
        pattern: re.Pattern,
    ) -> List[Tuple[str, str]]:
        """Split text by sub-level pattern, returning (title, body) pairs."""
        matches = list(pattern.finditer(text))
        if len(matches) < 2:
            return []

        result: List[Tuple[str, str]] = []

        # Text before first match
        preamble = text[: matches[0].start()].strip()
        if preamble:
            result.append(("", preamble))

        for i, m in enumerate(matches):
            title = m.group(0).strip()
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[body_start:body_end].strip()
            result.append((title, body))

        return result

    def _merge_small_sections(
        self,
        sub_sections: List[Tuple[str, str]],
        parent: DocumentSection,
        level: SectionLevel,
    ) -> List[DocumentSection]:
        """Merge small consecutive sub-sections to reach min chunk size."""
        merged: List[DocumentSection] = []
        buffer_titles: List[str] = []
        buffer_body: List[str] = []
        buffer_len = 0

        for title, body in sub_sections:
            piece = (title + "\n" + body).strip() if title else body
            if buffer_len + len(piece) > self.max_chunk_size and buffer_body:
                # Flush buffer
                node = DocumentSection(
                    level=level,
                    title=" | ".join(t for t in buffer_titles if t),
                    content="\n".join(buffer_body),
                    parent=parent,
                )
                merged.append(node)
                buffer_titles = []
                buffer_body = []
                buffer_len = 0

            buffer_titles.append(title)
            buffer_body.append(piece)
            buffer_len += len(piece)

        # Flush remaining
        if buffer_body:
            node = DocumentSection(
                level=level,
                title=" | ".join(t for t in buffer_titles if t),
                content="\n".join(buffer_body),
                parent=parent,
            )
            merged.append(node)

        return merged

    def _split_by_paragraphs(
        self, section: DocumentSection,
    ) -> List[DocumentSection]:
        """Fallback: split content by double-newline paragraphs."""
        paragraphs = re.split(r"\n\s*\n", section.full_content)
        if len(paragraphs) <= 1:
            return [section]

        chunks: List[DocumentSection] = []
        buffer: List[str] = []
        buffer_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if buffer_len + len(para) > self.max_chunk_size and buffer:
                node = DocumentSection(
                    level=section.level,
                    title=section.title,
                    content="\n\n".join(buffer),
                    parent=section.parent,
                )
                chunks.append(node)
                buffer = []
                buffer_len = 0
            buffer.append(para)
            buffer_len += len(para)

        if buffer:
            node = DocumentSection(
                level=section.level,
                title=section.title,
                content="\n\n".join(buffer),
                parent=section.parent,
            )
            chunks.append(node)

        return chunks
