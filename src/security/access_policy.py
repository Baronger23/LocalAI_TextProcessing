"""Deterministic RBAC policy for sensitive RAG questions and documents."""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, List

ACCESS_DENIED_MESSAGE = "Bạn không có quyền truy cập nội dung này."
NO_AUTHORIZED_CONTEXT_MESSAGE = (
    "Tôi không tìm thấy thông tin phù hợp trong phạm vi quyền truy cập của bạn."
)

ROLES = {"Admin", "Manager", "Employee"}
DEPARTMENTS = {"finance", "hr", "it", "legal", "security", "general"}
SENSITIVITIES = {"public", "internal", "confidential", "restricted"}

SENSITIVE_KEYWORDS: Dict[str, List[str]] = {
    "finance": [
        "doanh thu",
        "loi nhuan",
        "lợi nhuận",
        "luong",
        "lương",
        "quy luong",
        "quỹ lương",
        "chi phi",
        "chi phí",
        "bao cao tai chinh",
        "báo cáo tài chính",
        "ngan sach",
        "ngân sách",
    ],
    "security": [
        "mat khau",
        "mật khẩu",
        "api key",
        "token",
        "secret",
        "private key",
        "khoa bi mat",
        "khóa bí mật",
        "lỗ hổng",
        "lo hong",
        "bao mat",
        "bảo mật",
    ],
    "hr": [
        "hop dong lao dong",
        "hợp đồng lao động",
        "ky luat",
        "kỷ luật",
        "danh gia nhan su",
        "đánh giá nhân sự",
        "ho so nhan vien",
        "hồ sơ nhân viên",
        "sa thai",
        "sa thải",
    ],
    "legal": [
        "kien tung",
        "kiện tụng",
        "hop dong phap ly",
        "hợp đồng pháp lý",
        "tranh chap",
        "tranh chấp",
        "phap che",
        "pháp chế",
    ],
}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(without_marks.lower().split())


def normalize_role(role: str | None) -> str:
    raw = (role or "Employee").strip().lower()
    mapping = {
        "admin": "Admin",
        "administrator": "Admin",
        "manager": "Manager",
        "employee": "Employee",
        "user": "Employee",
    }
    return mapping.get(raw, "Employee")


def normalize_department(department: str | None) -> str:
    value = _fold(department or "general")
    aliases = {
        "tai chinh": "finance",
        "finance": "finance",
        "nhan su": "hr",
        "hr": "hr",
        "it": "it",
        "cntt": "it",
        "phap ly": "legal",
        "phap che": "legal",
        "legal": "legal",
        "bao mat": "security",
        "security": "security",
        "general": "general",
        "chung": "general",
    }
    return aliases.get(value, value if value in DEPARTMENTS else "general")


def classify_question_category(question: str) -> str:
    folded = _fold(question)
    raw = (question or "").lower()
    for category, keywords in SENSITIVE_KEYWORDS.items():
        for keyword in keywords:
            if _fold(keyword) in folded or keyword.lower() in raw:
                return category
    return "general"


def check_question_permission(role: str, department: str, category: str) -> bool:
    role = normalize_role(role)
    department = normalize_department(department)
    category = normalize_department(category)

    if role == "Admin":
        return True
    if category == "general":
        return True
    if role == "Manager":
        return department == category
    return False


def build_access_filter(role: str, department: str) -> Dict[str, Any]:
    role = normalize_role(role)
    department = normalize_department(department)
    if role == "Admin":
        return {
            "policy": "rbac_v1",
            "role": role,
            "department": department,
            "admin": True,
        }
    if role == "Manager":
        return {
            "policy": "rbac_v1",
            "role": role,
            "department": department,
            "admin": False,
            "departments": sorted({"general", department}),
            "sensitivities": ["public", "internal", "confidential"],
            "require_verified": True,
        }
    return {
        "policy": "rbac_v1",
        "role": "Employee",
        "department": department,
        "admin": False,
        "departments": sorted({"general", department}),
        "sensitivities": ["public", "internal"],
        "require_verified": True,
    }


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def document_allowed(metadata: Dict[str, Any], access_filter: Dict[str, Any] | None) -> bool:
    if not access_filter or access_filter.get("admin"):
        return True

    role = normalize_role(access_filter.get("role"))
    allowed_departments = {
        normalize_department(item) for item in _as_list(access_filter.get("departments"))
    }
    allowed_sensitivities = {
        str(item).lower() for item in _as_list(access_filter.get("sensitivities"))
    }

    if access_filter.get("require_verified") and not _bool_value(metadata.get("metadata_verified")):
        return False

    doc_department = normalize_department(metadata.get("department"))
    doc_sensitivity = str(metadata.get("sensitivity") or "").strip().lower()
    if doc_department not in allowed_departments:
        return False
    if doc_sensitivity not in allowed_sensitivities:
        return False

    allowed_roles = {normalize_role(item) for item in _as_list(metadata.get("allowed_roles"))}
    if allowed_roles and role not in allowed_roles:
        return False
    return True


def compact_filter_for_chroma(access_filter: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """Return the subset of the policy filter Chroma can evaluate natively."""
    if not access_filter or access_filter.get("admin"):
        return None
    departments = _as_list(access_filter.get("departments"))
    sensitivities = _as_list(access_filter.get("sensitivities"))
    conditions: List[Dict[str, Any]] = [{"metadata_verified": True}]
    if departments:
        conditions.append({"department": {"$in": departments}})
    if sensitivities:
        conditions.append({"sensitivity": {"$in": sensitivities}})
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
