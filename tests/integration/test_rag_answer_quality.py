"""
Integration Test — RAG Answer Quality
======================================
Test thật: gọi Ollama + PostgreSQL thật, không mock.

Câu hỏi: "Các công trình lý luận về vai trò trong quan hệ quốc tế"

Kiểm tra câu trả lời có đề cập đủ 5 ý lớn:
  1. Chủ nghĩa Hiện thực (Realism)
  2. Chủ nghĩa Tự do (Liberalism)
  3. Chủ nghĩa Kiến tạo (Constructivism)
  4. Lý thuyết Vai trò (Role Theory)
  5. Phân tích Mạng lưới Xã hội (SNA)

Chạy:
    venv\\Scripts\\pytest.exe tests/integration/test_rag_answer_quality.py -v -s

Yêu cầu:
    - Ollama đang chạy tại http://localhost:11434
    - PostgreSQL đang chạy và đã có dữ liệu được index
    - File .env đã được cấu hình đúng
"""
from __future__ import annotations

import sys
import textwrap
import time
from pathlib import Path

import pytest

# Đảm bảo src/ nằm trong path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag import RAGPipeline

# ---------------------------------------------------------------------------
# Câu hỏi và các ý lớn cần kiểm tra
# ---------------------------------------------------------------------------

QUERY = "Các công trình lý luận về vai trò trong quan hệ quốc tế"

# Mỗi ý lớn: (tên hiển thị, danh sách từ khóa — đúng ít nhất 1 từ là đạt)
EXPECTED_TOPICS = [
    (
        "Chủ nghĩa Hiện thực (Realism)",
        ["hiện thực", "realism", "realist", "waltz", "morgenthau", "quyền lực", "power"],
    ),
    (
        "Chủ nghĩa Tự do (Liberalism)",
        ["tự do", "liberalism", "liberal", "keohane", "nye", "hợp tác", "interdependence", "phụ thuộc lẫn nhau"],
    ),
    (
        "Chủ nghĩa Kiến tạo (Constructivism)",
        ["kiến tạo", "constructivism", "constructivist", "wendt", "bản sắc", "identity", "chuẩn mực", "norm"],
    ),
    (
        "Lý thuyết Vai trò (Role Theory)",
        ["vai trò", "role theory", "role", "holsti", "thuyết vai trò", "nhận thức vai trò", "role conception"],
    ),
    (
        "Phân tích Mạng lưới Xã hội (SNA)",
        ["mạng lưới", "social network", "sna", "network analysis", "phân tích mạng", "centrality"],
    ),
]

# Ngưỡng: cần đạt ít nhất bao nhiêu ý lớn để test PASS
MIN_TOPICS_REQUIRED = 3  # ≥ 3/5 ý lớn


# ---------------------------------------------------------------------------
# Fixture: khởi tạo RAGPipeline một lần cho cả module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rag_pipeline():
    """Khởi tạo RAGPipeline thật (Ollama + PostgreSQL)."""
    try:
        pipeline = RAGPipeline()
        return pipeline
    except Exception as exc:
        pytest.skip(f"Không thể khởi tạo RAGPipeline: {exc}")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _check_topic(answer_lower: str, keywords: list[str]) -> tuple[bool, str]:
    """Kiểm tra answer có chứa ít nhất 1 keyword của topic không."""
    for kw in keywords:
        if kw.lower() in answer_lower:
            return True, kw
    return False, ""


def _print_report(answer: str, topic_results: list[tuple[str, bool, str]]) -> None:
    """In báo cáo chi tiết ra stdout."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"QUERY: {QUERY}")
    print(separator)
    print("\n📝 CÂU TRẢ LỜI CỦA CHATBOT:")
    print("-" * 70)
    # Wrap dài để dễ đọc
    for line in answer.split("\n"):
        if line.strip():
            print(textwrap.fill(line, width=70))
        else:
            print()
    print("-" * 70)

    print("\n📊 ĐÁNH GIÁ THEO CÁC Ý LỚN:")
    passed = 0
    for topic_name, found, matched_kw in topic_results:
        status = "✅ CÓ" if found else "❌ THIẾU"
        detail = f"(từ khóa: '{matched_kw}')" if found else ""
        print(f"  {status}  {topic_name} {detail}")
        if found:
            passed += 1

    print(f"\n📈 KẾT QUẢ: {passed}/{len(EXPECTED_TOPICS)} ý lớn được đề cập")
    print(f"   Ngưỡng yêu cầu: ≥ {MIN_TOPICS_REQUIRED}/{len(EXPECTED_TOPICS)}")
    verdict = "✅ ĐẠT" if passed >= MIN_TOPICS_REQUIRED else "❌ CHƯA ĐẠT"
    print(f"   Kết luận: {verdict}")
    print(separator)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRAGAnswerQuality:
    """Integration tests kiểm tra chất lượng câu trả lời thật từ RAG pipeline."""

    def test_retrieval_returns_documents(self, rag_pipeline: RAGPipeline):
        """
        Kiểm tra pipeline retrieve được tài liệu liên quan.
        Nếu không có tài liệu nào, câu trả lời sẽ không có nội dung.
        """
        docs = rag_pipeline.vector_store_manager.similarity_search(
            query=QUERY,
            keyword_query=QUERY,
            k=8,
        )
        print(f"\n🔍 Số tài liệu retrieve được: {len(docs)}")
        for i, doc in enumerate(docs[:5], 1):
            breadcrumb = doc.metadata.get("breadcrumb", "N/A")
            preview = doc.page_content[:120].replace("\n", " ")
            print(f"  [{i}] {breadcrumb}")
            print(f"       {preview}...")

        assert len(docs) > 0, (
            "Không retrieve được tài liệu nào. "
            "Kiểm tra lại dữ liệu đã được index vào PostgreSQL chưa."
        )

    def test_answer_covers_expected_topics(self, rag_pipeline: RAGPipeline):
        """
        Test chính: gửi câu hỏi thật, kiểm tra câu trả lời có đủ 5 ý lớn không.

        Đây là integration test thật — gọi Ollama và PostgreSQL.
        Có thể mất 10-30 giây tùy tốc độ máy.
        """
        print(f"\n⏳ Đang gửi câu hỏi đến RAG pipeline...")
        start = time.perf_counter()

        result = rag_pipeline.query(
            question=QUERY,
            k=8,
        )

        elapsed = time.perf_counter() - start
        answer = result.get("answer", "")
        timing = result.get("timing", {})

        print(f"⏱️  Thời gian phản hồi: {elapsed:.1f}s")
        print(f"   embedding_ms={timing.get('embedding_ms', 0):.0f}  "
              f"search_ms={timing.get('search_ms', 0):.0f}  "
              f"llm_ms={timing.get('llm_ms', 0):.0f}  "
              f"total_ms={timing.get('total_ms', 0):.0f}")

        assert answer, "Câu trả lời rỗng — pipeline có vấn đề."
        assert len(answer) > 50, (
            f"Câu trả lời quá ngắn ({len(answer)} ký tự): {answer!r}"
        )

        # Kiểm tra từng ý lớn
        answer_lower = answer.lower()
        topic_results = []
        for topic_name, keywords in EXPECTED_TOPICS:
            found, matched_kw = _check_topic(answer_lower, keywords)
            topic_results.append((topic_name, found, matched_kw))

        _print_report(answer, topic_results)

        # Đếm số ý lớn đạt
        topics_found = sum(1 for _, found, _ in topic_results if found)

        assert topics_found >= MIN_TOPICS_REQUIRED, (
            f"Câu trả lời chỉ đề cập {topics_found}/{len(EXPECTED_TOPICS)} ý lớn "
            f"(yêu cầu ≥ {MIN_TOPICS_REQUIRED}).\n"
            f"Các ý thiếu: "
            + ", ".join(name for name, found, _ in topic_results if not found)
        )

    def test_answer_not_breadcrumb_only(self, rag_pipeline: RAGPipeline):
        """
        Kiểm tra câu trả lời KHÔNG phải chỉ là breadcrumb/chỉ mục.
        Đây là regression test cho Bug 1 đã fix.
        """
        result = rag_pipeline.query(question=QUERY, k=8)
        answer = result.get("answer", "")

        # Breadcrumb pattern: "X > Y > Z" hoặc "Chương X: Phần Y"
        import re
        breadcrumb_pattern = re.compile(
            r'^[\w\s]+\s*[>:]\s*[\w\s]+(\s*[>:]\s*[\w\s]+)*$',
            re.MULTILINE
        )

        # Nếu toàn bộ answer chỉ là breadcrumb (< 3 dòng và match pattern)
        lines = [l.strip() for l in answer.split("\n") if l.strip()]
        all_breadcrumbs = all(breadcrumb_pattern.match(line) for line in lines[:3]) if lines else False

        print(f"\n🔍 Kiểm tra breadcrumb: answer có {len(lines)} dòng")
        print(f"   Độ dài answer: {len(answer)} ký tự")

        assert not (all_breadcrumbs and len(answer) < 200), (
            f"Bug 1 regression: câu trả lời có vẻ chỉ là breadcrumb/chỉ mục:\n{answer}"
        )

    def test_answer_no_json_artifacts(self, rag_pipeline: RAGPipeline):
        """
        Kiểm tra câu trả lời KHÔNG chứa JSON artifact.
        Đây là regression test cho Bug 1 đã fix.
        """
        result = rag_pipeline.query(question=QUERY, k=8)
        answer = result.get("answer", "")

        json_artifacts = [
            '"answer":',
            '"rewritten_query":',
            '"confidence":',
            '```json',
        ]

        found_artifacts = [a for a in json_artifacts if a in answer]

        print(f"\n🔍 Kiểm tra JSON artifact trong answer:")
        if found_artifacts:
            print(f"   ❌ Tìm thấy: {found_artifacts}")
        else:
            print(f"   ✅ Không có JSON artifact")

        assert not found_artifacts, (
            f"Bug 1 regression: câu trả lời chứa JSON artifact: {found_artifacts}\n"
            f"Answer (200 ký tự đầu): {answer[:200]}"
        )
