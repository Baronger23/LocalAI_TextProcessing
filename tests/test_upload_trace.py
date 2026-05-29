"""Simulate upload and check logging."""
import sys
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline


def test_upload_simulation():
    """Simulate uploading a file and trace the pipeline."""
    print("\n[TRACE] SIMULATING FILE UPLOAD\n")
    
    # Create a test directory with a single file
    test_dir = Path(tempfile.mkdtemp(prefix="upload_test_"))
    
    # Create a moderately large TXT file
    txt_file = test_dir / "test_large_doc.txt"
    
    content = """NỘI QUY LAO ĐỘNG CÔNG TY ABC - 2024 Edition

CHƯƠNG I: QUY ĐỊNH CHUNG

Điều 1: Phạm vi áp dụng
Nội quy này áp dụng đối với tất cả nhân viên của công ty ABC bao gồm nhân viên chính thức, 
nhân viên thử việc, nhân viên hợp đồng xác định thời hạn và nhân viên hợp đồng không xác định thời hạn. 
Các quy định này bắt buộc phải tuân thủ trong mọi trường hợp và không có ngoại lệ.

Điều 2: Mục đích và nguyên tắc
Mục đích của nội quy này là để xây dựng một môi trường làm việc tích cực, chuyên nghiệp và 
hiệu quả. Chúng tôi cam kết đảm bảo quyền lợi của nhân viên và công ty, nâng cao năng suất lao động, 
và tạo điều kiện để nhân viên phát triển sự nghiệp một cách bền vững.

Điều 3: Định nghĩa các thuật ngữ
Công ty là nơi làm việc chính của các nhân viên. Nhân viên là những người làm việc tại công ty. 
Quản lý là những người có trách nhiệm giám sát và hướng dẫn nhân viên. Lương là tiền công do công ty trả cho nhân viên.

CHƯƠNG II: QUYỀN VÀ NGHĨA VỤ

Điều 4: Quyền của nhân viên
Nhân viên có quyền nhận lương đầy đủ và đúng hạn theo quy định pháp luật. 
Nhân viên có quyền làm việc trong môi trường an toàn và được cảnh báo khi có nguy hiểm. 
Nhân viên có quyền được tôn trọng và công bằng trong mọi tình huống. 
Nhân viên có quyền được phát triển kỹ năng thông qua các chương trình đào tạo.

Điều 5: Nghĩa vụ của nhân viên
Nhân viên phải tuân thủ mọi quy định của công ty và pháp luật hiện hành. 
Nhân viên phải hoàn thành đầy đủ công việc được giao với chất lượng cao nhất. 
Nhân viên phải bảo vệ tài sản công ty và không được làm hư hỏng. 
Nhân viên phải giữ bí mật thương mại và thông tin confidential của công ty.

CHƯƠNG III: NGÀY VÀ GIỜ LÀM VIỆC

Điều 6: Thời gian làm việc
Thời gian làm việc bình thường từ thứ 2 đến thứ 6 hàng tuần. 
Buổi sáng làm việc từ 8:00 đến 12:00 (4 giờ). 
Buổi chiều làm việc từ 13:00 đến 17:00 (4 giờ). 
Tổng cộng mỗi tuần là 40 giờ làm việc bình thường không tính giờ extra.

Điều 7: Ngày nghỉ
Các ngày lễ quốc gia được nghỉ đầy đủ lương. 
Nhân viên được 12 ngày hưởng lương hàng năm để nghỉ dưỡng. 
Ngày phép hàng năm phải được sắp xếp hợp lý và không được tích lũy quá 30 ngày.

Điều 8: Làm việc ngoài giờ
Khi cần làm việc ngoài giờ bình thường, phải có sự chấp thuận bằng văn bản từ quản lý. 
Sẽ được thanh toán theo tỷ lệ 1.5x lương giờ bình thường. 
Không được vượt quá 40 giờ mỗi tháng trừ trường hợp đặc biệt và khẩn cấp.

CHƯƠNG IV: LƯƠNG VÀ PHÚC LỢI

Điều 9: Mức lương
Mức lương được quy định dựa trên chức vụ, kinh nghiệm, kỹ năng và thành tích công việc. 
Lương được trả hàng tháng, không chậm quá ngày 5 của tháng tiếp theo. 
Mỗi nhân viên sẽ nhận một bảng lương chi tiết vào ngày nhận lương.

Điều 10: Phúc lợi
Công ty cung cấp bảo hiểm xã hội cho 30% của lương cơ bản hàng tháng. 
Bảo hiểm y tế được cung cấp cho tất cả nhân viên và gia đình. 
Bảo hiểm thất nghiệp được trích từ lương hàng tháng theo quy định. 
Quà tặng cho dịp Tết và các ngày lễ quan trọng khác.

Điều 11: Thưởng
Nhân viên sẽ được thưởng dựa trên kết quả công việc và đóng góp tích cực cho công ty.

CHƯƠNG V: KỶ LUẬT

Điều 12: Quy tắc ứng xử
Nhân viên phải đi làm đúng giờ quy định không được muộn trừ lý do chính đáng. 
Nhân viên phải mặc trang phục phù hợp và chuyên nghiệp tại nơi làm việc. 
Nhân viên phải giữ gìn vệ sinh và trật tự tại nơi làm việc. 
Không hút thuốc tại nơi làm việc ngoài khu hút thuốc được chỉ định. 
Không sử dụng rượu/bia tại nơi làm việc trong mọi trường hợp. 
Không sử dụng điện thoại cá nhân trong giờ làm việc trừ trường hợp khẩn cấp.

Điều 13: Vi phạm nhẹ
Vi phạm nhẹ bao gồm đi làm muộn dưới 30 phút, đi sớm dưới 30 phút, quên mang thẻ. 
Hình phạt lần 1 là cảnh cáo bằng văn bản. 
Hình phạt lần 2 là rút lương 1 ngày. 
Hình phạt lần 3 là rút lương 3 ngày.

Điều 14: Vi phạm nặng
Vi phạm nặng bao gồm đi làm muộ hơn 2 giờ liên tục, không đi làm không phép. 
Tiết lộ bí mật công ty cho bên thứ ba hoặc đối thủ cạnh tranh. 
Làm hư hỏng tài sản công ty một cách cố ý hoặc do sơ suất. 
Gây mâu thuẫn nghiêm trọng với đồng nghiệp hoặc quản lý. 
Hành vi bạo lực hoặc mặc cả tại nơi làm việc.
""" * 5  # Replicate to make it larger
    
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    file_size_mb = txt_file.stat().st_size / (1024 * 1024)
    print(f"Created test file: {txt_file.name} ({file_size_mb:.2f} MB)")
    
    with patch("src.rag.vector_store.VectorStoreManager.add_documents") as mock_add:
        mock_add.return_value = []
        try:
            rag = RAGPipeline()
            print(f"\nCalling rag.load_documents('{test_dir}')...\n")
            count = rag.load_documents(str(test_dir))
            
            print(f"\n[RESULT] {count} chunks loaded and inserted")
            
        finally:
            # Clean up
            shutil.rmtree(test_dir)
            print(f"\nCleaned up test directory")


if __name__ == "__main__":
    from unittest.mock import patch
    test_upload_simulation()

