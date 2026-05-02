"""PostgreSQL-backed storage for users, conversations, and messages."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

import psycopg
from psycopg.rows import dict_row

from src.config import POSTGRES_CONNECTION_STRING

T = TypeVar("T")


class ChatStore:
    """Manage auth and chat persistence with tenant-safe queries on PostgreSQL."""

    def __init__(self, db_url: str = POSTGRES_CONNECTION_STRING):
        self.db_url = db_url
        self._retry_attempts = 3
        self._retry_base_delay = 0.5

    def _connect(self):
        return psycopg.connect(
            self.db_url,
            row_factory=dict_row,
            autocommit=True
        )

    def _run_with_retry(self, operation: Callable[[psycopg.Connection], T]) -> T:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                with self._connect() as conn:
                    return operation(conn)
            except psycopg.OperationalError as exc:
                last_exc = exc
                if attempt == self._retry_attempts:
                    raise
                time.sleep(self._retry_base_delay * attempt)
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected PostgreSQL retry state")

    def cleanup_old_messages(self, retention_days: int = 365) -> int:
        """Apply retention policy to old messages."""
        def _op(conn: psycopg.Connection) -> int:
            cursor = conn.execute(
                """
                DELETE FROM chat_messages
                WHERE created_at < NOW() - %s::interval
                """,
                (f"{retention_days} days",),
            )
            return cursor.rowcount

        return self._run_with_retry(_op)

    def _hash_password(self, password: str, salt_hex: str) -> str:
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120000
        )
        return hashed.hex()

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def register_user(self, email: str, password: str) -> str:
        """Create a new user account and return user id."""
        normalized_email = self._normalize_email(email)
        if len(normalized_email) < 5 or "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        if len(password) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")

        salt_hex = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt_hex)
        packed_hash = f"{salt_hex}${password_hash}"
        username = normalized_email.split("@")[0] + "_" + secrets.token_hex(4)

        def _op(conn: psycopg.Connection) -> str:
            try:
                row = conn.execute(
                    """
                    INSERT INTO users(username, email, hashed_password)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (username, normalized_email, packed_hash),
                ).fetchone()
                user_id = str(row["id"])
                self._log_audit_with_conn(conn, user_id, "register", {"message": "User registered"})
                return user_id
            except psycopg.IntegrityError as exc:
                raise ValueError("Email hoặc Username đã tồn tại.") from exc

        return self._run_with_retry(_op)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with password verification."""
        normalized_email = self._normalize_email(email)
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT id, email, hashed_password, is_active
                FROM users
                WHERE email = %s
                """,
                (normalized_email,),
            ).fetchone()

        row = self._run_with_retry(_op)

        if not row or not row["is_active"]:
            return None

        packed_hash = row["hashed_password"]
        if "$" not in packed_hash:
            return None
            
        salt_hex, stored_hash = packed_hash.split("$", 1)
        candidate_hash = self._hash_password(password, salt_hex)
        if not hmac.compare_digest(candidate_hash, stored_hash):
            return None

        user = {"id": str(row["id"]), "email": row["email"]}
        self.log_audit(user["id"], "login", {"message": "Login success"})
        return user

    def log_audit(self, user_id: Optional[str], event: str, details: Any = None) -> None:
        """Write basic audit records for auth and data actions."""
        if details is None:
            details = {}
            
        def _op(conn: psycopg.Connection) -> None:
            self._log_audit_with_conn(conn, user_id, event, details)

        try:
            self._run_with_retry(_op)
        except psycopg.Error:
            # Audit is non-critical
            return

    def _log_audit_with_conn(
        self,
        conn: psycopg.Connection,
        user_id: Optional[str],
        event: str,
        details: Any,
    ) -> None:
        try:
            conn.execute(
                """
                INSERT INTO audit_logs(user_id, event, details)
                VALUES (%s, %s, %s::jsonb)
                """,
                (user_id, event, json.dumps(details)),
            )
        except psycopg.Error:
            return

    def create_conversation(self, user_id: str, title: str) -> str:
        safe_title = (title or "Chat mới").strip()[:120]
        if not safe_title:
            safe_title = "Chat mới"

        def _op(conn: psycopg.Connection) -> str:
            row = conn.execute(
                """
                INSERT INTO chat_sessions(user_id, title)
                VALUES (%s, %s)
                RETURNING id
                """,
                (user_id, safe_title),
            ).fetchone()
            conversation_id = str(row["id"])
            self._log_audit_with_conn(
                conn,
                user_id,
                "conversation_create",
                {"conversation_id": conversation_id},
            )
            return conversation_id

        return self._run_with_retry(_op)

    def list_conversations(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()

        rows = self._run_with_retry(_op)
        result = []
        for row in rows:
            r = dict(row)
            r["id"] = str(r["id"])
            result.append(r)
        return result

    def _user_owns_conversation(self, user_id: str, conversation_id: str) -> bool:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT 1
                FROM chat_sessions
                WHERE id = %s AND user_id = %s
                """,
                (conversation_id, user_id),
            ).fetchone()

        row = self._run_with_retry(_op)
        return row is not None

    def get_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        if not self._user_owns_conversation(user_id, conversation_id):
            self.log_audit(user_id, "conversation_access_denied", {"conversation_id": conversation_id})
            return []

        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT id, role, content, citations, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()

        rows = self._run_with_retry(_op)

        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["id"] = str(item["id"])
            item["sources"] = item.pop("citations", None)
            result.append(item)

        self.log_audit(user_id, "conversation_open", {"conversation_id": conversation_id})
        return result

    def append_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("Role không hợp lệ.")
        if not self._user_owns_conversation(user_id, conversation_id):
            self.log_audit(user_id, "message_write_denied", {"conversation_id": conversation_id})
            raise PermissionError("Không có quyền ghi vào cuộc chat này.")

        citations_json = json.dumps(sources if sources else [])

        def _op(conn: psycopg.Connection) -> str:
            with conn.transaction():
                row = conn.execute(
                    """
                    INSERT INTO chat_messages(session_id, role, content, citations)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    (conversation_id, role, content, citations_json),
                ).fetchone()
                
                conn.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = NOW()
                    WHERE id = %s
                    """,
                    (conversation_id,),
                )
                
                message_id = str(row["id"])
                self._log_audit_with_conn(
                    conn,
                    user_id,
                    "message_append",
                    {"conversation_id": conversation_id, "role": role, "message_id": message_id},
                )
                return message_id

        return self._run_with_retry(_op)

    def update_conversation_title(self, user_id: str, conversation_id: str, title: str) -> None:
        if not self._user_owns_conversation(user_id, conversation_id):
            raise PermissionError("Không có quyền đổi tiêu đề cuộc chat này.")

        safe_title = (title or "Chat mới").strip()[:120]
        if not safe_title:
            safe_title = "Chat mới"

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE chat_sessions
                SET title = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (safe_title, conversation_id),
            )

        self._run_with_retry(_op)

    def get_conversation_summary(self, user_id: str, conversation_id: str) -> str:
        if not self._user_owns_conversation(user_id, conversation_id):
            return ""

        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT summary
                FROM chat_sessions
                WHERE id = %s
                """,
                (conversation_id,),
            ).fetchone()

        row = self._run_with_retry(_op)
        if not row:
            return ""
        return str(row["summary"] or "")

    def upsert_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary: str,
        last_message_id: Optional[str] = None,
    ) -> None:
        if not self._user_owns_conversation(user_id, conversation_id):
            raise PermissionError("Không có quyền cập nhật summary cuộc chat này.")

        safe_summary = (summary or "").strip()

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE chat_sessions
                SET summary = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (safe_summary, conversation_id),
            )
            self._log_audit_with_conn(
                conn,
                user_id,
                "summary_upsert",
                {"conversation_id": conversation_id, "last_message_id": last_message_id},
            )

        self._run_with_retry(_op)

    def list_user_memories(self, user_id: str, limit: int = 12) -> List[Dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT id, memory_type, content, confidence, last_used_at, updated_at
                FROM user_memories
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY confidence DESC, last_used_at DESC, updated_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()

        rows = self._run_with_retry(_op)
        result = []
        for row in rows:
            r = dict(row)
            r["id"] = str(r["id"])
            result.append(r)
        return result

    def upsert_user_memories(
        self,
        user_id: str,
        memories: List[Dict[str, Any]],
        min_confidence: float = 0.7,
        max_memories: int = 50,
    ) -> int:
        allowed_types = {"preference", "fact", "constraint"}
        filtered: List[Dict[str, Any]] = []
        for memory in memories:
            mem_type = str(memory.get("memory_type", "")).strip().lower()
            content = str(memory.get("content", "")).strip()
            confidence_raw = memory.get("confidence", 0.5)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.5

            confidence = max(0.0, min(1.0, confidence))

            if mem_type not in allowed_types:
                continue
            if len(content) < 8 or len(content) > 400:
                continue
            if confidence < min_confidence:
                continue

            filtered.append(
                {
                    "memory_type": mem_type,
                    "content": content,
                    "confidence": confidence,
                }
            )

        if not filtered:
            return 0

        def _op(conn: psycopg.Connection) -> int:
            upserted = 0
            with conn.transaction():
                for item in filtered:
                    conn.execute(
                        """
                        INSERT INTO user_memories(user_id, memory_type, content, confidence, updated_at, last_used_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT(user_id, memory_type, content)
                        DO UPDATE SET
                            confidence = GREATEST(user_memories.confidence, EXCLUDED.confidence),
                            updated_at = NOW(),
                            last_used_at = NOW(),
                            is_active = TRUE
                        """,
                        (user_id, item["memory_type"], item["content"], item["confidence"]),
                    )
                    upserted += 1

                conn.execute(
                    """
                    DELETE FROM user_memories
                    WHERE user_id = %s
                      AND id NOT IN (
                          SELECT id
                          FROM user_memories
                          WHERE user_id = %s AND is_active = TRUE
                          ORDER BY confidence DESC, last_used_at DESC, updated_at DESC
                          LIMIT %s
                      )
                    """,
                    (user_id, user_id, max_memories),
                )

                self._log_audit_with_conn(
                    conn,
                    user_id,
                    "user_memory_upsert",
                    {"upserted": upserted, "kept_max": max_memories},
                )
            return upserted

        return self._run_with_retry(_op)
