"""Security policy helpers for role-aware RAG access control."""

from .access_policy import (
    ACCESS_DENIED_MESSAGE,
    NO_AUTHORIZED_CONTEXT_MESSAGE,
    build_access_filter,
    check_question_permission,
    classify_question_category,
    document_allowed,
    normalize_department,
    normalize_role,
)

__all__ = [
    "ACCESS_DENIED_MESSAGE",
    "NO_AUTHORIZED_CONTEXT_MESSAGE",
    "build_access_filter",
    "check_question_permission",
    "classify_question_category",
    "document_allowed",
    "normalize_department",
    "normalize_role",
]
