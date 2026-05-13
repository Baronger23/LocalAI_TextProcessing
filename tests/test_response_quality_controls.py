from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.documents import Document

from src.config import BROAD_QUERY_TOP_K, DEFAULT_TOP_K, MAX_CONTEXT_CHARS
from src.rag.rag_pipeline import RAGPipeline


def _mock_pipeline(docs: list[Document] | None = None) -> RAGPipeline:
    llm = MagicMock()
    llm.model = "mock-llm"
    llm.generate_response.return_value = "cau tra loi day du"

    embeddings = MagicMock()
    embeddings.model = "mock-embed"

    vector_store = MagicMock()
    vector_store.get_collection_stats.return_value = {"count": len(docs or [])}
    vector_store.similarity_search.return_value = docs or []
    vector_store.keyword_search.return_value = []

    return RAGPipeline(
        llm_manager=llm,
        embedding_manager=embeddings,
        vector_store_manager=vector_store,
        query_rewrite_enabled=False,
        prompt_fusion_enabled=False,
    )


def _doc(content: str, source: str, index: int) -> Document:
    return Document(
        page_content=content,
        metadata={
            "source": source,
            "file_name": source,
            "breadcrumb": f"{source} > muc {index}",
            "chunk_index": index,
        },
    )


class TestQueryMode:
    def test_broad_query_keywords_are_detected(self):
        rag = _mock_pipeline()

        broad_questions = [
            "Các công trình lý luận về vai trò trong quan hệ quốc tế",
            "Phân tích vai trò của ASEAN trong hợp tác an ninh",
            "So sánh chủ nghĩa hiện thực và chủ nghĩa tự do",
            "Liệt kê các đặc điểm chính của quan hệ Việt Nam - EU",
            "Tổng hợp các hướng tiếp cận trong tài liệu",
        ]

        for question in broad_questions:
            assert rag.classify_query_mode(question) == "broad"

    def test_short_fact_query_is_focused(self):
        rag = _mock_pipeline()

        assert rag.classify_query_mode("ASEAN thành lập năm nào?") == "focused"


class TestAdaptiveTopK:
    def test_broad_query_uses_broad_top_k_when_unspecified(self):
        rag = _mock_pipeline()

        rag.query("Phân tích các công trình lý luận về vai trò")

        rag.vector_store_manager.similarity_search.assert_called_once()
        assert rag.vector_store_manager.similarity_search.call_args.kwargs["k"] == BROAD_QUERY_TOP_K

    def test_focused_query_uses_default_top_k_when_unspecified(self):
        rag = _mock_pipeline()

        rag.query("ASEAN thành lập năm nào?")

        rag.vector_store_manager.similarity_search.assert_called_once()
        assert rag.vector_store_manager.similarity_search.call_args.kwargs["k"] == DEFAULT_TOP_K

    def test_explicit_top_k_is_preserved(self):
        rag = _mock_pipeline()

        rag.query("Phân tích các công trình lý luận về vai trò", k=5)

        rag.vector_store_manager.similarity_search.assert_called_once()
        assert rag.vector_store_manager.similarity_search.call_args.kwargs["k"] == 5


class TestKeywordSupplement:
    def test_broad_query_uses_keyword_supplement(self):
        vector_docs = [_doc("Nội dung vector về vai trò ASEAN.", "vector.pdf", 1)]
        keyword_docs = [_doc("Các công trình liên quan đến Chủ nghĩa Kiến tạo.", "keyword.pdf", 1)]
        rag = _mock_pipeline(vector_docs)
        rag.vector_store_manager.keyword_search.return_value = keyword_docs

        result = rag.query("Các công trình lý luận về vai trò trong quan hệ quốc tế")

        assert rag.vector_store_manager.keyword_search.call_count >= 1
        assert "keyword.pdf" in result["context"]

    def test_focused_query_skips_keyword_supplement(self):
        rag = _mock_pipeline([_doc("ASEAN thành lập năm 1967.", "fact.pdf", 1)])

        rag.query("ASEAN thành lập năm nào?")

        rag.vector_store_manager.keyword_search.assert_not_called()


class TestStreamingMetadata:
    def test_query_stream_reports_sources_on_complete(self):
        docs = [_doc("Ná»™i dung vá» vai trÃ² cá»§a Chá»§ nghÄ©a Kiáº¿n táº¡o.", "lats.pdf", 3)]
        rag = _mock_pipeline(docs)
        rag.llm_manager.stream.return_value = iter(["Cau ", "tra ", "loi"])
        captured: dict = {}

        tokens = list(
            rag.query_stream(
                "PhÃ¢n tÃ­ch cÃ¡c cÃ´ng trÃ¬nh lÃ½ luáº­n vá» vai trÃ²",
                on_complete=captured.update,
            )
        )

        assert "".join(tokens) == "Cau tra loi"
        assert captured["answer"] == "Cau tra loi"
        assert captured["sources"]
        assert captured["sources"][0]["metadata"]["source"] == "lats.pdf"

    def test_query_stream_reports_cached_sources_on_complete(self):
        rag = _mock_pipeline()
        cache_key = rag.query_cache.make_key(
            query="ASEAN thÃ nh láº­p nÄƒm nÃ o?",
            top_k=DEFAULT_TOP_K,
            filters=None,
            model_version=rag.llm_manager.model,
        )
        cached = {
            "answer": "ASEAN thÃ nh láº­p nÄƒm 1967.",
            "sources": [{"content": "ASEAN 1967...", "metadata": {"source": "asean.pdf"}}],
            "context": "ASEAN 1967",
            "rewritten_query": None,
            "timing": {},
        }
        rag.query_cache.set(cache_key, cached)
        captured: dict = {}

        tokens = list(
            rag.query_stream(
                "ASEAN thÃ nh láº­p nÄƒm nÃ o?",
                on_complete=captured.update,
            )
        )

        assert "".join(tokens) == "ASEAN thÃ nh láº­p nÄƒm 1967. "
        assert captured["sources"][0]["metadata"]["source"] == "asean.pdf"
        rag.vector_store_manager.similarity_search.assert_not_called()


class TestContextPacking:
    def test_context_packing_dedupes_and_adds_source_headers(self):
        duplicate = "Nội dung trùng lặp về chủ nghĩa hiện thực và quyền lực."
        docs = [
            _doc(duplicate, "a.pdf", 1),
            _doc(duplicate, "a.pdf", 2),
            _doc("Nội dung khác về chủ nghĩa tự do và hợp tác.", "b.pdf", 1),
        ]
        rag = _mock_pipeline(docs)

        context = rag._build_context(docs, mode="broad")

        assert context.count(duplicate) == 1
        assert "[Nguồn: a.pdf]" in context
        assert "[Nguồn: b.pdf]" in context

    def test_context_packing_respects_max_context_chars(self):
        docs = [
            _doc("A" * (MAX_CONTEXT_CHARS // 2), "a.pdf", 1),
            _doc("B" * (MAX_CONTEXT_CHARS // 2), "b.pdf", 1),
            _doc("C" * (MAX_CONTEXT_CHARS // 2), "c.pdf", 1),
        ]
        rag = _mock_pipeline(docs)

        context = rag._build_context(docs, mode="broad")

        assert len(context) <= MAX_CONTEXT_CHARS
        assert "[Nguồn: a.pdf]" in context
        assert "[Nguồn: b.pdf]" in context


def test_app_prompt_is_academic_and_preserves_memory_context():
    from app import build_system_prompt

    prompt = build_system_prompt(
        summary="Người dùng đang hỏi về lý thuyết vai trò.",
        user_memories=[{"memory_type": "preference", "content": "Muốn câu trả lời có phân tích."}],
    )

    lowered = prompt.lower()
    assert "đúng trọng tâm" in lowered
    assert "đầy đủ" in lowered
    assert "phân tích" in lowered
    assert "thiếu dữ liệu" in lowered or "chưa đủ thông tin" in lowered
    assert "lý thuyết vai trò" in lowered
    assert "muốn câu trả lời có phân tích" in lowered
