"""Shared pytest configuration for environment-dependent integration checks."""

from __future__ import annotations

import json
import socket
from functools import lru_cache
from urllib.request import urlopen

import pytest

from src.config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_BASE_URL,
    POSTGRES_HOST,
    POSTGRES_PORT,
)


@lru_cache(maxsize=1)
def _postgres_available(host: str = POSTGRES_HOST, port: int = POSTGRES_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def _ollama_models_available() -> bool:
    try:
        with urlopen(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return False

    available = {
        model.get("name") or model.get("model")
        for model in payload.get("models", [])
    }
    return {LLM_MODEL, EMBEDDING_MODEL}.issubset(available)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests that require external services such as PostgreSQL or Ollama",
    )
    config.addinivalue_line("markers", "postgres: tests that require PostgreSQL")
    config.addinivalue_line("markers", "ollama: tests that require Ollama models")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    postgres_skip = pytest.mark.skip(
        reason=f"PostgreSQL is not reachable at {POSTGRES_HOST}:{POSTGRES_PORT}"
    )
    ollama_skip = pytest.mark.skip(
        reason=f"Ollama is not reachable or lacks {LLM_MODEL}/{EMBEDDING_MODEL}"
    )

    for item in items:
        if "postgres" in item.keywords and not _postgres_available():
            item.add_marker(postgres_skip)
        if "ollama" in item.keywords and not _ollama_models_available():
            item.add_marker(ollama_skip)
