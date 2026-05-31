"""Unit tests for get_audit_logs query and filters."""

import datetime

import pytest

from src.config import POSTGRES_CONNECTION_STRING
from src.storage.chat_store import ChatStore

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


@pytest.fixture
def store():
    store_obj = ChatStore(db_url=POSTGRES_CONNECTION_STRING)
    # Clean up test user and its audit logs
    emails = ["audit_test@example.com", "audit_another@example.com"]

    def _cleanup(conn):
        # Delete audit logs of test users first
        conn.execute(
            """
            DELETE FROM audit_logs
            WHERE user_id IN (SELECT id FROM users WHERE email = ANY(%s))
            """,
            (emails,),
        )
        # Delete test users
        conn.execute("DELETE FROM users WHERE email = ANY(%s)", (emails,))

    store_obj._run_with_retry(_cleanup)
    return store_obj


def test_get_audit_logs_filters_and_pagination(store: ChatStore):
    # 1. Register test users
    user_id_1 = store.register_user("audit_test@example.com", "password123")
    user_id_2 = store.register_user("audit_another@example.com", "password123")

    # 2. Write custom audit logs
    store.log_audit(user_id_1, "test_event_a", {"info": "user 1 event a"})
    store.log_audit(user_id_1, "test_event_b", {"info": "user 1 event b"})
    store.log_audit(user_id_2, "test_event_a", {"info": "user 2 event a"})

    # 3. Test retrieving all logs (without filter)
    logs, total = store.get_audit_logs(limit=10, offset=0)
    assert total >= 3
    # Check that our test logs are returned
    events = [log["event"] for log in logs]
    assert "test_event_a" in events
    assert "test_event_b" in events

    # 4. Test filtering by event type
    logs, total = store.get_audit_logs(event_type="test_event_b")
    assert total == 1
    assert logs[0]["event"] == "test_event_b"
    assert logs[0]["user_email"] == "audit_test@example.com"
    assert logs[0]["details"]["info"] == "user 1 event b"

    # 5. Test filtering by email query (matches both registration log and test event)
    logs, total = store.get_audit_logs(email_query="another")
    assert total == 2
    # The newest log is test_event_a since it was written after registration
    assert logs[0]["user_email"] == "audit_another@example.com"
    assert logs[0]["event"] == "test_event_a"
    assert logs[1]["event"] == "register"

    # 6. Test filtering by dates
    today_str = datetime.date.today().isoformat()
    logs, total = store.get_audit_logs(start_date=today_str, end_date=today_str)
    # Since they were logged today, they should be found
    assert total >= 3

    # Test filtering out via future date
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()
    logs, total = store.get_audit_logs(start_date=tomorrow_str)
    assert total == 0

    # 7. Test pagination (limit & offset)
    logs, total = store.get_audit_logs(limit=1, offset=0, event_type="test_event_a")
    assert len(logs) == 1
    # total should represent total matching (2 logs of type test_event_a)
    assert total == 2

    first_log_id = logs[0]["id"]

    # Fetch offset 1
    logs_offset, total_offset = store.get_audit_logs(limit=1, offset=1, event_type="test_event_a")
    assert len(logs_offset) == 1
    assert total_offset == 2
    assert logs_offset[0]["id"] != first_log_id
