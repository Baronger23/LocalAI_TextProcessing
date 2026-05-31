"""Test PDF loading and chunking."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


from src.document_loader import DocumentProcessor


def create_test_pdf():
    """Create a test PDF file with multiple pages."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        print("❌ reportlab not installed. Skipping PDF test.")
        return None

    pdf_path = Path("/tmp/test_document.pdf")

    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    # Add 20 pages with content
    for page_num in range(1, 21):
        c.drawString(50, 750, f"Page {page_num} - Test Document")
        c.drawString(50, 730, "=" * 60)

        # Add some Vietnamese content
        content_lines = [
            "Nội Quy Lao Động Công Ty ABC",
            f"Chương {page_num}: Quy Định Chung",
            f"Điều {page_num}: Phạm Vị Áp Dụng",
            "Nội quy này áp dụng cho tất cả nhân viên của công ty.",
            "Các quy định này bắt buộc phải tuân thủ.",
            "Nhân viên phải hiểu rõ các nội quy.",
            "Các vi phạm sẽ bị xử lý theo quy định.",
            "Công ty có quyền sửa đổi nội quy.",
        ]

        y = 700
        for line in content_lines:
            c.drawString(50, y, line)
            y -= 20

        c.showPage()

    c.save()
    return str(pdf_path)


def test_pdf_loading_and_chunking():
    """Test if PDF loading and chunking works correctly."""
    print("\n📄 TEST: PDF LOADING AND CHUNKING")

    pdf_path = create_test_pdf()
    if not pdf_path:
        return

    processor = DocumentProcessor()

    # Step 1: Load PDF
    print(f"Loading PDF from: {pdf_path}")
    pdf_docs = processor.load_pdf(pdf_path)
    print(f"  PDF Pages: {len(pdf_docs)}")

    # Step 2: Chunk
    print("Chunking PDF documents...")
    chunks = processor.split_documents_adaptive(pdf_docs)
    print(f"  Total chunks: {len(chunks)}")

    # Show first few chunks
    for i, chunk in enumerate(chunks[:5]):
        print(f"\n  Chunk {i+1}:")
        print(f"    Size: {len(chunk.page_content)} chars")
        print(f"    Breadcrumb: {chunk.metadata.get('breadcrumb', 'N/A')}")
        print(f"    Content preview: {chunk.page_content[:60]}...")

    # Clean up
    Path(pdf_path).unlink()

    print(f"\n✅ PDF test completed: {len(chunks)} chunks")


def test_document_processor_pipeline():
    """Test the full document processor pipeline."""
    print("\n📂 TEST: FULL DOCUMENT PROCESSOR PIPELINE")

    # Create a test directory with multiple files
    test_dir = Path("/tmp/test_docs")
    test_dir.mkdir(exist_ok=True)

    # Create a large TXT file
    txt_file = test_dir / "test.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        text = """NỘI QUY LAO ĐỘNG CÔNG TY ABC

CHƯƠNG I: QUY ĐỊNH CHUNG
Điều 1: Phạm vi áp dụng
Nội quy này áp dụng cho tất cả nhân viên.

Điều 2: Mục đích
Xây dựng môi trường làm việc tích cực.

Điều 3: Nguyên tắc
Công bằng và bình đẳng.

CHƯƠNG II: QUYỀN VÀ NGHĨA VỤ
Điều 4: Quyền nhân viên
Nhân viên có quyền lương đầy đủ.

Điều 5: Nghĩa vụ
Nhân viên phải tuân thủ quy định.

CHƯƠNG III: NGÀY GIỜ LÀM VIỆC
Điều 6: Thời gian
Thời gian làm việc 8-17 giờ.

Điều 7: Nghỉ
Các ngày lễ được nghỉ.
"""
        f.write(text * 3)  # Replicate for size

    processor = DocumentProcessor()

    # Test process_documents
    print(f"Processing directory: {test_dir}")
    documents = processor.process_documents(str(test_dir), is_directory=True)
    print(f"  Total documents/chunks: {len(documents)}")

    for i, doc in enumerate(documents[:3]):
        print(f"\n  Doc {i+1}:")
        print(f"    Size: {len(doc.page_content)} chars")
        print(f"    Breadcrumb: {doc.metadata.get('breadcrumb', 'N/A')}")

    # Clean up
    import shutil
    shutil.rmtree(test_dir)

    print(f"\n✅ Directory processing test: {len(documents)} chunks")


if __name__ == "__main__":
    print("🔍 TEST DOCUMENT LOADING AND CHUNKING")

    test_pdf_loading_and_chunking()
    test_document_processor_pipeline()
