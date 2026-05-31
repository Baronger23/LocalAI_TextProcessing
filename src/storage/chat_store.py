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
        self._schema_ready = False
        self._ensure_schema()

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

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS clearance_level INTEGER NOT NULL DEFAULT 1;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version BIGINT NOT NULL DEFAULT 1;

                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS description TEXT;
                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS max_clearance_level INTEGER NOT NULL DEFAULT 1;
                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS document_scope JSONB NOT NULL DEFAULT '{}'::jsonb;
                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
                ALTER TABLE IF EXISTS permission_groups ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

                ALTER TABLE IF EXISTS user_permission_groups ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

                ALTER TABLE IF EXISTS group_department_permissions ADD COLUMN IF NOT EXISTS max_sensitivity TEXT NOT NULL DEFAULT 'internal';
                ALTER TABLE IF EXISTS group_department_permissions ADD COLUMN IF NOT EXISTS can_view_all_documents BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE IF EXISTS group_department_permissions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
                ALTER TABLE IF EXISTS group_department_permissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

                CREATE TABLE IF NOT EXISTS permission_groups (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    max_clearance_level INTEGER NOT NULL DEFAULT 1,
                    document_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
                    is_system BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS user_permission_groups (
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    group_id UUID NOT NULL REFERENCES permission_groups(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (user_id, group_id)
                );

                CREATE TABLE IF NOT EXISTS group_department_permissions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    group_id UUID NOT NULL REFERENCES permission_groups(id) ON DELETE CASCADE,
                    department TEXT NOT NULL,
                    max_sensitivity TEXT NOT NULL DEFAULT 'internal',
                    can_view_all_documents BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (group_id, department)
                );

                CREATE INDEX IF NOT EXISTS idx_permission_groups_name ON permission_groups(name);
                CREATE INDEX IF NOT EXISTS idx_user_permission_groups_user ON user_permission_groups(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_permission_groups_group ON user_permission_groups(group_id);
                CREATE INDEX IF NOT EXISTS idx_group_department_permissions_group ON group_department_permissions(group_id);
                """
            )

            defaults = [
                ("Admin", "Toàn quyền quản trị hệ thống", 5, True),
                ("HR", "Quản trị dữ liệu nhân sự", 3, True),
                ("Finance", "Quản trị dữ liệu tài chính", 4, True),
                ("Legal", "Quản trị dữ liệu pháp lý", 4, True),
                ("Viewer", "Chỉ xem dữ liệu được cho phép", 1, True),
            ]
            for name, description, clearance, is_system in defaults:
                conn.execute(
                    """
                    INSERT INTO permission_groups(name, description, max_clearance_level, is_system)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (name, description, clearance, is_system),
                )

            matrix_rows = [
                ("Admin", "general", "restricted", True),
                ("Admin", "finance", "restricted", True),
                ("Admin", "hr", "restricted", True),
                ("Admin", "it", "restricted", True),
                ("Admin", "legal", "restricted", True),
                ("Admin", "security", "restricted", True),
                ("HR", "hr", "confidential", False),
                ("Finance", "finance", "confidential", False),
                ("Legal", "legal", "confidential", False),
                ("Viewer", "general", "internal", False),
            ]
            for group_name, department, max_sensitivity, can_view_all in matrix_rows:
                conn.execute(
                    """
                    INSERT INTO group_department_permissions(group_id, department, max_sensitivity, can_view_all_documents)
                    SELECT id, %s, %s, %s
                    FROM permission_groups
                    WHERE name = %s
                    ON CONFLICT (group_id, department) DO NOTHING
                    """,
                    (department, max_sensitivity, can_view_all, group_name),
                )

        self._run_with_retry(_op)
        self._schema_ready = True

    @staticmethod
    def _sensitivity_rank(value: str | None) -> int:
        order = {"public": 1, "internal": 2, "confidential": 3, "restricted": 4}
        return order.get(str(value or "").strip().lower(), 0)

    @staticmethod
    def _rank_to_sensitivity(value: int | None) -> str:
        mapping = {1: "public", 2: "internal", 3: "confidential", 4: "restricted", 5: "restricted"}
        try:
            return mapping.get(int(value or 1), "internal")
        except (TypeError, ValueError):
            return "internal"

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
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.email,
                    u.hashed_password,
                    u.is_active,
                    u.role,
                    u.department_id,
                    d.name AS department,
                    u.clearance_level,
                    u.last_login_at,
                    u.session_version
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                WHERE u.email = %s
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

        user = {
            "id": str(row["id"]),
            "full_name": row.get("full_name") or row.get("username") or row["email"],
            "username": row.get("username") or normalized_email.split("@")[0],
            "email": row["email"],
            "role": row.get("role") or "Employee",
            "department_id": str(row["department_id"]) if row.get("department_id") else None,
            "department": row.get("department") or "general",
            "clearance_level": int(row.get("clearance_level") or 1),
            "last_login_at": row.get("last_login_at"),
            "session_version": int(row.get("session_version") or 1),
        }
        def _mark_login(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE users
                SET last_login_at = NOW()
                WHERE id = %s
                """,
                (user["id"],),
            )
            self._log_audit_with_conn(conn, user["id"], "login", {"message": "Login success"})

        self._run_with_retry(_mark_login)
        return user

    def get_user_security_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.email,
                    u.role,
                    u.department_id,
                    d.name AS department,
                    u.is_active,
                    u.clearance_level,
                    u.last_login_at,
                    u.session_version
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                WHERE u.id = %s
                """,
                (user_id,),
            ).fetchone()

        row = self._run_with_retry(_op)
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "full_name": row.get("full_name") or row.get("username") or row.get("email"),
            "username": row.get("username") or "",
            "email": row.get("email") or "",
            "role": row.get("role") or "Employee",
            "department_id": str(row["department_id"]) if row.get("department_id") else None,
            "department": row.get("department") or "general",
            "is_active": bool(row.get("is_active")),
            "clearance_level": int(row.get("clearance_level") or 1),
            "last_login_at": row.get("last_login_at"),
            "session_version": int(row.get("session_version") or 1),
        }

    def list_departments(self) -> list[dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT id, name, description, created_at, updated_at
                FROM departments
                ORDER BY name ASC
                """
            ).fetchall()

        rows = self._run_with_retry(_op)
        return [dict(row) | {"id": str(row["id"])} for row in rows]

    def list_permission_groups(self, query: str | None = None) -> list[dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT
                    g.id,
                    g.name,
                    g.description,
                    g.max_clearance_level,
                    g.document_scope,
                    g.is_system,
                    g.created_at,
                    g.updated_at,
                    COUNT(ug.user_id) AS member_count
                FROM permission_groups g
                LEFT JOIN user_permission_groups ug ON ug.group_id = g.id
                WHERE (%s::text IS NULL OR g.name ILIKE %s::text)
                GROUP BY g.id
                ORDER BY g.name ASC
                """,
                (query, f"%{query}%" if query else None),
            ).fetchall()

        rows = self._run_with_retry(_op)
        result = []
        for row in rows:
            result.append(
                {
                    **dict(row),
                    "id": str(row["id"]),
                    "member_count": int(row["member_count"]),
                }
            )
        return result

    def create_permission_group(self, name: str, description: str, max_clearance_level: int) -> str:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Tên nhóm quyền không được để trống.")
        safe_description = (description or "").strip()
        clearance_level = max(1, min(5, int(max_clearance_level or 1)))

        def _op(conn: psycopg.Connection) -> str:
            row = conn.execute(
                """
                INSERT INTO permission_groups(name, description, max_clearance_level)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (safe_name, safe_description, clearance_level),
            ).fetchone()
            group_id = str(row["id"])
            self._log_audit_with_conn(conn, None, "rbac_group_create", {"group_id": group_id, "name": safe_name})
            return group_id

        return self._run_with_retry(_op)

    def update_permission_group(
        self,
        group_id: str,
        name: str,
        description: str,
        max_clearance_level: int,
        document_scope: Optional[Dict[str, Any]] = None,
    ) -> None:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Tên nhóm quyền không được để trống.")

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE permission_groups
                SET name = %s,
                    description = %s,
                    max_clearance_level = %s,
                    document_scope = COALESCE(%s::jsonb, document_scope),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    safe_name,
                    (description or "").strip(),
                    max(1, min(5, int(max_clearance_level or 1))),
                    json.dumps(document_scope) if document_scope is not None else None,
                    group_id,
                ),
            )
            self._log_audit_with_conn(conn, None, "rbac_group_update", {"group_id": group_id, "name": safe_name})

        self._run_with_retry(_op)

    def delete_permission_group(self, group_id: str) -> None:
        def _op(conn: psycopg.Connection) -> None:
            member_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM user_permission_groups WHERE group_id = %s",
                (group_id,),
            ).fetchone()
            if int(member_row["cnt"] or 0) > 0:
                raise ValueError("Chỉ được xóa nhóm quyền khi không còn thành viên.")
            conn.execute("DELETE FROM group_department_permissions WHERE group_id = %s", (group_id,))
            conn.execute("DELETE FROM permission_groups WHERE id = %s", (group_id,))
            self._log_audit_with_conn(conn, None, "rbac_group_delete", {"group_id": group_id})

        self._run_with_retry(_op)

    def list_users(
        self,
        query: str | None = None,
        department_id: str | None = None,
        role: str | None = None,
        active: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if query:
            conditions.append("(u.full_name ILIKE %s OR u.username ILIKE %s OR u.email ILIKE %s)")
            params.extend([f"%{query}%"] * 3)
        if department_id:
            conditions.append("u.department_id = %s")
            params.append(department_id)
        if role:
            conditions.append("u.role = %s")
            params.append(role)
        if active is not None:
            conditions.append("u.is_active = %s")
            params.append(active)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        def _op(conn: psycopg.Connection):
            return conn.execute(
                f"""
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    u.email,
                    u.role,
                    u.department_id,
                    d.name AS department,
                    u.clearance_level,
                    u.is_active,
                    u.last_login_at,
                    u.session_version,
                    ARRAY_REMOVE(ARRAY_AGG(g.name ORDER BY g.name), NULL) AS groups
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                LEFT JOIN user_permission_groups ug ON ug.user_id = u.id
                LEFT JOIN permission_groups g ON g.id = ug.group_id
                {where_clause}
                GROUP BY u.id, d.name
                ORDER BY u.created_at DESC, u.email ASC
                """,
                params,
            ).fetchall()

        rows = self._run_with_retry(_op)
        return [
            {
                **dict(row),
                "id": str(row["id"]),
                "department_id": str(row["department_id"]) if row.get("department_id") else None,
                "clearance_level": int(row.get("clearance_level") or 1),
                "session_version": int(row.get("session_version") or 1),
            }
            for row in rows
        ]

    def create_user(
        self,
        full_name: str,
        username: str,
        email: str,
        temporary_password: str,
        role: str,
        department_id: Optional[str],
        clearance_level: int,
    ) -> str:
        normalized_email = self._normalize_email(email)
        if not username.strip():
            raise ValueError("Username không được để trống.")
        if len(temporary_password) < 8:
            raise ValueError("Mật khẩu tạm thời phải có ít nhất 8 ký tự.")

        salt_hex = secrets.token_hex(16)
        password_hash = self._hash_password(temporary_password, salt_hex)
        packed_hash = f"{salt_hex}${password_hash}"

        def _op(conn: psycopg.Connection) -> str:
            row = conn.execute(
                """
                INSERT INTO users(full_name, username, email, hashed_password, role, department_id, clearance_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    (full_name or "").strip() or username.strip(),
                    username.strip(),
                    normalized_email,
                    packed_hash,
                    role,
                    department_id,
                    max(1, min(5, int(clearance_level or 1))),
                ),
            ).fetchone()
            user_id = str(row["id"])
            self._log_audit_with_conn(conn, user_id, "user_create", {"email": normalized_email, "role": role})
            return user_id

        return self._run_with_retry(_op)

    def update_user(
        self,
        user_id: str,
        full_name: str,
        email: str,
        role: str,
        department_id: Optional[str],
        clearance_level: int,
    ) -> None:
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE users
                SET full_name = %s,
                    email = %s,
                    role = %s,
                    department_id = %s,
                    clearance_level = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    (full_name or "").strip(),
                    self._normalize_email(email),
                    role,
                    department_id,
                    max(1, min(5, int(clearance_level or 1))),
                    user_id,
                ),
            )
            self._log_audit_with_conn(conn, user_id, "user_update", {"role": role, "department_id": department_id})

        self._run_with_retry(_op)

    def set_user_active(self, user_id: str, is_active: bool) -> None:
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE users
                SET is_active = %s,
                    session_version = session_version + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (is_active, user_id),
            )
            self._log_audit_with_conn(conn, user_id, "user_status_change", {"is_active": is_active})

        self._run_with_retry(_op)

    def reset_user_password(self, user_id: str) -> str:
        temporary_password = secrets.token_urlsafe(10)
        salt_hex = secrets.token_hex(16)
        password_hash = self._hash_password(temporary_password, salt_hex)
        packed_hash = f"{salt_hex}${password_hash}"

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE users
                SET hashed_password = %s,
                    session_version = session_version + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (packed_hash, user_id),
            )
            self._log_audit_with_conn(conn, user_id, "user_password_reset", {"password_reset": True})

        self._run_with_retry(_op)
        return temporary_password

    def force_logout_user(self, user_id: str) -> None:
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                UPDATE users
                SET session_version = session_version + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (user_id,),
            )
            self._log_audit_with_conn(conn, user_id, "user_force_logout", {"forced": True})

        self._run_with_retry(_op)

    def list_user_groups(self, user_id: str) -> list[dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT g.id, g.name, g.description, g.max_clearance_level, g.is_system, ug.created_at
                FROM user_permission_groups ug
                JOIN permission_groups g ON g.id = ug.group_id
                WHERE ug.user_id = %s
                ORDER BY g.name ASC
                """,
                (user_id,),
            ).fetchall()

        rows = self._run_with_retry(_op)
        return [{**dict(row), "id": str(row["id"])} for row in rows]

    def assign_user_to_group(self, user_id: str, group_id: str) -> None:
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                INSERT INTO user_permission_groups(user_id, group_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, group_id) DO NOTHING
                """,
                (user_id, group_id),
            )
            self._log_audit_with_conn(conn, user_id, "rbac_group_assign", {"group_id": group_id})

        self._run_with_retry(_op)

    def remove_user_from_group(self, user_id: str, group_id: str) -> None:
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                "DELETE FROM user_permission_groups WHERE user_id = %s AND group_id = %s",
                (user_id, group_id),
            )
            self._log_audit_with_conn(conn, user_id, "rbac_group_remove", {"group_id": group_id})

        self._run_with_retry(_op)

    def upsert_group_department_permission(
        self,
        group_id: str,
        department: str,
        max_sensitivity: str,
        can_view_all_documents: bool = False,
    ) -> None:
        allowed_sensitivities = {"public", "internal", "confidential", "restricted"}
        normalized_sensitivity = str(max_sensitivity or "internal").strip().lower()
        if normalized_sensitivity not in allowed_sensitivities:
            raise ValueError("Mức bảo mật không hợp lệ.")

        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                INSERT INTO group_department_permissions(group_id, department, max_sensitivity, can_view_all_documents)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (group_id, department)
                DO UPDATE SET
                    max_sensitivity = EXCLUDED.max_sensitivity,
                    can_view_all_documents = EXCLUDED.can_view_all_documents,
                    updated_at = NOW()
                """,
                (group_id, department, normalized_sensitivity, can_view_all_documents),
            )
            self._log_audit_with_conn(conn, None, "rbac_matrix_update", {"group_id": group_id, "department": department})

        self._run_with_retry(_op)

    def list_group_department_permissions(self, group_id: Optional[str] = None) -> list[dict[str, Any]]:
        def _op(conn: psycopg.Connection):
            if group_id:
                return conn.execute(
                    """
                    SELECT id, group_id, department, max_sensitivity, can_view_all_documents, created_at, updated_at
                    FROM group_department_permissions
                    WHERE group_id = %s
                    ORDER BY department ASC
                    """,
                    (group_id,),
                ).fetchall()
            return conn.execute(
                """
                SELECT id, group_id, department, max_sensitivity, can_view_all_documents, created_at, updated_at
                FROM group_department_permissions
                ORDER BY department ASC
                """
            ).fetchall()

        rows = self._run_with_retry(_op)
        return [{**dict(row), "id": str(row["id"]), "group_id": str(row["group_id"])} for row in rows]

    def preview_user_access(self, user_id: str, document_id: str) -> Dict[str, Any]:
        def _op(conn: psycopg.Connection):
            return conn.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.full_name,
                    u.username,
                    u.email,
                    u.role,
                    u.clearance_level,
                    u.department_id,
                    d.name AS department,
                    u.is_active,
                    u.session_version,
                    doc.id AS document_id,
                    doc.file_name,
                    doc.metadata
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                JOIN documents doc ON doc.id = %s
                WHERE u.id = %s
                """,
                (document_id, user_id),
            ).fetchone()

        row = self._run_with_retry(_op)
        if not row:
            raise ValueError("Không tìm thấy user hoặc tài liệu.")

        metadata = row.get("metadata") or {}
        doc_department = str(metadata.get("department") or "general").strip().lower()
        doc_sensitivity = str(metadata.get("sensitivity") or "internal").strip().lower()
        user_clearance = int(row.get("clearance_level") or 1)
        user_role = row.get("role") or "Employee"
        can_access = False
        reasons = []

        if user_role == "Admin":
            can_access = True
            reasons.append("Admin có toàn quyền truy cập")
        else:
            if self._sensitivity_rank(doc_sensitivity) <= user_clearance:
                can_access = True
                reasons.append("Mức bảo mật trong ngưỡng cho phép")
            if row.get("department") and row.get("department") == doc_department:
                can_access = True
                reasons.append("Cùng phòng ban")

        return {
            "user_id": str(row["user_id"]),
            "document_id": str(row["document_id"]),
            "file_name": row.get("file_name"),
            "can_access": can_access,
            "reasons": reasons,
            "user": {
                "full_name": row.get("full_name") or row.get("username") or row.get("email"),
                "email": row.get("email"),
                "role": user_role,
                "department": row.get("department") or "general",
                "clearance_level": user_clearance,
            },
            "document": {
                "department": doc_department,
                "sensitivity": doc_sensitivity,
            },
        }

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

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        """Delete a conversation session (and its messages via CASCADE)."""
        def _op(conn: psycopg.Connection) -> None:
            conn.execute(
                """
                DELETE FROM chat_sessions
                WHERE id = %s AND user_id = %s
                """,
                (conversation_id, user_id),
            )
            self._log_audit_with_conn(
                conn,
                user_id,
                "conversation_delete",
                {"conversation_id": conversation_id},
            )

        self._run_with_retry(_op)

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

    def get_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str | list[str]] = None,
        email_query: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Truy vấn nhật ký hệ thống kèm bộ lọc và phân trang. Trả về (danh sách log, tổng số lượng bản ghi khớp lọc)."""
        conditions = []
        params = []

        if event_type:
            if isinstance(event_type, list):
                placeholders = ", ".join(["%s"] * len(event_type))
                conditions.append(f"a.event IN ({placeholders})")
                params.extend(event_type)
            else:
                conditions.append("a.event = %s")
                params.append(event_type)

        if email_query:
            conditions.append("u.email ILIKE %s")
            params.append(f"%{email_query.strip()}%")

        if start_date:
            conditions.append("a.created_at >= %s::timestamptz")
            params.append(start_date)

        if end_date:
            conditions.append("a.created_at <= %s::timestamptz + interval '1 day'")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        else:
            where_clause = ""

        def _op(conn: psycopg.Connection) -> tuple[list[dict[str, Any]], int]:
            # Query total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM audit_logs a
                LEFT JOIN users u ON u.id = a.user_id
                {where_clause}
            """
            count_row = conn.execute(count_query, params).fetchone()
            total_count = count_row["total"] if count_row else 0

            # Query rows
            select_query = f"""
                SELECT 
                    a.id,
                    a.event,
                    a.details,
                    a.created_at,
                    u.email as user_email,
                    u.role as user_role,
                    u.department_id as department_id,
                    d.name as department
                FROM audit_logs a
                LEFT JOIN users u ON u.id = a.user_id
                LEFT JOIN departments d ON d.id = u.department_id
                {where_clause}
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT %s OFFSET %s
            """
            rows = conn.execute(select_query, params + [limit, offset]).fetchall()
            
            logs = []
            for row in rows:
                r = dict(row)
                r["id"] = str(r["id"])
                logs.append(r)
            return logs, total_count

        return self._run_with_retry(_op)

