from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.documents import Document

from src.rag.rag_pipeline import RAGPipeline
from src.security import (
    build_access_filter,
    check_question_permission,
    classify_question_category,
    document_allowed,
)


def _mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.model = "mock-llm"
    llm.generate_response.return_value = "answer"
    return llm


def _mock_embeddings() -> MagicMock:
    embeddings = MagicMock()
    embeddings.model = "mock-embed"
    return embeddings


def test_employee_is_denied_for_finance_question():
    category = classify_question_category("Cho tôi xem quỹ lương tháng này")

    assert category == "finance"
    assert not check_question_permission("Employee", "it", category)


def test_manager_is_limited_to_own_department():
    assert check_question_permission("Manager", "hr", "hr")
    assert not check_question_permission("Manager", "hr", "finance")


def test_unverified_document_is_hidden_from_employee():
    access_filter = build_access_filter("Employee", "it")

    assert not document_allowed(
        {
            "department": "it",
            "sensitivity": "internal",
            "metadata_verified": False,
            "allowed_roles": ["Employee"],
        },
        access_filter,
    )


def test_rag_passes_access_filter_to_all_retrieval_paths():
    vector_store = MagicMock()
    vector_store.get_document_version.return_value = "v1"
    vector_store.similarity_search.return_value = [
        Document(
            page_content="public it context",
            metadata={
                "department": "it",
                "sensitivity": "internal",
                "metadata_verified": True,
                "allowed_roles": ["Employee"],
                "chunk_id": "c1",
            },
        )
    ]
    vector_store.keyword_search.return_value = []

    rag = RAGPipeline(
        llm_manager=_mock_llm(),
        embedding_manager=_mock_embeddings(),
        vector_store_manager=vector_store,
        query_rewrite_enabled=False,
        prompt_fusion_enabled=False,
    )
    access_filter = build_access_filter("Employee", "it")

    rag.query("trinh bay tai lieu noi bo IT", access_filter=access_filter)

    assert vector_store.similarity_search.call_args.kwargs["filter"] == access_filter
    assert vector_store.keyword_search.call_args.kwargs["filter"] == access_filter


def test_cache_key_includes_access_scope():
    vector_store = MagicMock()
    vector_store.get_document_version.return_value = "v1"
    rag = RAGPipeline(
        llm_manager=_mock_llm(),
        embedding_manager=_mock_embeddings(),
        vector_store_manager=vector_store,
    )
    admin_filter = build_access_filter("Admin", "finance")
    employee_filter = build_access_filter("Employee", "finance")

    admin_key = rag.query_cache.make_key("lương", 8, admin_filter, "mock-llm")
    employee_key = rag.query_cache.make_key("lương", 8, employee_filter, "mock-llm")

    assert admin_key != employee_key
