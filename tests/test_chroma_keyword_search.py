from __future__ import annotations

from unittest.mock import MagicMock

from src.rag.vector_store import VectorStoreManager


def _chroma_vsm(tmp_path):
    vsm = VectorStoreManager(
        backend="chroma",
        persist_directory=str(tmp_path),
        embedding_manager=MagicMock(),
    )
    store = MagicMock()
    store._collection = MagicMock()
    vsm._chroma_store = store
    return vsm, store._collection


def test_chroma_keyword_search_ranks_specific_policy_chunk(tmp_path):
    vsm, collection = _chroma_vsm(tmp_path)
    collection.get.return_value = {
        "ids": ["generic", "leave"],
        "documents": [
            "Tài liệu này thiết lập chuẩn vận hành thống nhất cho công ty.",
            (
                "### 5.1 Annual Leave Standard\n"
                "Nhân viên chính thức có 14 ngày nghỉ phép hưởng lương mỗi năm."
            ),
        ],
        "metadatas": [
            {"file_name": "data_privacy_policy.md", "chunk_index": 1},
            {
                "file_name": "employee_handbook.md",
                "title": "Employee Handbook",
                "section_title": "Annual Leave Standard",
                "chunk_index": 6,
            },
        ],
    }

    docs = vsm.keyword_search("Tôi được nghỉ phép bao nhiêu ngày mỗi năm?", k=1)

    assert len(docs) == 1
    assert docs[0].metadata["file_name"] == "employee_handbook.md"
    assert docs[0].metadata["chunk_id"] == "leave"
    assert docs[0].metadata["retrieval_method"] == "chroma_keyword"
    assert docs[0].metadata["keyword_score"] > 0


def test_chroma_keyword_search_applies_access_filter(tmp_path):
    vsm, collection = _chroma_vsm(tmp_path)
    collection.get.return_value = {
        "ids": ["finance", "it"],
        "documents": [
            "Quy định mật khẩu hệ thống nội bộ.",
            "Quy định mật khẩu hệ thống nội bộ.",
        ],
        "metadatas": [
            {
                "file_name": "finance_policy.md",
                "department": "finance",
                "sensitivity": "internal",
                "metadata_verified": True,
            },
            {
                "file_name": "it_security_policy.md",
                "department": "it",
                "sensitivity": "internal",
                "metadata_verified": True,
                "allowed_roles": ["Employee"],
            },
        ],
    }

    docs = vsm.keyword_search(
        "quy định mật khẩu",
        k=5,
        filter={
            "role": "Employee",
            "departments": ["it"],
            "sensitivities": ["internal"],
            "require_verified": True,
        },
    )

    assert [doc.metadata["file_name"] for doc in docs] == ["it_security_policy.md"]


def test_chroma_keyword_search_includes_previous_heading_neighbor(tmp_path):
    vsm, collection = _chroma_vsm(tmp_path)
    collection.get.return_value = {
        "ids": ["heading", "answer", "other"],
        "documents": [
            '<a id="po-before-invoice"></a>\n### 5.2 PO Before Invoice',
            "Hóa đơn chỉ được thanh toán khi có PO đã phê duyệt trước ngày hóa đơn.",
            "Quy định chung về mua sắm.",
        ],
        "metadatas": [
            {"file_name": "finance_procurement_policy.md", "chunk_index": 14},
            {"file_name": "finance_procurement_policy.md", "chunk_index": 15},
            {"file_name": "finance_procurement_policy.md", "chunk_index": 52},
        ],
    }

    docs = vsm.keyword_search("Hóa đơn được thanh toán khi nào liên quan đến PO?", k=2)

    assert [doc.metadata["chunk_id"] for doc in docs] == ["answer", "heading"]
    assert docs[1].metadata["retrieval_method"] == "chroma_keyword_neighbor"
