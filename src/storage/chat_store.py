"""SQLite-backed storage for users, conversations, and messages."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from threading import RLock
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")


class ChatStore:
    """Manage auth and chat persistence with tenant-safe queries."""

    def __init__(self, db_path: str = "data/processed/chat.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = RLock()
        self._retry_attempts = 6
        self._retry_base_delay = 0.1
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _is_locked_error(self, exc: sqlite3.OperationalError) -> bool:
        msg = str(exc).lower()
        return "database is locked" in msg or "database table is locked" in msg

    def _run_read_with_retry(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        last_exc: Optional[sqlite3.OperationalError] = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                with self._connect() as conn:
                    return operation(conn)
            except sqlite3.OperationalError as exc:
                if not self._is_locked_error(exc) or attempt == self._retry_attempts:
                    raise
                last_exc = exc
                time.sleep(self._retry_base_delay * attempt)

        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected SQLite read retry state")

    def _run_write_with_retry(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        last_exc: Optional[sqlite3.OperationalError] = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                with self._write_lock:
                    with self._connect() as conn:
                        return operation(conn)
            except sqlite3.OperationalError as exc:
                if not self._is_locked_error(exc) or attempt == self._retry_attempts:
                    raise
                last_exc = exc
                time.sleep(self._retry_base_delay * attempt)

        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected SQLite write retry state")

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    archived_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    conversation_id INTEGER PRIMARY KEY,
                    rolling_summary TEXT NOT NULL DEFAULT '',
                    last_message_id INTEGER,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(user_id, memory_type, content),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at ASC);
                CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
                CREATE INDEX IF NOT EXISTS idx_summaries_updated_at ON conversation_summaries(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories(user_id, is_active, confidence DESC, last_used_at DESC);
                """
            )

    def cleanup_old_messages(self, retention_days: int = 365) -> int:
        """Apply retention policy to old messages."""
        def _op(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                """
                DELETE FROM messages
                WHERE created_at < datetime('now', ?)
                """,
                (f"-{retention_days} days",),
            )
            return cursor.rowcount

        return self._run_write_with_retry(_op)

    def _hash_password(self, password: str, salt_hex: str) -> str:
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120000
        )
        return hashed.hex()

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def register_user(self, email: str, password: str) -> int:
        """Create a new user account and return user id."""
        normalized_email = self._normalize_email(email)
        if len(normalized_email) < 5 or "@" not in normalized_email:
            raise ValueError("Email không hợp lệ.")
        if len(password) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")

        salt_hex = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt_hex)

        def _op(conn: sqlite3.Connection) -> int:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users(email, password_hash, salt)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_email, password_hash, salt_hex),
                )
                user_id = int(cursor.lastrowid)
                self._log_audit_with_conn(conn, user_id, "register", "User registered")
                return user_id
            except sqlite3.IntegrityError as exc:
                raise ValueError("Email đã tồn tại.") from exc

        return self._run_write_with_retry(_op)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with password verification."""
        normalized_email = self._normalize_email(email)
        def _op(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
            return conn.execute(
                """
                SELECT id, email, password_hash, salt, is_active
                FROM users
                WHERE email = ?
                """,
                (normalized_email,),
            ).fetchone()

        row = self._run_read_with_retry(_op)

        if not row or row["is_active"] != 1:
            return None

        candidate_hash = self._hash_password(password, row["salt"])
        if not hmac.compare_digest(candidate_hash, row["password_hash"]):
            return None

        user = {"id": int(row["id"]), "email": row["email"]}
        self.log_audit(user["id"], "login", "Login success")
        return user

    def log_audit(self, user_id: Optional[int], event: str, details: str = "") -> None:
        """Write basic audit records for auth and data actions."""
        def _op(conn: sqlite3.Connection) -> None:
            self._log_audit_with_conn(conn, user_id, event, details)

        try:
            self._run_write_with_retry(_op)
        except sqlite3.OperationalError:
            # Audit is non-critical: avoid breaking main user flow.
            return

    def _log_audit_with_conn(
        self,
        conn: sqlite3.Connection,
        user_id: Optional[int],
        event: str,
        details: str = "",
    ) -> None:
        """Write audit logs using an existing transaction/connection."""
        try:
            conn.execute(
                """
                INSERT INTO audit_logs(user_id, event, details)
                VALUES (?, ?, ?)
                """,
                (user_id, event, details),
            )
        except sqlite3.Error:
            # Audit is best-effort and should not block core operations.
            return

    def create_conversation(self, user_id: int, title: str) -> int:
        """Create conversation scoped to a user."""
        safe_title = (title or "Chat mới").strip()[:120]
        if not safe_title:
            safe_title = "Chat mới"

        def _op(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                """
                INSERT INTO conversations(user_id, title)
                VALUES (?, ?)
                """,
                (user_id, safe_title),
            )
            conversation_id = int(cursor.lastrowid)
            self._log_audit_with_conn(
                conn,
                user_id,
                "conversation_create",
                f"conversation_id={conversation_id}",
            )
            return conversation_id

        return self._run_write_with_retry(_op)

    def list_conversations(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """List conversations for current user only (tenant isolation)."""
        def _op(conn: sqlite3.Connection) -> List[sqlite3.Row]:
            return conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = ? AND archived_at IS NULL
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        rows = self._run_read_with_retry(_op)

        return [dict(row) for row in rows]

    def _user_owns_conversation(self, user_id: int, conversation_id: int) -> bool:
        def _op(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
            return conn.execute(
                """
                SELECT 1
                FROM conversations
                WHERE id = ? AND user_id = ? AND archived_at IS NULL
                """,
                (conversation_id, user_id),
            ).fetchone()

        row = self._run_read_with_retry(_op)
        return row is not None

    def get_messages(self, user_id: int, conversation_id: int) -> List[Dict[str, Any]]:
        """Return messages only when the user owns the conversation."""
        if not self._user_owns_conversation(user_id, conversation_id):
            self.log_audit(user_id, "conversation_access_denied", f"conversation_id={conversation_id}")
            return []

        def _op(conn: sqlite3.Connection) -> List[sqlite3.Row]:
            return conn.execute(
                """
                SELECT id, role, content, sources_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()

        rows = self._run_read_with_retry(_op)

        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["sources"] = json.loads(item["sources_json"]) if item.get("sources_json") else None
            item.pop("sources_json", None)
            result.append(item)

        self.log_audit(user_id, "conversation_open", f"conversation_id={conversation_id}")
        return result

    def append_message(
        self,
        user_id: int,
        conversation_id: int,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Append a message to a conversation after ownership check."""
        if role not in {"user", "assistant", "system"}:
            raise ValueError("Role không hợp lệ.")
        if not self._user_owns_conversation(user_id, conversation_id):
            self.log_audit(user_id, "message_write_denied", f"conversation_id={conversation_id}")
            raise PermissionError("Không có quyền ghi vào cuộc chat này.")

        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None

        def _op(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                """
                INSERT INTO messages(conversation_id, role, content, sources_json)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, sources_json),
            )
            conn.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_id,),
            )
            message_id = int(cursor.lastrowid)
            self._log_audit_with_conn(
                conn,
                user_id,
                "message_append",
                f"conversation_id={conversation_id}; role={role}; message_id={message_id}",
            )
            return message_id

        return self._run_write_with_retry(_op)

    def update_conversation_title(self, user_id: int, conversation_id: int, title: str) -> None:
        """Update title with ownership check."""
        if not self._user_owns_conversation(user_id, conversation_id):
            raise PermissionError("Không có quyền đổi tiêu đề cuộc chat này.")

        safe_title = (title or "Chat mới").strip()[:120]
        if not safe_title:
            safe_title = "Chat mới"

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (safe_title, conversation_id),
            )

        self._run_write_with_retry(_op)

    def get_conversation_summary(self, user_id: int, conversation_id: int) -> str:
        """Get rolling summary for a user conversation."""
        if not self._user_owns_conversation(user_id, conversation_id):
            return ""

        def _op(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
            return conn.execute(
                """
                SELECT rolling_summary
                FROM conversation_summaries
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        row = self._run_read_with_retry(_op)
        if not row:
            return ""
        return str(row["rolling_summary"] or "")

    def upsert_conversation_summary(
        self,
        user_id: int,
        conversation_id: int,
        summary: str,
        last_message_id: Optional[int] = None,
    ) -> None:
        """Upsert rolling summary for a conversation with ownership check."""
        if not self._user_owns_conversation(user_id, conversation_id):
            raise PermissionError("Không có quyền cập nhật summary cuộc chat này.")

        safe_summary = (summary or "").strip()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO conversation_summaries(conversation_id, rolling_summary, last_message_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(conversation_id)
                DO UPDATE SET
                    rolling_summary = excluded.rolling_summary,
                    last_message_id = excluded.last_message_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (conversation_id, safe_summary, last_message_id),
            )
            self._log_audit_with_conn(
                conn,
                user_id,
                "summary_upsert",
                f"conversation_id={conversation_id}; last_message_id={last_message_id}",
            )

        self._run_write_with_retry(_op)

    def list_user_memories(self, user_id: int, limit: int = 12) -> List[Dict[str, Any]]:
        """List active long-term memories for a user."""
        def _op(conn: sqlite3.Connection) -> List[sqlite3.Row]:
            return conn.execute(
                """
                SELECT id, memory_type, content, confidence, last_used_at, updated_at
                FROM user_memories
                WHERE user_id = ? AND is_active = 1
                ORDER BY confidence DESC, last_used_at DESC, updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        rows = self._run_read_with_retry(_op)
        return [dict(row) for row in rows]

    def upsert_user_memories(
        self,
        user_id: int,
        memories: List[Dict[str, Any]],
        min_confidence: float = 0.7,
        max_memories: int = 50,
    ) -> int:
        """Upsert selected long-term user memories and keep bounded memory count."""
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

        def _op(conn: sqlite3.Connection) -> int:
            upserted = 0
            for item in filtered:
                conn.execute(
                    """
                    INSERT INTO user_memories(user_id, memory_type, content, confidence, updated_at, last_used_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, memory_type, content)
                    DO UPDATE SET
                        confidence = MAX(user_memories.confidence, excluded.confidence),
                        updated_at = CURRENT_TIMESTAMP,
                        last_used_at = CURRENT_TIMESTAMP,
                        is_active = 1
                    """,
                    (user_id, item["memory_type"], item["content"], item["confidence"]),
                )
                upserted += 1

            conn.execute(
                """
                DELETE FROM user_memories
                WHERE user_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM user_memories
                      WHERE user_id = ? AND is_active = 1
                      ORDER BY confidence DESC, last_used_at DESC, updated_at DESC
                      LIMIT ?
                  )
                """,
                (user_id, user_id, max_memories),
            )

            self._log_audit_with_conn(
                conn,
                user_id,
                "user_memory_upsert",
                f"upserted={upserted}; kept_max={max_memories}",
            )
            return upserted

        return self._run_write_with_retry(_op)
