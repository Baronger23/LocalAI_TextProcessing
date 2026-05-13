"""
Tests for the Adaptive + Context-Enriched Chunking module.
"""
import pytest
from langchain_core.documents import Document

from src.chunking.vietnamese_chunker import (
    VietnameseDocumentParser,
    DocumentSection,
    SectionLevel,
)
from src.chunking.context_enricher import ContextEnricher
from src.chunking.chunking_pipeline import AdaptiveChunkingPipeline
from src.document_loader.loader import DocumentProcessor


# ---------------------------------------------------------------------------
# Sample Vietnamese legal document text for testing
# ---------------------------------------------------------------------------

SAMPLE_VN_LEGAL_TEXT = """
NỘI QUY LAO ĐỘNG CÔNG TY ABC

CHƯƠNG I: QUY ĐỊNH CHUNG

Điều 1: Phạm vi áp dụng
Nội quy lao động này áp dụng cho toàn bộ người lao động đang làm việc tại Công ty ABC, bao gồm nhân viên chính thức, nhân viên thử việc và nhân viên hợp đồng thời vụ.

Điều 2: Mục đích
1. Đảm bảo trật tự, kỷ luật trong công ty.
2. Bảo vệ quyền và lợi ích hợp pháp của người lao động.
3. Nâng cao năng suất lao động và hiệu quả công việc.

CHƯƠNG II: THỜI GIỜ LÀM VIỆC VÀ NGHỈ NGƠI

Điều 3: Thời giờ làm việc
1. Thời giờ làm việc chính thức: 8 giờ/ngày, từ 08:00 đến 17:00, nghỉ trưa từ 12:00 đến 13:00.
2. Ngày làm việc: Thứ Hai đến Thứ Sáu hàng tuần.
3. Trường hợp đặc biệt có thể thay đổi theo quyết định của Ban Giám đốc.

Điều 4: Nghỉ phép
1. Nhân viên chính thức được nghỉ phép 12 ngày/năm.
2. Nhân viên thử việc được nghỉ phép theo tỷ lệ thời gian làm việc.

CHƯƠNG III: KỶ LUẬT LAO ĐỘNG

Điều 5: Hình thức kỷ luật
1. Khiển trách bằng văn bản.
2. Kéo dài thời hạn nâng lương không quá 6 tháng.
3. Cách chức.
4. Sa thải.

Điều 6: Vi phạm và hình thức xử lý
1. Đi trễ hoặc về sớm không phép: Khiển trách lần 1, phạt 50% lương ngày lần 2.
2. Nghỉ không phép: Trừ lương ngày nghỉ và khiển trách bằng văn bản.
3. Vi phạm an toàn lao động: Tùy mức độ, từ khiển trách đến sa thải.
""".strip()


SAMPLE_UNSTRUCTURED_TEXT = """
Đây là một đoạn văn bản không có cấu trúc Chương/Điều rõ ràng.

Nội dung này chỉ gồm các đoạn văn thông thường, không tuân theo
format của văn bản pháp luật hay quy chế nội bộ.

Vì vậy hệ thống nên fallback về RecursiveCharacterTextSplitter.
""".strip()


SAMPLE_ACADEMIC_OUTLINE_TEXT = """
CHƯƠNG 1: TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU

Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Hiện thực
Nội dung về các công trình hiện thực.

Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Tự do
Nội dung về các công trình tự do.

Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Kiến tạo
Nội dung về các công trình kiến tạo.

Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Lý thuyết Vai trò (Role theory)
Nội dung về Linton, Mead, Cooley và Holsti.

Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Phân tích Mạng lưới Xã hội (SNA)
Nội dung về SNA và centrality.
""".strip()


# ============================================================================
# Test VietnameseDocumentParser
# ============================================================================

class TestVietnameseDocumentParser:
    """Test Regex-based Vietnamese document structure parsing."""

    def setup_method(self):
        self.parser = VietnameseDocumentParser(
            max_chunk_size=1500,
            min_chunk_size=100,
        )

    def test_is_structured_positive(self):
        """Structured Vietnamese text should be detected."""
        assert self.parser.is_structured(SAMPLE_VN_LEGAL_TEXT) is True

    def test_is_structured_negative(self):
        """Unstructured text should not be detected as structured."""
        assert self.parser.is_structured(SAMPLE_UNSTRUCTURED_TEXT) is False

    def test_parse_detects_chuong(self):
        """Parser should detect CHƯƠNG (chapter) headings."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT, doc_title="Nội quy lao động")
        chuong_nodes = [
            c for c in root.children if c.level == SectionLevel.CHUONG
        ]
        assert len(chuong_nodes) == 3
        assert "CHƯƠNG I" in chuong_nodes[0].title
        assert "CHƯƠNG II" in chuong_nodes[1].title
        assert "CHƯƠNG III" in chuong_nodes[2].title

    def test_parse_detects_dieu(self):
        """Parser should detect ĐIỀU (article) headings within chapters."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT, doc_title="Nội quy")

        # Collect all ĐIỀU nodes recursively
        dieu_nodes = []

        def collect(node):
            if node.level == SectionLevel.DIEU:
                dieu_nodes.append(node)
            for child in node.children:
                collect(child)

        collect(root)
        assert len(dieu_nodes) == 6  # Điều 1 through Điều 6

    def test_parse_tree_hierarchy(self):
        """ĐIỀU should be children of CHƯƠNG."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT)
        chuong_1 = root.children[0]
        assert chuong_1.level == SectionLevel.CHUONG
        # Chương I should have Điều 1 and Điều 2 as children
        dieu_children = [
            c for c in chuong_1.children if c.level == SectionLevel.DIEU
        ]
        assert len(dieu_children) == 2

    def test_parse_breadcrumb(self):
        """Breadcrumb should reflect full path from root to leaf."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT, doc_title="Nội quy ABC")
        # Navigate to first Điều
        chuong_1 = root.children[0]
        dieu_1 = chuong_1.children[0]

        crumbs = dieu_1.breadcrumb()
        assert len(crumbs) >= 2
        assert "Nội quy ABC" in crumbs[0]
        assert "CHƯƠNG I" in crumbs[1] or "Chương I" in crumbs[1]

    def test_parse_preserves_content(self):
        """Each ĐIỀU node should contain its actual content text."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT)
        # Find Điều 1
        chuong_1 = root.children[0]
        dieu_1 = chuong_1.children[0]
        content = dieu_1.full_content
        assert "Công ty ABC" in content or "phạm vi" in content.lower()

    def test_unstructured_text_returns_flat(self):
        """Unstructured text should produce a root node with content only."""
        root = self.parser.parse(SAMPLE_UNSTRUCTURED_TEXT, doc_title="Test")
        assert root.level == SectionLevel.DOCUMENT
        assert len(root.children) == 0
        assert len(root.content) > 0


# ============================================================================
# Test ContextEnricher
# ============================================================================

class TestContextEnricher:
    """Test breadcrumb context enrichment."""

    def setup_method(self):
        self.enricher = ContextEnricher(
            context_depth=3,
            prefix_enabled=True,
        )
        self.parser = VietnameseDocumentParser()

    def test_breadcrumb_format(self):
        """Breadcrumb should use [Level] > [Level] format."""
        root = self.parser.parse(SAMPLE_VN_LEGAL_TEXT, doc_title="Nội quy")
        chuong = root.children[0]
        dieu = chuong.children[0]

        breadcrumb = self.enricher._build_breadcrumb(dieu)
        assert "[" in breadcrumb
        assert "]" in breadcrumb
        assert " > " in breadcrumb

    def test_enrich_adds_prefix_to_content(self):
        """Enriched Document should have breadcrumb prefix in page_content."""
        section = DocumentSection(
            level=SectionLevel.DIEU,
            title="Điều 15: Đi trễ",
            content="Phạt 50% lương nếu vi phạm.",
        )
        parent = DocumentSection(
            level=SectionLevel.CHUONG,
            title="Chương II: Kỷ luật",
            children=[section],
        )
        section.parent = parent

        docs = self.enricher.enrich_sections([section])
        assert len(docs) == 1

        doc = docs[0]
        assert "[Chương II: Kỷ luật]" in doc.page_content
        assert "[Điều 15: Đi trễ]" in doc.page_content
        assert "Phạt 50% lương" in doc.page_content

    def test_enrich_metadata(self):
        """Enriched Document should have breadcrumb in metadata."""
        section = DocumentSection(
            level=SectionLevel.DIEU,
            title="Điều 1: Test",
            content="Nội dung test.",
        )
        docs = self.enricher.enrich_sections(
            [section],
            source_metadata={"source": "test.pdf"},
        )
        assert len(docs) == 1
        meta = docs[0].metadata
        assert "breadcrumb" in meta
        assert "section_level" in meta
        assert meta["section_level"] == "DIEU"
        assert meta["source"] == "test.pdf"

    def test_prefix_disabled(self):
        """When prefix_enabled=False, page_content should not have breadcrumb."""
        enricher_no_prefix = ContextEnricher(prefix_enabled=False)
        section = DocumentSection(
            level=SectionLevel.DIEU,
            title="Điều 1: Test",
            content="Nội dung không prefix.",
        )
        docs = enricher_no_prefix.enrich_sections([section])
        assert docs[0].page_content.startswith("Nội dung không prefix.")


# ============================================================================
# Test AdaptiveChunkingPipeline
# ============================================================================

class TestAdaptiveChunkingPipeline:
    """Test the full chunking pipeline."""

    def setup_method(self):
        self.pipeline = AdaptiveChunkingPipeline(strategy="adaptive")

    def test_structured_text_produces_chunks(self):
        """Structured Vietnamese text should produce multiple chunks."""
        chunks = self.pipeline.chunk_text(
            SAMPLE_VN_LEGAL_TEXT,
            doc_title="Nội quy lao động",
        )
        assert len(chunks) > 1
        assert all(isinstance(c, Document) for c in chunks)

    def test_chunks_have_breadcrumb(self):
        """Each chunk should have breadcrumb metadata."""
        chunks = self.pipeline.chunk_text(
            SAMPLE_VN_LEGAL_TEXT,
            doc_title="Nội quy lao động",
        )
        for chunk in chunks:
            assert "breadcrumb" in chunk.metadata

    def test_chunks_contain_content(self):
        """Chunks should contain actual document text."""
        chunks = self.pipeline.chunk_text(
            SAMPLE_VN_LEGAL_TEXT,
            doc_title="Nội quy",
        )
        all_text = " ".join(c.page_content for c in chunks)
        assert "Công ty ABC" in all_text or "công ty" in all_text.lower()
        assert "kỷ luật" in all_text.lower() or "Kỷ luật" in all_text

    def test_unstructured_text_fallback(self):
        """Unstructured text should use fallback splitter."""
        chunks = self.pipeline.chunk_text(SAMPLE_UNSTRUCTURED_TEXT)
        assert len(chunks) >= 1
        # Fallback chunks won't have breadcrumb
        assert all(isinstance(c, Document) for c in chunks)

    def test_recursive_strategy(self):
        """Strategy='recursive' should always use fallback."""
        pipeline_recursive = AdaptiveChunkingPipeline(strategy="recursive")
        chunks = pipeline_recursive.chunk_text(SAMPLE_VN_LEGAL_TEXT)
        assert len(chunks) >= 1
        # Recursive chunks don't have breadcrumb metadata
        for chunk in chunks:
            assert "breadcrumb" not in chunk.metadata

    def test_chunk_documents_method(self):
        """chunk_documents should handle pre-loaded LangChain Documents."""
        docs = [
            Document(
                page_content=SAMPLE_VN_LEGAL_TEXT,
                metadata={"source": "noi_quy.pdf"},
            )
        ]
        chunks = self.pipeline.chunk_documents(docs)
        assert len(chunks) > 1
        # Source metadata should be preserved
        for chunk in chunks:
            assert chunk.metadata.get("source") == "noi_quy.pdf"

    def test_source_metadata_preserved(self):
        """Source metadata should be passed through to all chunks."""
        source_meta = {"source": "test.pdf", "page": 1}
        chunks = self.pipeline.chunk_text(
            SAMPLE_VN_LEGAL_TEXT,
            doc_title="Test",
            source_metadata=source_meta,
        )
        for chunk in chunks:
            assert chunk.metadata.get("source") == "test.pdf"
            assert chunk.metadata.get("page") == 1

    def test_recursive_strategy_adds_academic_outline_metadata(self):
        """Recursive fallback should still preserve academic section headings."""
        pipeline = AdaptiveChunkingPipeline(
            strategy="recursive",
            fallback_chunk_size=420,
            fallback_chunk_overlap=0,
        )

        chunks = pipeline.chunk_text(
            SAMPLE_ACADEMIC_OUTLINE_TEXT,
            source_metadata={"source": "lats.pdf"},
        )

        content_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("chunk_type") != "outline"
        ]
        section_titles = {
            chunk.metadata.get("section_title")
            for chunk in content_chunks
            if chunk.metadata.get("section_title")
        }

        assert any("Chủ nghĩa Hiện thực" in title for title in section_titles)
        assert any("Chủ nghĩa Tự do" in title for title in section_titles)
        assert any("Chủ nghĩa Kiến tạo" in title for title in section_titles)
        assert any("Lý thuyết Vai trò" in title for title in section_titles)
        assert any("Phân tích Mạng lưới Xã hội" in title for title in section_titles)
        assert all("outline_path" in chunk.metadata for chunk in content_chunks)

    def test_recursive_strategy_contextualizes_chunk_content_for_embedding(self):
        """Embedding text should include the section heading, not body text only."""
        pipeline = AdaptiveChunkingPipeline(
            strategy="recursive",
            fallback_chunk_size=420,
            fallback_chunk_overlap=0,
        )

        chunks = pipeline.chunk_text(SAMPLE_ACADEMIC_OUTLINE_TEXT)
        constructivism_chunk = next(
            chunk for chunk in chunks
            if "Nội dung về các công trình kiến tạo" in chunk.page_content
        )

        assert constructivism_chunk.page_content.startswith("Mục:")
        assert "Chủ nghĩa Kiến tạo" in constructivism_chunk.page_content.splitlines()[0]

    def test_recursive_strategy_creates_outline_chunk(self):
        """A compact outline chunk should be available for broad retrieval."""
        pipeline = AdaptiveChunkingPipeline(
            strategy="recursive",
            fallback_chunk_size=420,
            fallback_chunk_overlap=0,
        )

        chunks = pipeline.chunk_text(SAMPLE_ACADEMIC_OUTLINE_TEXT)
        outline_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("chunk_type") == "outline"
        ]

        assert len(outline_chunks) == 1
        outline_text = outline_chunks[0].page_content
        assert "Chủ nghĩa Hiện thực" in outline_text
        assert "Chủ nghĩa Tự do" in outline_text
        assert "Chủ nghĩa Kiến tạo" in outline_text
        assert "Lý thuyết Vai trò" in outline_text
        assert "Phân tích Mạng lưới Xã hội" in outline_text


class TestDocumentProcessorOutlineIngestion:
    """Test production ingestion path used by UI/scripts."""

    def test_recursive_split_merges_pages_by_source_before_outline_detection(self):
        page_1 = Document(
            page_content=(
                "CHƯƠNG 1: TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU\n\n"
                "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Hiện thực\n"
                "Nội dung hiện thực."
            ),
            metadata={"source": "lats.pdf", "page": 1},
        )
        page_2 = Document(
            page_content=(
                "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Tự do\n"
                "Nội dung tự do.\n\n"
                "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Kiến tạo\n"
                "Nội dung kiến tạo."
            ),
            metadata={"source": "lats.pdf", "page": 2},
        )

        processor = DocumentProcessor(
            chunk_size=420,
            chunk_overlap=0,
            strategy="recursive",
        )
        chunks = processor.split_documents([page_1, page_2])

        outline_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("chunk_type") == "outline"
        ]
        assert len(outline_chunks) == 1
        assert "Chủ nghĩa Hiện thực" in outline_chunks[0].page_content
        assert "Chủ nghĩa Tự do" in outline_chunks[0].page_content
        assert "Chủ nghĩa Kiến tạo" in outline_chunks[0].page_content
        assert all(chunk.metadata.get("source") == "lats.pdf" for chunk in chunks)

    def test_recursive_split_detects_pdf_ocr_spaced_academic_headings(self):
        text = (
            "CHƢƠNG 1: TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU\n\n"
            "Các công trình liên quan đ ến vai trò ch ủ thể quan hệ quốc tế chịu ảnh "
            "hưởng của Chủ nghĩa Hiện thực\n"
            "Nội dung hiện thực.\n\n"
            "Các công trình liên quan đ ến vai trò ch ủ thể quan hệ quốc tế chịu ảnh "
            "hưởng của Chủ nghĩa Tự do\n"
            "Nội dung tự do."
        )
        processor = DocumentProcessor(
            chunk_size=420,
            chunk_overlap=0,
            strategy="recursive",
        )

        chunks = processor.split_documents(
            [Document(page_content=text, metadata={"source": "ocr.pdf"})]
        )
        outline_chunks = [
            chunk for chunk in chunks
            if chunk.metadata.get("chunk_type") == "outline"
        ]

        assert len(outline_chunks) == 1
        assert "Chủ nghĩa Hiện thực" in outline_chunks[0].page_content
        assert "Chủ nghĩa Tự do" in outline_chunks[0].page_content


# ============================================================================
# Test edge cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text(self):
        """Empty text should return empty list or minimal chunks."""
        pipeline = AdaptiveChunkingPipeline(strategy="adaptive")
        chunks = pipeline.chunk_text("")
        assert isinstance(chunks, list)

    def test_single_dieu(self):
        """A document with only one Điều should produce one chunk."""
        text = """
Điều 1: Quy định duy nhất
Nội dung của điều khoản duy nhất trong tài liệu này.
Áp dụng cho toàn bộ nhân viên.
""".strip()
        pipeline = AdaptiveChunkingPipeline(strategy="adaptive")
        # May not be detected as structured (needs >= 2 headings)
        chunks = pipeline.chunk_text(text)
        assert len(chunks) >= 1

    def test_mixed_casing(self):
        """Parser should handle both uppercase CHƯƠNG and mixed case Chương."""
        text = """
Chương I: Tổng quan
Điều 1: Giới thiệu
Nội dung giới thiệu.

CHƯƠNG II: Chi tiết
Điều 2: Quy định
Nội dung quy định chi tiết.
""".strip()
        parser = VietnameseDocumentParser()
        assert parser.is_structured(text) is True
        root = parser.parse(text)
        assert len(root.children) == 2
