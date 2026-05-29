import sys
import time
from pathlib import Path

# Force stdout/stderr to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from src.rag.rag_pipeline import RAGPipeline

EVAL_QUESTIONS = [
    {
        "id": 1,
        "question": "Quy định về mật khẩu tài khoản thông thường và MFA trong chính sách sử dụng tài nguyên CNTT như thế nào?",
        "expected": "Mật khẩu tối thiểu 14 ký tự, phải bật MFA và không tái sử dụng."
    },
    {
        "id": 2,
        "question": "Theo chính sách công nợ phải trả, đơn mua hàng từ bao nhiêu tiền trở lên thì bắt buộc phải có tối thiểu 3 báo giá hợp lệ?",
        "expected": "Đơn mua hàng từ 50.000.000 VND trở lên."
    },
    {
        "id": 3,
        "question": "Hạn mức phòng khách sạn tại TP.HCM cho nhân viên cấp Manager khi đi công tác là bao nhiêu?",
        "expected": "Hạn mức khách sạn tại TP.HCM cho cấp Manager là 2.000.000 VND/đêm."
    },
    {
        "id": 4,
        "question": "Nhân viên chính thức của công ty có bao nhiêu ngày nghỉ phép hưởng lương mỗi năm theo sổ tay nhân viên?",
        "expected": "Nhân viên chính thức có 14 ngày nghỉ phép hưởng lương mỗi năm."
    },
    {
        "id": 5,
        "question": "Thời hạn để phản hồi các yêu cầu truy cập hoặc chỉnh sửa dữ liệu cá nhân (DSAR) là bao nhiêu ngày làm việc?",
        "expected": "Yêu cầu DSAR phải được phản hồi trong vòng 15 ngày làm việc."
    }
]

def main():
    print("=" * 80)
    print("🎬 RUNNING 5 EVALUATION QUESTIONS FOR NEW COMPANY POLICIES")
    print("=" * 80)

    rag = RAGPipeline()
    output_blocks = [
        "# Kết Quả Đánh Giá RAG Trên Tài Liệu Chính Sách Công Ty (5 Câu Hỏi Mẫu)\n\n",
        f"Thời gian đánh giá: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        "--- \n\n"
    ]

    for item in EVAL_QUESTIONS:
        q_id = item["id"]
        q_text = item["question"]
        expected = item["expected"]

        print(f"\n[{q_id}/5] Đang xử lý câu hỏi: {q_text}")
        start_time = time.perf_counter()

        try:
            # Query RAG
            res = rag.query(q_text, k=5)
            answer = res["answer"]
            sources = res["sources"]
            elapsed = time.perf_counter() - start_time
            print(f"      Hoàn thành trong {elapsed:.2f}s")
        except Exception as exc:
            answer = f"⚠️ Lỗi thực thi RAG: {exc}"
            sources = []
            elapsed = time.perf_counter() - start_time
            print(f"      Thất bại trong {elapsed:.2f}s - Lỗi: {exc}")

        # Format sources
        sources_summary = []
        for i, s in enumerate(sources[:3]):
            meta = s.get("metadata") or {}
            source_file = Path(meta.get("source", "unknown")).name
            sec = meta.get("section_title") or "unknown"
            sources_summary.append(f"- [{i+1}] {source_file} (Mục: {sec})")
        sources_str = "\n".join(sources_summary) if sources_summary else "- Không tìm thấy"

        # Append to report
        block = (
            f"## [Câu hỏi {q_id}]\n\n"
            f"**Câu hỏi:** {q_text}\n\n"
            f"**Kỳ vọng cốt lõi:** {expected}\n\n"
            f"### 🔹 Câu trả lời của RAG:\n\n"
            f"{answer}\n\n"
            f"### 🔹 Các nguồn đã truy xuất (Top 3):\n\n"
            f"{sources_str}\n\n"
            f"**Thời gian chạy:** {elapsed:.2f}s\n\n"
            "--- \n\n"
        )
        output_blocks.append(block)

    # Save report
    output_file = Path(__file__).parent.parent / "evaluation" / "company_policies_eval_results.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("".join(output_blocks), encoding="utf-8")
    print(f"\n✅ Đánh giá hoàn tất! Kết quả đã được lưu tại: {output_file.relative_to(Path(__file__).parent.parent)}")

if __name__ == "__main__":
    main()
