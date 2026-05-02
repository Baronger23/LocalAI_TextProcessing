"""Unit tests for ChatStore critical behaviors.

Coverage focus:
- Tenant isolation and authorization checks.
- SQLite lock retry behavior.
- Rolling summary persistence.
- User memories filtering, dedupe, and bounded retention.
"""

import sqlite3

import pytest

from src.storage.chat_store import ChatStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "chat_store_test.db"
    return ChatStore(db_path=str(db_path))


def _create_user(store: ChatStore, email: str, password: str = "password123") -> int:
    return store.register_user(email, password)


def test_tenant_isolation_for_messages_and_summary(store: ChatStore):
    user_a = _create_user(store, "a@example.com")
    user_b = _create_user(store, "b@example.com")

    conv_a = store.create_conversation(user_a, "A chat")
    store.append_message(user_a, conv_a, "user", "hello from user a")

    # Cross-tenant reads should not expose data.
    assert store.get_messages(user_b, conv_a) == []
    assert store.get_conversation_summary(user_b, conv_a) == ""

    # Cross-tenant writes should be blocked.
    with pytest.raises(PermissionError):
        store.append_message(user_b, conv_a, "user", "intrusion attempt")

    with pytest.raises(PermissionError):
        store.upsert_conversation_summary(user_b, conv_a, "secret summary")


def test_lock_retry_succeeds_after_transient_lock(store: ChatStore, monkeypatch):
    monkeypatch.setattr("src.storage.chat_store.time.sleep", lambda _s: None)

    calls = {"count": 0}

    def operation(_conn):
        calls["count"] += 1
        if calls["count"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return 42

    result = store._run_write_with_retry(operation)
    assert result == 42
    assert calls["count"] == 3


def test_lock_retry_does_not_swallow_non_lock_errors(store: ChatStore):
    def operation(_conn):
        raise sqlite3.OperationalError("syntax error near FROM")

    with pytest.raises(sqlite3.OperationalError):
        store._run_write_with_retry(operation)


def test_conversation_summary_roundtrip(store: ChatStore):
    user_id = _create_user(store, "summary@example.com")
    conv_id = store.create_conversation(user_id, "Summary chat")

    assert store.get_conversation_summary(user_id, conv_id) == ""

    store.upsert_conversation_summary(user_id, conv_id, "first summary")
    assert store.get_conversation_summary(user_id, conv_id) == "first summary"

    store.upsert_conversation_summary(user_id, conv_id, "updated summary")
    assert store.get_conversation_summary(user_id, conv_id) == "updated summary"


def test_user_memories_filtering_dedupe_and_limit(store: ChatStore):
    user_id = _create_user(store, "memory@example.com")

    inserted = store.upsert_user_memories(
        user_id=user_id,
        memories=[
            {
                "memory_type": "preference",
                "content": "prefer concise answers in Vietnamese",
                "confidence": 0.91,
            },
            {
                "memory_type": "fact",
                "content": "works on a local RAG system with Ollama",
                "confidence": 0.88,
            },
            {
                "memory_type": "constraint",
                "content": "must keep tenant isolation in storage",
                "confidence": 0.95,
            },
            # Should be filtered out: low confidence
            {
                "memory_type": "preference",
                "content": "likes emojis",
                "confidence": 0.2,
            },
            # Should be filtered out: invalid type
            {
                "memory_type": "temporary",
                "content": "current one-off question",
                "confidence": 0.9,
            },
        ],
        min_confidence=0.7,
        max_memories=2,
    )

    # upsert_user_memories returns number of accepted items before max trimming.
    assert inserted == 3

    memories = store.list_user_memories(user_id, limit=10)
    assert len(memories) == 2

    types = {m["memory_type"] for m in memories}
    assert types.issubset({"preference", "fact", "constraint"})

    # Dedupe/upsert same content with higher confidence should keep a single row.
    inserted_again = store.upsert_user_memories(
        user_id=user_id,
        memories=[
            {
                "memory_type": "preference",
                "content": "prefer concise answers in Vietnamese",
                "confidence": 0.99,
            }
        ],
        min_confidence=0.7,
        max_memories=2,
    )
    assert inserted_again == 1

    updated = store.list_user_memories(user_id, limit=10)
    same_content = [m for m in updated if m["content"] == "prefer concise answers in Vietnamese"]
    assert len(same_content) == 1
    assert float(same_content[0]["confidence"]) >= 0.91
