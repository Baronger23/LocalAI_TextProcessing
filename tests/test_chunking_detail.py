"""Test chunking logic specifically."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking import AdaptiveChunkingPipeline
from langchain_core.documents import Document


def test_adaptive_chunking_large_doc():
    """Test adaptive chunking with a large Vietnamese document."""
    
    # Large sample text
    text = """
NỘI QUY LAO ĐỘNG CÔNG TY ABC - Version 2024

CHƯƠNG I: QUY ĐỊNH CHUNG

Điều 1: Phạm vi áp dụng
Nội quy này áp dụng đối với tất cả nhân viên của công ty ABC, bao gồm nhân viên chính thức, nhân viên thử việc, nhân viên hợp đồng xác định thời hạn và nhân viên hợp đồng không xác định thời hạn. Các quy định này bắt buộc phải tuân thủ.

Điều 2: Mục đích và nguyên tắc
Mục đích của nội quy là xây dựng môi trường làm việc tích cực, chuyên nghiệp, đảm bảo quyền lợi của nhân viên và công ty, nâng cao năng suất lao động, và tạo điều kiện để nhân viên phát triển sự nghiệp.

Điều 3: Định nghĩa các thuật ngữ
Công ty là nơi làm việc của các nhân viên. Nhân viên là những người làm việc tại công ty. Quản lý là những người có trách nhiệm giám sát nhân viên. Lương là tiền công do công ty trả cho nhân viên theo quy định.

CHƯƠNG II: QUYỀN VÀ NGHĨA VỤ

Điều 4: Quyền của nhân viên
Nhân viên có quyền nhận lương đầy đủ và đúng hạn. Nhân viên có quyền làm việc trong môi trường an toàn. Nhân viên có quyền được tôn trọng và công bằng. Nhân viên có quyền được phát triển kỹ năng.

Điều 5: Nghĩa vụ của nhân viên
Nhân viên phải tuân thủ quy định của công ty. Nhân viên phải hoàn thành công việc được giao. Nhân viên phải bảo vệ tài sản công ty. Nhân viên phải giữ bí mật thương mại. Nhân viên phải có hành vi lịch sự với đồng nghiệp.

CHƯƠNG III: NGÀY VÀ GIỜ LÀM VIỆC

Điều 6: Thời gian làm việc
Thời gian làm việc bình thường từ thứ 2 đến thứ 6. Buổi sáng làm việc từ 8:00 đến 12:00. Buổi chiều làm việc từ 13:00 đến 17:00. Tổng cộng mỗi tuần là 40 giờ làm việc bình thường.

Điều 7: Ngày nghỉ
Các ngày lễ quốc gia được nghỉ. Nhân viên được 12 ngày hưởng lương hàng năm. Ngày phép hàng năm phải được sắp xếp hợp lý.

Điều 8: Làm việc ngoài giờ
Khi cần làm việc ngoài giờ, phải có sự chấp thuận từ quản lý. Sẽ được thanh toán theo tỷ lệ quy định. Không được vượt quá 40 giờ mỗi tháng trừ trường hợp đặc biệt.

CHƯƠNG IV: LƯƠNG VÀ PHÚC LỢI

Điều 9: Mức lương
Mức lương được quy định dựa trên chức vụ, kinh nghiệm, kỹ năng và thành tích công việc. Lương được trả hàng tháng, không chậm quá ngày 5 của tháng tiếp theo.

Điều 10: Phúc lợi
Công ty cung cấp bảo hiểm xã hội cho 30% của lương cơ bản. Bảo hiểm y tế được cung cấp cho tất cả nhân viên. Bảo hiểm thất nghiệp được trích từ lương. Quà tặng cho dịp Tết và các ngày lễ. Hỗ trợ học tập chuyên nghiệp.

Điều 11: Thưởng
Nhân viên sẽ được thưởng dựa trên kết quả công việc, thành tích xuất sắc, và đóng góp cho công ty.

CHƯƠNG V: KỶ LUẬT

Điều 12: Quy tắc ứng xử
Nhân viên phải đi làm đúng giờ. Nhân viên phải mặc trang phục phù hợp. Nhân viên phải giữ gìn vệ sinh. Không hút thuốc tại nơi làm việc ngoài khu hút thuốc. Không sử dụng rượu/bia tại nơi làm việc. Không sử dụng điện thoại cá nhân trong giờ làm việc trừ trường hợp khẩn cấp.

Điều 13: Vi phạm nhẹ
Vi phạm nhẹ bao gồm đi làm muộn dưới 30 phút, đi sớm dưới 30 phút, quên mang thẻ, và không tuân thủ trang phục. Hình phạt lần 1 là cảnh cáo. Hình phạt lần 2 là rút lương 1 ngày. Hình phạt lần 3 là rút lương 3 ngày.

Điều 14: Vi phạm nặng
Vi phạm nặng bao gồm đi làm muộ hơn 2 giờ, không đi làm không phép, tiết lộ bí mật công ty, làm hư hỏng tài sản công ty, gây mâu thuẫn với đồng nghiệp, và hành vi bạo lực tại nơi làm việc. Hình phạt có thể là rút lương từ 5-10 ngày, tạm ngừng công việc, hoặc chấm dứt hợp đồng lao động.

CHƯƠNG VI: KỸ NĂNG VÀ ĐÀO TẠO

Điều 15: Chương trình đào tạo
Công ty cam kết cung cấp đào tạo ban đầu cho nhân viên mới. Đào tạo chuyên ngành hàng năm sẽ được thực hiện. Hỗ trợ cho các khóa học ngoài. Tài trợ cho các chứng chỉ chuyên nghiệp.

Điều 16: Phát triển sự nghiệp
Nhân viên có thể xin chuyên môn. Nhân viên có thể xin thăng chức. Nhân viên có thể tham gia các dự án mới. Nhân viên được hướng dẫn bởi những người có kinh nghiệm.

CHƯƠNG VII: AN TOÀN VÀ SỨC KHỎE

Điều 17: Điều kiện làm việc an toàn
Công ty cam kết cung cấp thiết bị bảo vệ. Bảo dưỡng các thiết bị thường xuyên. Đào tạo an toàn cho nhân viên. Có bảo hiểm tai nạn lao động.

Điều 18: Sức khỏe
Công ty cung cấp khám sức khỏe định kỳ hàng năm. Phòng y tế với nhân viên y tế. Quỹ hỗ trợ khi nhân viên bệnh. Chế độ nghỉ ốm.

CHƯƠNG VIII: BẢO MẬT VÀ BẢO VỆ DỮ LIỆU

Điều 19: Bí mật thương mại
Nhân viên phải giữ bí mật về các dự án công ty. Nhân viên không tiết lộ thông tin khách hàng. Nhân viên không copy dữ liệu công ty. Nhân viên không sử dụng thông tin công ty cho mục đích cá nhân.

Điều 20: Bảo vệ dữ liệu cá nhân
Công ty chỉ thu thập dữ liệu cần thiết. Công ty bảo mật dữ liệu nhân viên. Công ty không chia sẻ dữ liệu với bên thứ ba trừ pháp luật. Công ty có chính sách bảo vệ dữ liệu.

CHƯƠNG IX: CÁC VẤN ĐỀ KHÁC

Điều 21: Nghỉ phép
Nhân viên có thể xin nghỉ phép. Phép hàng năm tối thiểu 12 ngày. Phép bệnh với giấy chứng nhận từ bác sĩ. Phép gia đình trong trường hợp khẩn cấp. Phải xin phép trước khi vắng mặt trừ trường hợp khẩn cấp.

Điều 22: Kết thúc hợp đồng lao động
Khi kết thúc hợp đồng, nhân viên hoàn lại tài sản công ty. Nhân viên nhận quyết định chấm dứt. Nhân viên được thanh toán lương còn lại. Nhân viên được hỗ trợ tìm việc nếu cần.

Điều 23: Tranh chấp lao động
Nếu có tranh chấp, có thảo luận trực tiếp với quản lý. Liên hệ phòng nhân sự nếu không giải quyết. Có thể xin hòa giải. Nếu cần, đưa ra tòa án lao động.

CHƯƠNG X: ĐIỀU KHOẢN CUỐI CÙNG

Điều 24: Hiệu lực của nội quy
Nội quy này có hiệu lực kể từ ngày 01/01/2024.

Điều 25: Sửa đổi
Nội quy có thể được sửa đổi khi có sự thay đổi pháp luật. Nội quy có thể sửa đổi khi có sự đồng ý của đa số nhân viên. Nội quy có thể sửa đổi khi có quyết định từ lãnh đạo công ty.

Điều 26: Giải thích
Bất kỳ điều khoản nào không rõ sẽ được giải thích bởi phòng nhân sự.

Điều 27: Áp dụng
Nội quy này áp dụng cho tất cả nhân viên của công ty ABC.

Ngày được phê duyệt: 01/01/2024
Ký bởi: Ban lãnh đạo công ty ABC
""" * 20  # Replicate to make it bigger
    
    pipeline = AdaptiveChunkingPipeline(strategy="adaptive")
    
    # Test 1: chunk_text directly
    print("TEST 1: chunk_text (raw text)")
    chunks_direct = pipeline.chunk_text(text, doc_title="Nội quy ABC")
    print(f"  Direct chunks: {len(chunks_direct)}")
    for i, chunk in enumerate(chunks_direct[:3]):
        print(f"    Chunk {i+1}: {len(chunk.page_content)} chars, breadcrumb: {chunk.metadata.get('breadcrumb', 'N/A')}")
    
    # Test 2: chunk_documents with Document wrapper
    print("\nTEST 2: chunk_documents (Document wrapper)")
    docs = [Document(page_content=text, metadata={"source": "test.txt", "file_path": "test.txt"})]
    chunks_wrapped = pipeline.chunk_documents(docs)
    print(f"  Wrapped chunks: {len(chunks_wrapped)}")
    for i, chunk in enumerate(chunks_wrapped[:3]):
        print(f"    Chunk {i+1}: {len(chunk.page_content)} chars, breadcrumb: {chunk.metadata.get('breadcrumb', 'N/A')}")


if __name__ == "__main__":
    test_adaptive_chunking_large_doc()
