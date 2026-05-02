"""Migrate ChromaDB chunks into PostgreSQL pgvector tables."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure the project root is importable when this script is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg
from langchain_chroma import Chroma
from pgvector import Vector
from pgvector.psycopg import register_vector

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    POSTGRES_CONNECTION_STRING,
    POSTGRES_SCHEMA,
    POSTGRES_VECTOR_TABLE,
)
from src.embeddings import EmbeddingManager


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "postgres" / "schema.sql"


def _normalize_postgres_connection_string(connection_string: str) -> str:
    normalized = connection_string.strip()
    if normalized.startswith("postgresql+psycopg://"):
        return "postgresql://" + normalized.split("postgresql+psycopg://", 1)[1]
    if normalized.startswith("postgresql+asyncpg://"):
        return "postgresql://" + normalized.split("postgresql+asyncpg://", 1)[1]
    return normalized


def _sanitize_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _sanitize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _source_key(metadata: Dict[str, Any], fallback_text: str) -> str:
    candidate = (
        metadata.get("file_path")
        or metadata.get("source")
        or metadata.get("document_id")
        or metadata.get("title")
        or fallback_text
    )
    safe_text = str(candidate).strip() or fallback_text
    return f"source-{hashlib.sha1(safe_text.encode('utf-8')).hexdigest()[:16]}"


def _load_schema(conn: psycopg.Connection) -> None:
    if SCHEMA_PATH.exists():
        for statement in SCHEMA_PATH.read_text(encoding="utf-8").split(";"):
            cleaned_statement = statement.strip()
            if cleaned_statement:
                conn.execute(cleaned_statement)


def _get_chroma_items() -> Tuple[List[str], List[str], List[Dict[str, Any]], List[List[float]]]:
    embedding_manager = EmbeddingManager()
    store = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_manager.embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    payload = store._collection.get(include=["documents", "metadatas", "embeddings"])  # noqa: SLF001
    ids = list(payload.get("ids") or [])
    documents = list(payload.get("documents") or [])
    metadatas = list(payload.get("metadatas") or [])
    embeddings_payload = payload.get("embeddings")
    embeddings = list(embeddings_payload) if embeddings_payload is not None else []
    return ids, documents, metadatas, embeddings


def migrate() -> int:
    ids, documents, metadatas, embeddings = _get_chroma_items()
    if not documents:
        print("No ChromaDB documents found to migrate.")
        return 0

    with psycopg.connect(_normalize_postgres_connection_string(POSTGRES_CONNECTION_STRING), autocommit=True) as conn:
        register_vector(conn)
        conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        _load_schema(conn)

        migrated = 0
        chunk_counters: Dict[str, int] = {}
        for index, (doc_id, content, metadata, embedding) in enumerate(zip(ids, documents, metadatas, embeddings)):
            safe_metadata = _sanitize_json(metadata or {})
            source_key = _source_key(safe_metadata, doc_id or content[:32])
            file_path = str(safe_metadata.get("file_path") or safe_metadata.get("source") or "") or None
            file_name = str(safe_metadata.get("file_name") or (Path(file_path).name if file_path else f"document-{index + 1}.txt"))
            chunk_index = chunk_counters.get(source_key, 0)
            chunk_counters[source_key] = chunk_index + 1

            row = conn.execute(
                f"""
                INSERT INTO {POSTGRES_SCHEMA}.documents (source_key, file_name, file_path, metadata, status)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (source_key)
                DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    file_path = EXCLUDED.file_path,
                    metadata = {POSTGRES_SCHEMA}.documents.metadata || EXCLUDED.metadata,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    source_key,
                    file_name,
                    file_path,
                    json.dumps(safe_metadata),
                    "migrated",
                ),
            ).fetchone()

            if row is None:
                continue

            document_id = row[0]

            page_number = safe_metadata.get("page_number") or safe_metadata.get("page")
            conn.execute(
                f"""
                INSERT INTO {POSTGRES_SCHEMA}.{POSTGRES_VECTOR_TABLE}
                    (document_id, chunk_index, content, embedding, page_number, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (document_id, chunk_index)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    page_number = EXCLUDED.page_number,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                (
                    document_id,
                    chunk_index,
                    content,
                    Vector(embedding),
                    int(page_number) if isinstance(page_number, (int, float, str)) and str(page_number).isdigit() else None,
                    json.dumps(safe_metadata),
                ),
            )
            migrated += 1

    print(f"Migrated {migrated} ChromaDB chunks into PostgreSQL.")
    return migrated


if __name__ == "__main__":
    migrate()
    raise SystemExit(0)