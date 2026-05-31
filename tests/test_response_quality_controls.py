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

        assert rag.vector_store_manager.similarity_search.call_args_list[0].kwargs["k"] == max(rag.mmr_fetch_k if rag.mmr_enabled else 35, BROAD_QUERY_TOP_K + 20)

    def test_focused_query_uses_default_top_k_when_unspecified(self):
        rag = _mock_pipeline()

        rag.query("ASEAN thành lập năm nào?")

        rag.vector_store_manager.similarity_search.assert_called_once()
        assert rag.vector_store_manager.similarity_search.call_args.kwargs["k"] == max(rag.mmr_fetch_k if rag.mmr_enabled else 35, DEFAULT_TOP_K + 20)

    def test_explicit_top_k_is_preserved(self):
        rag = _mock_pipeline()

        rag.query("Phân tích các công trình lý luận về vai trò", k=5)

        assert rag.vector_store_manager.similarity_search.call_args_list[0].kwargs["k"] == max(rag.mmr_fetch_k if rag.mmr_enabled else 35, 5 + 20)



class TestKeywordSupplement:
    def test_broad_query_uses_keyword_supplement(self):
        vector_docs = [_doc("Nội dung vector về vai trò ASEAN.", "vector.pdf", 1)]
        keyword_docs = [_doc("Các công trình liên quan đến Chủ nghĩa Kiến tạo.", "keyword.pdf", 1)]
        rag = _mock_pipeline(vector_docs)
        rag.vector_store_manager.keyword_search.return_value = keyword_docs

        result = rag.query("Các công trình lý luận về vai trò trong quan hệ quốc tế")

        assert rag.vector_store_manager.keyword_search.call_count >= 1
        assert "keyword.pdf" in result["context"]

    def test_focused_query_uses_keyword_supplement(self):
        vector_docs = [_doc("Nội dung nền về ASEAN.", "vector.pdf", 1)]
        keyword_docs = [_doc("ASEAN thành lập năm 1967.", "fact.pdf", 1)]
        rag = _mock_pipeline(vector_docs)
        rag.vector_store_manager.keyword_search.return_value = keyword_docs

        result = rag.query("ASEAN thành lập năm nào?")

        rag.vector_store_manager.keyword_search.assert_called()
        assert "fact.pdf" in result["context"]

    def test_keyword_supplement_does_not_add_domain_canned_queries(self):
        queries = RAGPipeline._build_keyword_supplement_queries(
            "Các công trình nghiên cứu về vai trò của ASEAN trong khu vực Đông Á"
        )

        assert "công trình liên quan vai trò chủ thể quan hệ quốc tế" not in queries
        assert "vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng" not in queries

    def test_sentence_initial_verb_is_not_entity_boosted(self):
        assert RAGPipeline._extract_proper_nouns(
            "Xuất dữ liệu cá nhân khỏi hệ thống phân tích cần ai phê duyệt?"
        ) == []

    def test_sentence_initial_name_still_entity_boosted(self):
        assert RAGPipeline._extract_proper_nouns(
            "Amitav Acharya phân tích ASEAN như thế nào?"
        ) == ["Amitav", "Acharya", "ASEAN"]


class TestBroadQueryDecomposition:
    @staticmethod
    def _outline_doc() -> Document:
        return Document(
            page_content=(
                "Các mục chính trong tài liệu:\n"
                "- Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Hiện thực\n"
                "- Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Tự do\n"
                "- Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Kiến tạo\n"
                "- Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Lý thuyết Vai trò (Role theory)\n"
                "- Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Phân tích Mạng lưới Xã hội (SNA)\n"
            ),
            metadata={
                "source": "outline.pdf",
                "file_name": "outline.pdf",
                "chunk_type": "outline",
                "section_title": "Tổng quan các mục chính",
                "chunk_index": 0,
            },
        )

    def test_broad_query_decomposes_from_retrieved_document_headings(self):
        facets = RAGPipeline.decompose_broad_query(
            "Các công trình lý luận về vai trò trong quan hệ quốc tế",
            seed_docs=[self._outline_doc()],
        )

        labels = [facet["label"] for facet in facets]
        assert labels == [
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Hiện thực",
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Tự do",
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Chủ nghĩa Kiến tạo",
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Lý thuyết Vai trò (Role theory)",
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế chịu ảnh hưởng của Phân tích Mạng lưới Xã hội (SNA)",
        ]

    def test_broad_query_does_not_decompose_without_document_headings(self):
        facets = RAGPipeline.decompose_broad_query(
            "Các công trình lý luận về vai trò trong quan hệ quốc tế"
        )

        assert facets == []

    def test_outline_seed_search_finds_outline_chunks_before_facet_search(self):
        outline_doc = self._outline_doc()
        rag = _mock_pipeline()
        rag.vector_store_manager.keyword_search.return_value = [outline_doc]

        seed_docs = rag._outline_seed_search(
            "Các công trình lý luận về vai trò trong quan hệ quốc tế",
            "broad",
        )

        assert seed_docs == [outline_doc]
        first_query = rag.vector_store_manager.keyword_search.call_args_list[0].kwargs["query"]
        assert first_query == "Các mục chính trong tài liệu"

    def test_decomposed_retrieval_fetches_each_facet_without_canned_answer(self):
        outline_doc = self._outline_doc()
        rag = _mock_pipeline([outline_doc])

        def section_doc(label: str, source: str) -> Document:
            doc = _doc(f"Nội dung của {label}", source, 1)
            doc.metadata["section_title"] = label
            return doc

        facets = RAGPipeline.decompose_broad_query(
            "Các công trình lý luận về vai trò trong quan hệ quốc tế",
            seed_docs=[outline_doc],
        )
        rag.vector_store_manager.similarity_search.side_effect = [
            [outline_doc],
            *[[section_doc(facet["label"], f"facet-{index}.pdf")] for index, facet in enumerate(facets)],
        ]

        result = rag.query("Các công trình lý luận về vai trò trong quan hệ quốc tế")

        queries = [
            call.kwargs["query"]
            for call in rag.vector_store_manager.similarity_search.call_args_list
        ]
        assert queries[0] == "Các công trình lý luận về vai trò trong quan hệ quốc tế"
        for facet in facets:
            assert facet["query"] in queries[1:]
            assert f"[GROUP: {facet['label']}]" in result["context"]

    def test_decomposed_retrieval_drops_wrong_section_matches(self):
        outline_doc = self._outline_doc()
        facets = RAGPipeline.decompose_broad_query(
            "Các công trình lý luận về vai trò trong quan hệ quốc tế",
            seed_docs=[outline_doc],
        )
        target_label = facets[1]["label"]
        wrong_label = facets[-1]["label"]
        target_seed_doc = Document(
            page_content=f"- {target_label}",
            metadata={
                "source": "outline.pdf",
                "file_name": "outline.pdf",
                "chunk_type": "outline",
                "section_title": "Tổng quan các mục chính",
                "chunk_index": 0,
            },
        )
        rag = _mock_pipeline()
        wrong_doc = _doc("Nội dung có nhắc tự do nhưng section là SNA", "sna.pdf", 1)
        wrong_doc.metadata["section_title"] = wrong_label

        rag.vector_store_manager.similarity_search.return_value = [wrong_doc]
        rag.vector_store_manager.keyword_search.return_value = []

        docs = rag._decomposed_broad_search(
            target_label,
            "broad",
            seed_docs=[target_seed_doc],
        )

        assert docs == []


class TestEvidenceRerank:
    def test_rerank_prioritizes_structural_and_lexical_evidence(self):
        rag = _mock_pipeline()
        question = "Các công trình nghiên cứu về vai trò của ASEAN trong khu vực Đông Á"
        generic = _doc(
            "ASEAN có vai trò trung tâm trong hợp tác khu vực Đông Á.",
            "generic.pdf",
            1,
        )
        evidence = _doc(
            "Kalevi J. Holsti, John Gerard Ruggie và Peter J. Katzenstein "
            "được sử dụng làm nền tảng nghiên cứu vai trò chủ thể quốc tế.",
            "evidence.pdf",
            2,
        )
        evidence.metadata["section_title"] = (
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế "
            "chịu ảnh hưởng của Lý thuyết Vai trò (Role theory)"
        )
        evidence.metadata["retrieval_group"] = evidence.metadata["section_title"]

        ranked = rag._rerank_retrieved_documents(question, [generic, evidence], "broad")

        assert ranked[0] == evidence

    def test_context_selection_balances_retrieval_groups(self):
        rag = _mock_pipeline()
        docs = []
        for index in range(5):
            doc = _doc(f"Nội dung nhóm hiện thực {index}", "a.pdf", index)
            doc.metadata["retrieval_group"] = "Chủ nghĩa Hiện thực"
            docs.append(doc)
        for index in range(2):
            doc = _doc(f"Nội dung nhóm tự do {index}", "b.pdf", index)
            doc.metadata["retrieval_group"] = "Chủ nghĩa Tự do"
            docs.append(doc)

        selected = rag._select_context_documents(
            docs,
            "broad",
            question="Các công trình nghiên cứu về vai trò",
        )
        groups = [doc.metadata.get("retrieval_group") for doc in selected[:4]]

        assert "Chủ nghĩa Hiện thực" in groups
        assert "Chủ nghĩa Tự do" in groups
        assert groups.count("Chủ nghĩa Hiện thực") < 4

    def test_eval_checks_expected_evidence_in_context(self):
        outline_doc = TestBroadQueryDecomposition._outline_doc()
        role_doc = _doc(
            "Holsti và Role theory xuất hiện trong phần lý thuyết vai trò.",
            "role.pdf",
            4,
        )
        role_doc.metadata["section_title"] = (
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế "
            "chịu ảnh hưởng của Lý thuyết Vai trò (Role theory)"
        )
        role_doc.metadata["retrieval_group"] = role_doc.metadata["section_title"]
        sna_doc = _doc(
            "Phân tích Mạng lưới Xã hội xem xét centrality trong mạng lưới quốc tế.",
            "sna.pdf",
            5,
        )
        sna_doc.metadata["section_title"] = (
            "Các công trình liên quan đến vai trò chủ thể quan hệ quốc tế "
            "chịu ảnh hưởng của Phân tích Mạng lưới Xã hội (SNA)"
        )
        sna_doc.metadata["retrieval_group"] = sna_doc.metadata["section_title"]
        rag = _mock_pipeline([outline_doc, role_doc, sna_doc])

        context = rag.query(
            "Các công trình nghiên cứu về vai trò của ASEAN trong khu vực Đông Á. "
            "Công trình của các tác giả nước ngoài"
        )["context"]

        assert "Holsti" in context
        assert "Phân tích Mạng lưới Xã hội" in context


class TestContextualQueryRewrite:
    def test_clear_question_skips_contextual_rewrite(self):
        rag = _mock_pipeline([_doc("ASEAN thành lập năm 1967.", "asean.pdf", 1)])

        rag.query(
            "ASEAN thành lập năm nào?",
            chat_history=[{"role": "user", "content": "Trước đó hỏi về con chó"}],
        )

        rag.llm_manager.invoke.assert_not_called()
        assert rag.vector_store_manager.similarity_search.call_args.kwargs["query"] == "ASEAN thành lập năm nào?"

    def test_follow_up_question_uses_rewritten_query_for_retrieval(self):
        rag = _mock_pipeline([_doc("Chó là vật nuôi phổ biến.", "dog.pdf", 1)])
        rag.llm_manager.invoke.return_value = "Con chó có phải là vật nuôi phổ biến không?"

        result = rag.query(
            "nó có phải là vật nuôi phổ biến không?",
            chat_history=[
                {"role": "user", "content": "Con chó là con gì?"},
                {"role": "assistant", "content": "Chó là một loài động vật được con người nuôi."},
            ],
        )

        assert rag.vector_store_manager.similarity_search.call_args_list[0].kwargs["query"] == "Con chó có phải là vật nuôi phổ biến không?"
        assert result["rewritten_query"] == "Con chó có phải là vật nuôi phổ biến không?"


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
            _doc("A" * (MAX_CONTEXT_CHARS // 3), "a.pdf", 1),
            _doc("B" * (MAX_CONTEXT_CHARS // 3), "b.pdf", 1),
            _doc("C" * (MAX_CONTEXT_CHARS // 3), "c.pdf", 1),
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
