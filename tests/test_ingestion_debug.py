"""Debug test for ingestion pipeline - chunk counting and database storage."""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_loader import DocumentProcessor
from src.embeddings import EmbeddingManager
from src.rag.vector_store import VectorStoreManager


def test_document_processing_chunking():
    """Test: Document processing should split into many chunks, not just 2."""

    # Create a sample Vietnamese legal document (9MB equivalent - simulate with long text)
    long_text = """
NỘI QUY LAO ĐỘNG CÔNG TY ABC - Version 2024

CHƯƠNG I: QUY ĐỊNH CHUNG

Điều 1: Phạm vi áp dụng
Nội quy này áp dụng đối với tất cả nhân viên của công ty ABC, bao gồm:
- Nhân viên chính thức
- Nhân viên thử việc
- Nhân viên hợp đồng xác định thời hạn
- Nhân viên hợp đồng không xác định thời hạn

Điều 2: Mục đích và nguyên tắc
Mục đích của nội quy là:
1. Xây dựng môi trường làm việc tích cực và chuyên nghiệp
2. Đảm bảo quyền lợi của nhân viên và công ty
3. Nâng cao năng suất lao động
4. Tạo điều kiện để nhân viên phát triển sự nghiệp

Các nguyên tắc:
- Công bằng và bình đẳng
- Tôn trọng nhân phẩm
- Tuân thủ pháp luật
- Minh bạch và công khai

Điều 3: Định nghĩa các thuật ngữ
- Công ty: Công ty ABC
- Nhân viên: Người làm việc tại công ty
- Quản lý: Người có trách nhiệm giám sát nhân viên
- Lương: Tiền công do công ty trả cho nhân viên

CHƯƠNG II: QUYỀN VÀ NGHĨA VỤ

Điều 4: Quyền của nhân viên
Nhân viên có quyền:
1. Nhận lương đầy đủ và đúng hạn
2. Làm việc trong môi trường an toàn
3. Được tôn trọng và công bằng
4. Được phát triển kỹ năng
5. Được bảo hiểm xã hội

Điều 5: Nghĩa vụ của nhân viên
Nhân viên phải:
1. Tuân thủ quy định của công ty
2. Hoàn thành công việc được giao
3. Bảo vệ tài sản công ty
4. Giữ bí mật thương mại
5. Có hành vi lịch sự

CHƯƠNG III: NGÀY VÀ GIỜ LÀM VIỆC

Điều 6: Thời gian làm việc
Thời gian làm việc bình thường:
- Từ thứ 2 đến thứ 6
- Sáng: 8:00 - 12:00
- Chiều: 13:00 - 17:00
- Tổng cộng: 40 giờ/tuần

Điều 7: Ngày nghỉ
Ngày nghỉ hàng năm:
- Các ngày lễ quốc gia
- 12 ngày hưởng lương
- Ngày phép hàng năm

Điều 8: Làm việc ngoài giờ
Khi cần làm việc ngoài giờ:
1. Phải có sự chấp thuận từ quản lý
2. Sẽ được thanh toán theo tỷ lệ quy định
3. Không được vượt quá 40 giờ/tháng (trừ trường hợp đặc biệt)

CHƯƠNG IV: LƯƠNG VÀ PHÚC LỢI

Điều 9: Mức lương
Mức lương được quy định dựa trên:
- Chức vụ
- Kinh nghiệm
- Kỹ năng
- Thành tích công việc

Lương được trả hàng tháng, không chậm quá ngày 5 của tháng tiếp theo.

Điều 10: Phúc lợi
Công ty cung cấp:
1. Bảo hiểm xã hội (30% của lương cơ bản)
2. Bảo hiểm y tế
3. Bảo hiểm thất nghiệp
4. Quà tặng cho dịp Tết và các ngày lễ
5. Hỗ trợ học tập

Điều 11: Thưởng
Nhân viên sẽ được thưởng dựa trên:
1. Kết quả công việc
2. Thành tích xuất sắc
3. Đóng góp cho công ty

CHƯƠNG V: KỶ LUẬT

Điều 12: Quy tắc ứng xử
Nhân viên phải:
1. Đi làm đúng giờ
2. Mặc trang phục phù hợp
3. Giữ gìn vệ sinh
4. Không hút thuốc tại nơi làm việc (ngoài khu hút thuốc)
5. Không sử dụng rượu/bia tại nơi làm việc
6. Không sử dụng điện thoại cá nhân trong giờ làm việc (trừ trường hợp khẩn cấp)

Điều 13: Vi phạm nhẹ
Vi phạm nhẹ bao gồm:
1. Đi làm muộn (dưới 30 phút)
2. Đi sớm (dưới 30 phút)
3. Quên mang thẻ
4. Không tuân thủ trang phục

Hình phạt:
- Lần 1: Cảnh cáo
- Lần 2: Rút lương 1 ngày
- Lần 3: Rút lương 3 ngày

Điều 14: Vi phạm nặng
Vi phạm nặng bao gồm:
1. Đi làm muộn trên 2 giờ
2. Không đi làm không phép
3. Tiết lộ bí mật công ty
4. Làm hư hỏng tài sản công ty
5. Gây mâu thuẫn với đồng nghiệp
6. Hành vi bạo lực tại nơi làm việc

Hình phạt có thể là:
- Rút lương từ 5-10 ngày
- Tạm ngừng công việc
- Chấm dứt hợp đồng lao động

CHƯƠNG VI: KỸ NĂNG VÀ ĐÀO TẠO

Điều 15: Chương trình đào tạo
Công ty cam kết cung cấp:
1. Đào tạo ban đầu cho nhân viên mới
2. Đào tạo chuyên ngành hàng năm
3. Hỗ trợ cho các khóa học ngoài
4. Tài trợ cho các chứng chỉ chuyên nghiệp

Điều 16: Phát triển sự nghiệp
Nhân viên có thể:
1. Xin chuyên môn
2. Xin thăng chức
3. Tham gia các dự án mới
4. Được hướng dẫn bởi những người có kinh nghiệm

CHƯƠNG VII: AN TOÀN VÀ SỨC KHỎE

Điều 17: Điều kiện làm việc an toàn
Công ty cam kết:
1. Cung cấp thiết bị bảo vệ
2. Bảo dưỡng các thiết bị thường xuyên
3. Đào tạo an toàn cho nhân viên
4. Có bảo hiểm tai nạn lao động

Điều 18: Sức khỏe
Công ty cung cấp:
1. Khám sức khỏe định kỳ hàng năm
2. Phòng y tế với nhân viên y tế
3. Quỹ hỗ trợ khi nhân viên bệnh
4. Chế độ nghỉ ốm

CHƯƠNG VIII: BẢO MẬT VÀ BẢO VỆ DỮ LIỆU

Điều 19: Bí mật thương mại
Nhân viên phải:
1. Giữ bí mật về các dự án công ty
2. Không tiết lộ thông tin khách hàng
3. Không copy dữ liệu công ty
4. Không sử dụng thông tin công ty cho mục đích cá nhân

Điều 20: Bảo vệ dữ liệu cá nhân
Công ty:
1. Chỉ thu thập dữ liệu cần thiết
2. Bảo mật dữ liệu nhân viên
3. Không chia sẻ dữ liệu với bên thứ ba (trừ pháp luật)
4. Có chính sách bảo vệ dữ liệu

CHƯƠNG IX: CÁC VẤN ĐỀ KHÁC

Điều 21: Nghỉ phép
Nhân viên có thể xin nghỉ phép:
1. Phép hàng năm: tối thiểu 12 ngày
2. Phép bệnh: với giấy chứng nhận từ bác sĩ
3. Phép gia đình: trong trường hợp khẩn cấp

Phải xin phép trước khi vắng mặt (trừ trường hợp khẩn cấp).

Điều 22: Kết thúc hợp đồng lao động
Khi kết thúc hợp đồng:
1. Hoàn lại tài sản công ty
2. Nhận quyết định chấm dứt
3. Được thanh toán lương còn lại
4. Được hỗ trợ tìm việc nếu cần

Điều 23: Tranh chấp lao động
Nếu có tranh chấp:
1. Thảo luận trực tiếp với quản lý
2. Liên hệ phòng nhân sự nếu không giải quyết
3. Có thể xin hòa giải
4. Nếu cần, đưa ra tòa án

CHƯƠNG X: ĐIỀU KHOẢN CUỐI CÙNG

Điều 24: Hiệu lực của nội quy
Nội quy này có hiệu lực kể từ ngày 01/01/2024.

Điều 25: Sửa đổi
Nội quy có thể được sửa đổi khi:
1. Có sự thay đổi pháp luật
2. Có sự đồng ý của đa số nhân viên
3. Có quyết định từ lãnh đạo công ty

Điều 26: Giải thích
Bất kỳ điều khoản nào không rõ sẽ được giải thích bởi phòng nhân sự.

Điều 27: Áp dụng
Nội quy này áp dụng cho tất cả nhân viên của công ty ABC.

Ngày được phê duyệt: 01/01/2024
Ký bởi: Ban lãnh đạo công ty ABC
""".strip() * 5  # Replicate 5 times to simulate large document

    processor = DocumentProcessor()

    # Test chunking
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
        f.write(long_text)
        temp_file = f.name

    try:
        documents = processor.process_documents(source=temp_file, is_directory=False)

        print("\n📊 CHUNK COUNT TEST")
        print(f"Total document chunks: {len(documents)}")
        print(f"Chunk sizes: {[len(d.page_content) for d in documents[:5]]}...")

        # Assertion
        assert len(documents) > 2, f"❌ Expected > 2 chunks, got {len(documents)}"
        print(f"✅ PASS: Got {len(documents)} chunks (expected > 2)")

    finally:
        Path(temp_file).unlink()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.ollama
def test_postgres_insertion_deduplication():
    """Test: PostgreSQL insertion should preserve all chunks, not deduplicate them."""

    # Create test documents
    test_chunks = [
        "Điều 1: Quy định chung. Nội quy này áp dụng cho tất cả nhân viên.",
        "Điều 2: Quyền của nhân viên. Nhân viên có quyền được lương đầy đủ.",
        "Điều 3: Nghĩa vụ. Nhân viên phải tuân thủ quy định.",
        "Điều 4: Thời gian. Thời gian làm việc là 8:00-17:00.",
        "Điều 5: Lương. Lương được trả hàng tháng.",
    ]

    from langchain_core.documents import Document

    documents = [
        Document(
            page_content=content,
            metadata={
                "source": "test_document.txt",
                "file_path": "test_document.txt",
                "file_name": "test_document.txt",
            }
        )
        for content in test_chunks
    ]

    embedding_manager = EmbeddingManager()
    vector_store = VectorStoreManager(
        embedding_manager=embedding_manager,
        backend="postgres"
    )

    try:
        # Add documents
        print("\n📊 DATABASE INSERTION TEST")
        print(f"Adding {len(documents)} chunks to PostgreSQL...")

        ids = vector_store.add_documents(documents)

        print(f"Inserted IDs: {ids}")
        print("✅ Documents inserted")

        # Query back
        with vector_store._get_postgres_connection() as conn:
            result = conn.execute(
                f"SELECT COUNT(*) as cnt FROM {vector_store.postgres_schema}.{vector_store.postgres_table_name}"
            ).fetchone()

            chunk_count = result["cnt"] if result else 0
            print(f"Chunks in database: {chunk_count}")

            # Show chunk content_hash info
            rows = conn.execute(
                f"""
                SELECT content_hash, content FROM {vector_store.postgres_schema}.{vector_store.postgres_table_name}
                LIMIT 10
                """
            ).fetchall()

            print("\nChunk samples (content_hash, content_length):")
            for row in rows:
                content_len = len(row.get("content", ""))
                print(f"  {row.get('content_hash', 'N/A')[:16]}... : {content_len} chars")
    finally:
        # Cleanup test documents to prevent database pollution
        try:
            with vector_store._get_postgres_connection() as conn:
                conn.execute(
                    f"DELETE FROM {vector_store.postgres_schema}.{vector_store.postgres_table_name} "
                    "WHERE document_id IN (SELECT id FROM public.documents WHERE file_name = %s)",
                    ("test_document.txt",)
                )
                conn.execute(
                    "DELETE FROM public.documents WHERE file_name = %s",
                    ("test_document.txt",)
                )
                print("🧹 Cleaned up test_document.txt chunks from database.")
        except Exception as e:
            print(f"⚠️ Error cleaning up test documents: {e}")



if __name__ == "__main__":
    print("🔍 DEBUGGING INGESTION PIPELINE\n")

    try:
        docs = test_document_processing_chunking()
        print(f"\n✅ Chunking test passed: {len(docs)} chunks created")
    except AssertionError as e:
        print(f"\n❌ Chunking test FAILED: {e}")
    except Exception as e:
        print(f"\n❌ Chunking test ERROR: {e}")

    try:
        test_postgres_insertion_deduplication()
        print("\n✅ Database insertion test completed")
    except Exception as e:
        print(f"\n❌ Database insertion ERROR: {e}")
