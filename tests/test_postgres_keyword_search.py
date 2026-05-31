from __future__ import annotations

from uuid import uuid4

from src.rag.vector_store import VectorStoreManager


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, result_sets):
        self._result_sets = list(result_sets)
        self.sql_calls = []

    def execute(self, sql, params=None):
        self.sql_calls.append((sql, params or []))
        return _Rows(self._result_sets.pop(0))


class _ConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_exc):
        return False


def _row(
    *,
    chunk_id,
    document_id,
    chunk_index,
    content,
    keyword_score=None,
):
    row = {
        "chunk_id": chunk_id,
        "content": content,
        "metadata": {"chunk_index": chunk_index},
        "page_number": None,
        "chunk_index": chunk_index,
        "document_id": document_id,
        "source_key": "source-key",
        "file_name": "finance_procurement_policy.md",
        "file_path": "/tmp/finance_procurement_policy.md",
        "document_metadata": {},
    }
    if keyword_score is not None:
        row["keyword_score"] = keyword_score
    return row


def test_postgres_keyword_search_includes_previous_heading_neighbor(monkeypatch):
    document_id = str(uuid4())
    answer_row = _row(
        chunk_id=str(uuid4()),
        document_id=document_id,
        chunk_index=15,
        content="Hóa đơn chỉ được thanh toán khi có PO đã phê duyệt.",
        keyword_score=0.7,
    )
    heading_row = _row(
        chunk_id=str(uuid4()),
        document_id=document_id,
        chunk_index=14,
        content='<a id="po-before-invoice"></a>\n### 5.2 PO Before Invoice',
    )
    connection = _Connection([[answer_row], [heading_row]])
    vsm = VectorStoreManager(backend="postgres")
    monkeypatch.setattr(vsm, "_init_postgres_schema", lambda: None)
    monkeypatch.setattr(vsm, "_pool_connection", lambda: _ConnectionContext(connection))

    docs = vsm.keyword_search("Hóa đơn được thanh toán khi nào liên quan đến PO?", k=2)

    assert [doc.metadata["chunk_index"] for doc in docs] == [15, 14]
    assert docs[1].metadata["retrieval_method"] == "postgres_keyword_neighbor"
    assert "po-before-invoice" in docs[1].page_content
    assert len(connection.sql_calls) == 2
