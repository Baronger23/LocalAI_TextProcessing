"""Tests for RBAC admin helpers."""

from __future__ import annotations

import pytest

from src.config import POSTGRES_CONNECTION_STRING
from src.storage.chat_store import ChatStore
from src.rag.vector_store import VectorStoreManager


@pytest.fixture
def store():
    store_obj = ChatStore(db_url=POSTGRES_CONNECTION_STRING)

    def _cleanup(conn):
        conn.execute("DELETE FROM user_permission_groups WHERE user_id IN (SELECT id FROM users WHERE email LIKE %s)", ("rbac_%@example.com",))
        conn.execute("DELETE FROM group_department_permissions WHERE group_id IN (SELECT id FROM permission_groups WHERE name LIKE %s)", ("RBAC Test %",))
        conn.execute("DELETE FROM permission_groups WHERE name LIKE %s", ("RBAC Test %",))
        conn.execute("DELETE FROM users WHERE email LIKE %s", ("rbac_%@example.com",))

    store_obj._run_with_retry(_cleanup)
    return store_obj


def test_permission_group_and_membership_flow(store: ChatStore):
    group_id = store.create_permission_group("RBAC Test Group", "Group for tests", 3)
    user_id = store.create_user(
        full_name="RBAC Tester",
        username="rbac_tester",
        email="rbac_user@example.com",
        temporary_password="temporary123",
        role="Employee",
        department_id=None,
        clearance_level=2,
    )

    groups = store.list_permission_groups("RBAC Test")
    assert any(group["id"] == group_id for group in groups)

    store.assign_user_to_group(user_id, group_id)
    memberships = store.list_user_groups(user_id)
    assert any(group["id"] == group_id for group in memberships)

    state = store.get_user_security_state(user_id)
    assert state is not None
    assert state["session_version"] == 1

    docs = VectorStoreManager().list_documents()
    if docs:
        preview = store.preview_user_access(user_id, docs[0]["id"])
        assert "can_access" in preview

    store.remove_user_from_group(user_id, group_id)
    store.delete_permission_group(group_id)


def test_force_logout_invalidates_session_version(store: ChatStore):
    user_id = store.create_user(
        full_name="RBAC Logout",
        username="rbac_logout",
        email="rbac_logout@example.com",
        temporary_password="temporary123",
        role="Employee",
        department_id=None,
        clearance_level=2,
    )
    before = store.get_user_security_state(user_id)
    assert before is not None

    store.force_logout_user(user_id)
    after = store.get_user_security_state(user_id)
    assert after is not None
    assert after["session_version"] == before["session_version"] + 1

    store.set_user_active(user_id, False)
    inactive = store.get_user_security_state(user_id)
    assert inactive is not None
    assert inactive["is_active"] is False
