"""Vector store manager with ChromaDB and PostgreSQL pgvector backends."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    POSTGRES_CONNECTION_STRING,
    POSTGRES_POOL_MIN_SIZE,
    POSTGRES_POOL_MAX_SIZE,
    POSTGRES_SCHEMA,
    POSTGRES_VECTOR_TABLE,
    SEARCH_RESULT_BUFFER,
    VECTOR_DIMENSION,
    VECTOR_STORE_BACKEND,
    MMR_FETCH_K,
    MMR_ENABLED,
)
from src.embeddings import EmbeddingManager
from src.rag.exceptions import PoolTimeoutError
from src.security.access_policy import compact_filter_for_chroma

logger = logging.getLogger(__name__)


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


def _source_key_from_metadata(metadata: Dict[str, Any], fallback_text: str) -> str:
    candidate = (
        metadata.get("file_path")
        or metadata.get("source")
        or metadata.get("document_id")
        or metadata.get("title")
        or fallback_text
    )
    candidate_text = str(candidate).strip() or fallback_text
    digest = hashlib.sha1(candidate_text.encode("utf-8")).hexdigest()[:16]
    return f"source-{digest}"


def _execute_sql_script(conn: Any, script_text: str) -> None:
    for statement in script_text.split(";"):
        cleaned_statement = statement.strip()
        if cleaned_statement:
            conn.execute(cleaned_statement)


class VectorStoreManager:
    """Manage vector store operations using ChromaDB or PostgreSQL pgvector."""

    def __init__(
        self,
        persist_directory: str = CHROMA_PERSIST_DIR,
        collection_name: str = CHROMA_COLLECTION_NAME,
        embedding_manager: Optional[EmbeddingManager] = None,
        backend: str = VECTOR_STORE_BACKEND,
        postgres_connection_string: str = POSTGRES_CONNECTION_STRING,
        postgres_schema: str = POSTGRES_SCHEMA,
        postgres_table_name: str = POSTGRES_VECTOR_TABLE,
        vector_dimension: int = VECTOR_DIMENSION,
        pool_min_size: int = POSTGRES_POOL_MIN_SIZE,
        pool_max_size: int = POSTGRES_POOL_MAX_SIZE,
        search_result_buffer: int = SEARCH_RESULT_BUFFER,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.backend = backend.lower()
        self.postgres_connection_string = postgres_connection_string
        self.postgres_schema = postgres_schema
        self.postgres_table_name = postgres_table_name
        self.vector_dimension = vector_dimension
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self.search_result_buffer = search_result_buffer
        self._content_hash_index_name = (
            f"uq_{''.join(ch if ch.isalnum() else '_' for ch in self.postgres_table_name)}_content_hash"
        )

        self._chroma_store: Chroma | None = None
        self._postgres_ready = False
        self._pool = None  # psycopg.pool.ConnectionPool (lazy-init)

        Path(persist_directory).mkdir(parents=True, exist_ok=True)

    @property
    def vector_store(self) -> Chroma:
        """Return the Chroma store when the Chroma backend is active."""
        if self.backend != "chroma":
            raise RuntimeError("vector_store property is only available for Chroma backend")

        if self._chroma_store is None:
            self._chroma_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embedding_manager.embeddings,
                persist_directory=self.persist_directory,
            )
        return self._chroma_store

    def _import_postgres_dependencies(self):
        import psycopg
        from pgvector import Vector
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row

        return psycopg, Vector, register_vector, dict_row

    def _get_pool(self):
        """Lazy-init and return the psycopg connection pool.

        The pool is created once and reused for all subsequent queries.
        Pool size is controlled by ``pool_min_size`` / ``pool_max_size``.

        Requires the ``psycopg-pool`` package (``pip install psycopg-pool``).
        """
        if self._pool is not None:
            return self._pool

        try:
            # psycopg-pool ships as a separate package: psycopg_pool
            # (not psycopg.pool which is only available in psycopg[pool] extras)
            import psycopg_pool
            from pgvector.psycopg import register_vector
            from psycopg.rows import dict_row

            def configure(conn):
                conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                register_vector(conn)

            self._pool = psycopg_pool.ConnectionPool(
                conninfo=self.postgres_connection_string,
                min_size=self.pool_min_size,
                max_size=self.pool_max_size,
                timeout=30,
                kwargs={"autocommit": True, "row_factory": dict_row},
                configure=configure,
                open=False,  # Lazy open — don't block on init; connections created on first use
            )
            self._pool.open(wait=False)  # Start opening in background, don't block
            logger.debug(
                "[pool] Initialised PostgreSQL connection pool min=%d max=%d",
                self.pool_min_size,
                self.pool_max_size,
            )
        except Exception as exc:
            logger.warning(
                "[pool] Failed to create connection pool (%s) — falling back to single connections.",
                exc,
            )
            self._pool = None
            raise

        return self._pool

    def _get_postgres_connection(self):
        """Return a single psycopg connection.

        Used for schema migration (which needs an advisory lock + transaction)
        and as a fallback when the pool is unavailable.
        """
        psycopg, _, register_vector, dict_row = self._import_postgres_dependencies()
        conn = psycopg.connect(
            self.postgres_connection_string,
            autocommit=True,
            row_factory=dict_row,
        )
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        register_vector(conn)
        return conn

    def _pool_connection(self):
        """Context manager that yields a connection from the pool.

        Falls back to a direct connection if the pool is not available.

        Raises:
            PoolTimeoutError: if the pool cannot provide a connection within 30 s.
        """
        try:
            pool = self._get_pool()
            try:
                return pool.connection()
            except Exception as exc:
                raise PoolTimeoutError(
                    f"PostgreSQL connection pool timed out or failed: {exc}"
                ) from exc
        except PoolTimeoutError:
            raise
        except Exception:
            # Pool init failed — fall back to direct connection
            return self._get_postgres_connection()

    def _init_postgres_schema(self) -> None:
        if self._postgres_ready:
            return

        schema_sql = f"""
        CREATE SCHEMA IF NOT EXISTS {self.postgres_schema};

        CREATE TABLE IF NOT EXISTS {self.postgres_schema}.documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_key TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            file_path TEXT,
            file_hash TEXT,
            uploaded_by UUID,
            status TEXT NOT NULL DEFAULT 'active',
            embedding_status TEXT NOT NULL DEFAULT 'pending',
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS {self.postgres_schema}.{self.postgres_table_name} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES {self.postgres_schema}.documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL,
            content_hash TEXT,
            embedding vector({self.vector_dimension}) NOT NULL,
            embedding_model TEXT,
            embedding_version TEXT,
            processing_status TEXT NOT NULL DEFAULT 'done',
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            page_number INTEGER,
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(document_id, chunk_index)
        );

        ALTER TABLE {self.postgres_schema}.documents ADD COLUMN IF NOT EXISTS file_hash TEXT;
        ALTER TABLE {self.postgres_schema}.documents ADD COLUMN IF NOT EXISTS embedding_status TEXT DEFAULT 'pending';
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS content_hash TEXT;
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS embedding_model TEXT;
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS embedding_version TEXT;
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'done';
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS last_error TEXT;
        ALTER TABLE {self.postgres_schema}.{self.postgres_table_name} ADD COLUMN IF NOT EXISTS fts_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;

        CREATE INDEX IF NOT EXISTS idx_documents_file_path ON {self.postgres_schema}.documents(file_path);
        CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON {self.postgres_schema}.documents(file_hash);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON {self.postgres_schema}.{self.postgres_table_name}(document_id);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_content_hash ON {self.postgres_schema}.{self.postgres_table_name}(content_hash);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_page_number ON {self.postgres_schema}.{self.postgres_table_name}(page_number);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata ON {self.postgres_schema}.{self.postgres_table_name} USING gin (metadata);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON {self.postgres_schema}.{self.postgres_table_name} USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON {self.postgres_schema}.{self.postgres_table_name} USING gin(fts_vector);
        CREATE INDEX IF NOT EXISTS {self._content_hash_index_name} ON {self.postgres_schema}.{self.postgres_table_name}(content_hash);
        """

        with self._get_postgres_connection() as conn:
            # Use an explicit transaction and advisory lock to prevent concurrent migrations
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(123456)")
                _execute_sql_script(conn, schema_sql)

        self._postgres_ready = True

    def _get_source_document(self, metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
        file_path = str(metadata.get("file_path") or metadata.get("source") or "").strip() or None
        file_name = str(metadata.get("file_name") or (Path(file_path).name if file_path else "document.txt"))
        source_key = _source_key_from_metadata(metadata, file_path or file_name or content[:32])
        return {
            "source_key": source_key,
            "file_name": file_name,
            "file_path": file_path,
            "metadata": _sanitize_json(metadata),
        }

    # Maximum characters to feed into the embedding model per chunk.
    # Ollama can crash / return 400 if the input is extremely long.
    _MAX_EMBED_CHARS = 3000
    _EMBED_RETRIES = 3

    def _safe_embed(self, text: str) -> List[float]:
        """Embed text with truncation and retry to prevent Ollama OOM crashes."""
        import time
        truncated = text[: self._MAX_EMBED_CHARS]
        last_exc: Exception | None = None
        for attempt in range(1, self._EMBED_RETRIES + 1):
            try:
                return self.embedding_manager.embed_query(truncated)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._EMBED_RETRIES:
                    time.sleep(2 ** attempt)  # exponential back-off: 2s, 4s
        raise RuntimeError(
            f"Embedding failed after {self._EMBED_RETRIES} attempts: {last_exc}"
        ) from last_exc


    def _build_access_sql_filter(
        self,
        filter: Optional[Dict[str, Any]],
        chunk_alias: str = "c",
        document_alias: str = "d",
    ) -> tuple[str, List[Any]]:
        """Build SQL predicates for the RBAC metadata filter."""
        if not filter:
            return "", []

        clauses: List[str] = []
        params: List[Any] = []

        document_id = filter.get("document_id")
        if document_id:
            clauses.append(f"{chunk_alias}.document_id = %s")
            params.append(document_id)

        if not filter.get("admin"):
            metadata_expr = (
                f"COALESCE({chunk_alias}.metadata->>%s, {document_alias}.metadata->>%s)"
            )

            if filter.get("require_verified"):
                clauses.append(
                    f"COALESCE(({chunk_alias}.metadata->>'metadata_verified')::boolean, "
                    f"({document_alias}.metadata->>'metadata_verified')::boolean, FALSE) = TRUE"
                )

            departments = list(filter.get("departments") or [])
            if departments:
                clauses.append(f"{metadata_expr} = ANY(%s)")
                params.extend(["department", "department", departments])

            sensitivities = list(filter.get("sensitivities") or [])
            if sensitivities:
                clauses.append(f"{metadata_expr} = ANY(%s)")
                params.extend(["sensitivity", "sensitivity", sensitivities])

            role = str(filter.get("role") or "").strip()
            if role:
                allowed_roles_expr = (
                    f"COALESCE({chunk_alias}.metadata->'allowed_roles', "
                    f"{document_alias}.metadata->'allowed_roles')"
                )
                clauses.append(
                    f"({allowed_roles_expr} IS NULL OR CASE "
                    f"WHEN jsonb_typeof({allowed_roles_expr}) = 'array' THEN "
                    f"EXISTS (SELECT 1 FROM jsonb_array_elements_text({allowed_roles_expr}) AS allowed_role WHERE allowed_role = %s) "
                    f"ELSE TRUE END)"
                )
                params.append(role)

        if not clauses:
            return "", []
        return "AND " + " AND ".join(clauses), params

    @staticmethod
    def _compute_content_hash(text: str) -> str:
        """SHA256 hash of chunk text for deduplication."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _postgres_add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents with dual-layer dedup, batch embedding, bulk insert.

        Pipeline:
          1. Group documents by source file.
          2. Upsert source document row.
          3. Compute content_hash for each chunk → filter out existing hashes.
          4. Batch-embed only NEW chunks.
          5. Bulk insert with ON CONFLICT (content_hash) DO NOTHING.
        """
        self._init_postgres_schema()

        _, Vector, _, _ = self._import_postgres_dependencies()
        ids: List[str] = []
        grouped: Dict[str, List[tuple[int, Document, Dict[str, Any]]]] = {}
        
        print(f"\n[INGESTION_DEBUG] Starting _postgres_add_documents with {len(documents)} documents")

        for index, document in enumerate(documents):
            metadata = dict(document.metadata or {})
            source_document = self._get_source_document(metadata, document.page_content)
            grouped.setdefault(source_document["source_key"], []).append(
                (index, document, source_document)
            )

        with self._pool_connection() as conn:
            for source_key, items in grouped.items():
                source_document = items[0][2]

                # --- FIX: Check if document already exists and is already processed ---
                existing_doc = conn.execute(
                    f"SELECT id, embedding_status FROM {self.postgres_schema}.documents WHERE source_key = %s",
                    (source_key,),
                ).fetchone()
                
                # FIX: Don't skip based on document existence alone. Instead, let chunk-level deduplication
                # handle detection of duplicate content. This allows re-upload of partially-processed files.
                # For example: if a document had a failed insert with only 2 chunks, re-uploading will now
                # properly insert the remaining chunks instead of skipping entirely.
                
                # --- Step 1: Upsert document row ---
                document_row = conn.execute(
                    f"""
                    INSERT INTO {self.postgres_schema}.documents
                        (source_key, file_name, file_path, metadata, embedding_status)
                    VALUES (%s, %s, %s, %s::jsonb, 'processing')
                    ON CONFLICT (source_key)
                    DO UPDATE SET
                        file_name = EXCLUDED.file_name,
                        file_path = EXCLUDED.file_path,
                        metadata = {self.postgres_schema}.documents.metadata || EXCLUDED.metadata,
                        embedding_status = 'processing',
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (
                        source_key,
                        source_document["file_name"],
                        source_document["file_path"],
                        json.dumps(source_document["metadata"]),
                    ),
                ).fetchone()

                if document_row is None:
                    continue

                document_id = document_row["id"]
                ids.append(str(document_id))

                # --- Step 2: Compute content hashes & filter duplicates ---
                chunk_data = []
                for chunk_index, (_, document, _) in enumerate(items):
                    content = document.page_content
                    content_hash = self._compute_content_hash(content)
                    chunk_metadata = _sanitize_json(dict(document.metadata or {}))
                    page_number = chunk_metadata.get("page_number") or chunk_metadata.get("page")
                    chunk_data.append({
                        "chunk_index": chunk_index,
                        "content": content,
                        "content_hash": content_hash,
                        "page_number": (
                            int(page_number)
                            if isinstance(page_number, (int, float, str))
                            and str(page_number).isdigit()
                            else None
                        ),
                        "metadata": chunk_metadata,
                    })

                # FIX: Query existing chunks ONLY for this document, not global
                # This prevents aggressive deduplication that removes chunks from re-uploaded files
                all_hashes = [c["content_hash"] for c in chunk_data]
                if all_hashes:
                    placeholders = ",".join(["%s"] * len(all_hashes))
                    existing_rows = conn.execute(
                        f"SELECT content_hash FROM {self.postgres_schema}.{self.postgres_table_name} "
                        f"WHERE document_id = %s AND content_hash IN ({placeholders})",
                        [document_id] + all_hashes,
                    ).fetchall()
                    existing_hashes = {r["content_hash"] for r in existing_rows}
                else:
                    existing_hashes = set()

                # # Debug: inspect parsed hashes and existing hashes to diagnose re-upload issues
                # print(f"  Parsed content_hash count: {len(all_hashes)}")
                # unique_hashes = set(all_hashes)
                # print(f"  Unique parsed content_hashes: {len(unique_hashes)}")
                # print(f"  Sample parsed hashes: {list(all_hashes)[:8]}")
                # print(f"  Sample unique hashes: {list(unique_hashes)[:8]}")
                # print(f"  Existing hashes in DB for this document: {list(existing_hashes)[:8]} (count={len(existing_hashes)})")

                new_chunks = [c for c in chunk_data if c["content_hash"] not in existing_hashes]

                # Debug: show small content previews to verify chunking differences
                previews = [c["content"].replace("\n", " ")[:120] for c in chunk_data[:5]]
                logger.info("  Sample chunk previews: %s", previews)
                
                logger.info("[INGESTION_DEBUG] Source: %s", source_key)
                logger.info("  Total chunks parsed: %d", len(chunk_data))
                logger.info("  Existing chunks for THIS document in DB: %d", len(existing_hashes))
                logger.info("  New chunks to embed: %d", len(new_chunks))

                # FIX: Provide better visibility for re-upload scenarios
                if existing_hashes and len(new_chunks) > 0:
                    logger.info("  RE-UPLOAD DETECTED: Adding %d new chunks to %d existing chunks", len(new_chunks), len(existing_hashes))

                if not new_chunks:
                    # All chunks already exist — skip embedding entirely
                    conn.execute(
                        f"UPDATE {self.postgres_schema}.documents "
                        f"SET embedding_status = 'done', updated_at = NOW() "
                        f"WHERE id = %s",
                        (document_id,),
                    )
                    continue

                # --- Step 3: Batch embed only NEW chunks ---
                texts_to_embed = [c["content"] for c in new_chunks]
                try:
                    vectors = self.embedding_manager.embed_documents_batched(
                        texts_to_embed
                    )
                except Exception as exc:
                    # Mark document as failed but don't crash the whole pipeline
                    conn.execute(
                        f"UPDATE {self.postgres_schema}.documents "
                        f"SET embedding_status = 'failed', updated_at = NOW() "
                        f"WHERE id = %s",
                        (document_id,),
                    )
                    logger.warning("Embedding failed for %s: %s", source_document['file_name'], exc)
                    continue

                # --- Step 4: Bulk insert with ON CONFLICT DO NOTHING ---
                embedding_model = getattr(
                    self.embedding_manager, "model", EMBEDDING_MODEL
                )
                inserted_count = 0
                for chunk, vector in zip(new_chunks, vectors):
                    conn.execute(
                        f"""
                        INSERT INTO {self.postgres_schema}.{self.postgres_table_name}
                            (document_id, chunk_index, content, content_hash,
                             embedding, embedding_model, page_number, metadata,
                             processing_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'done')
                        ON CONFLICT (document_id, chunk_index)
                            DO UPDATE SET
                                content = EXCLUDED.content,
                                content_hash = EXCLUDED.content_hash,
                                embedding = EXCLUDED.embedding,
                                embedding_model = EXCLUDED.embedding_model,
                                page_number = EXCLUDED.page_number,
                                metadata = EXCLUDED.metadata,
                                processing_status = 'done',
                                updated_at = NOW()
                        """,
                        (
                            document_id,
                            chunk["chunk_index"],
                            chunk["content"],
                            chunk["content_hash"],
                            Vector(vector),
                            embedding_model,
                            chunk["page_number"],
                            json.dumps(chunk["metadata"]),
                        ),
                    )
                    inserted_count += 1
                
                logger.info("  Chunks inserted: %d", inserted_count)

                # Mark document as done
                conn.execute(
                    f"UPDATE {self.postgres_schema}.documents "
                    f"SET embedding_status = 'done', updated_at = NOW() "
                    f"WHERE id = %s",
                    (document_id,),
                )

        return ids

    @staticmethod
    def _to_simple_tsquery_string(query: str) -> str:
        """Convert a query string to a simple tsquery string with stop words filtered."""
        import re
        import unicodedata
        # Clean special characters including ?, ;, etc.
        cleaned = re.sub(r"[&|!:'()\"?,.;\-/[\]{}]", " ", query)
        raw_tokens = [t.strip() for t in cleaned.split() if t.strip()]

        stop_words = {
            "neu", "toi", "thi", "ai", "se", "bang", "cho", "cua", "da", "duoc", 
            "co", "khong", "la", "va", "hoac", "nhung", "vi", "nen", "voi", "tai", 
            "trong", "o", "nay", "do", "kia", "ay", "nao", "gi", "su", 
            "cac", "nhung", "mot", "hai", "bon", "tam", "chin", "muoi", "tren", 
            "duoi", "khi", "luc", "noi", "cho", "nguoi", "hay", "den", "de", 
            "theo", "nhu", "xem", "the",
            "a", "an", "in", "on", "at", "for", "of", "with", "to", "and", 
            "or", "if", "then", "who", "will", "be", "is", "are", "was", "were", 
            "you", "i", "he", "she", "they", "we", "it", "my", "your", "his", "her",
            "him", "them", "us", "our", "their", "this", "that", "these", "those",
            "thoi", "gian", "cach", "thuc", "ra", "doi", "ty",
            # Refined stop words
            "moi", "quy", "nhat", "lien", "quan"
        }

        def strip_accents(text):
            lowered = text.lower().replace("đ", "d")
            return "".join(
                ch for ch in unicodedata.normalize("NFD", lowered)
                if unicodedata.category(ch) != "Mn"
            )

        tokens = []
        for t in raw_tokens:
            t_stripped = strip_accents(t)
            if t_stripped not in stop_words and len(t) >= 2:
                tokens.append(t)

        if not tokens:
            tokens = [t for t in raw_tokens if len(t) >= 2]
        if not tokens:
            return "the"

        return " | ".join(tokens)

    def _postgres_similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        keyword_query: Optional[str] = None,
        mmr_enabled: bool = MMR_ENABLED,
        mmr_fetch_k: int = MMR_FETCH_K,
    ) -> List[Document]:
        """Hybrid search (pgvector cosine + FTS) with Reciprocal Rank Fusion.

        The HNSW index ``idx_document_chunks_embedding USING hnsw (embedding vector_cosine_ops)``
        is used automatically by PostgreSQL for the vector similarity scan.

        Args:
            query:         Semantic search query (rewritten / expanded).
            k:             Number of final results to return. Must be >= 1.
            filter:        Optional metadata filter applied as a pre-filter
                           (``WHERE metadata @> %s::jsonb``) before vector distance.
            keyword_query: Original query used for FTS (preserves abbreviations).
            mmr_enabled:   When True, fetch ``mmr_fetch_k`` candidates for MMR reranking.
            mmr_fetch_k:   Candidate pool size when MMR is enabled.

        Returns:
            Up to ``k`` :class:`~langchain_core.documents.Document` objects ranked by RRF score.

        Raises:
            ValueError: if ``k < 1``.
        """
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        self._init_postgres_schema()

        # Determine how many candidates to fetch from the DB.
        # When MMR is disabled: fetch k + buffer to compensate for ranking noise,
        # then trim back to k after RRF scoring.
        # When MMR is enabled: fetch mmr_fetch_k for the MMR candidate pool.
        if mmr_enabled:
            fetch_limit = mmr_fetch_k
        else:
            fetch_limit = k + self.search_result_buffer

        # If keyword_query is not provided, use the semantic query
        fts_query = keyword_query if keyword_query else query

        _, Vector, _, _ = self._import_postgres_dependencies()
        query_vector = Vector(self.embedding_manager.embed_query(query))

        where_clause_semantic, semantic_filter_params = self._build_access_sql_filter(
            filter,
            chunk_alias="c",
            document_alias="d",
        )
        where_clause_keyword, keyword_filter_params = self._build_access_sql_filter(
            filter,
            chunk_alias="c",
            document_alias="d",
        )

        sql = f"""
        WITH semantic_search AS (
            SELECT
                c.id as chunk_id,
                c.content,
                c.metadata,
                c.page_number,
                c.chunk_index,
                c.document_id,
                d.source_key,
                d.file_name,
                d.file_path,
                d.metadata AS document_metadata,
                1 - (c.embedding <=> %s) AS vector_score,
                ROW_NUMBER() OVER (ORDER BY c.embedding <=> %s) AS semantic_rank
            FROM {self.postgres_schema}.{self.postgres_table_name} c
            JOIN {self.postgres_schema}.documents d ON d.id = c.document_id
            WHERE 1=1 {where_clause_semantic}
            ORDER BY c.embedding <=> %s
            LIMIT %s
        ),
        keyword_search AS (
            SELECT
                c.id as chunk_id,
                c.content,
                c.metadata,
                c.page_number,
                c.chunk_index,
                c.document_id,
                d.source_key,
                d.file_name,
                d.file_path,
                d.metadata AS document_metadata,
                ts_rank_cd(c.fts_vector, to_tsquery('simple', %s)) AS keyword_score,
                ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.fts_vector, to_tsquery('simple', %s)) DESC) AS keyword_rank
            FROM {self.postgres_schema}.{self.postgres_table_name} c
            JOIN {self.postgres_schema}.documents d ON d.id = c.document_id
            WHERE c.fts_vector @@ to_tsquery('simple', %s) {where_clause_keyword}
            ORDER BY keyword_score DESC
            LIMIT %s
        )
        SELECT
            COALESCE(s.chunk_id, k.chunk_id) AS chunk_id,
            COALESCE(s.content, k.content) AS content,
            COALESCE(s.metadata, k.metadata) AS metadata,
            COALESCE(s.page_number, k.page_number) AS page_number,
            COALESCE(s.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(s.document_id, k.document_id) AS document_id,
            COALESCE(s.source_key, k.source_key) AS source_key,
            COALESCE(s.file_name, k.file_name) AS file_name,
            COALESCE(s.file_path, k.file_path) AS file_path,
            COALESCE(s.document_metadata, k.document_metadata) AS document_metadata,
            COALESCE(1.0 / (60 + s.semantic_rank), 0.0) +
            COALESCE(1.0 / (60 + k.keyword_rank), 0.0) AS raw_rrf_score,
            COALESCE(
                (COALESCE(s.document_metadata, k.document_metadata)->>'doc_authority')::float,
                1.0
            ) AS doc_authority,
            (
                COALESCE(1.0 / (60 + s.semantic_rank), 0.0) +
                COALESCE(1.0 / (60 + k.keyword_rank), 0.0)
            ) * COALESCE(
                (COALESCE(s.document_metadata, k.document_metadata)->>'doc_authority')::float,
                1.0
            ) AS rrf_score,
            s.vector_score,
            k.keyword_score
        FROM semantic_search s
        FULL OUTER JOIN keyword_search k ON s.chunk_id = k.chunk_id
        ORDER BY rrf_score DESC
        LIMIT %s
        """

        tsquery_str = self._to_simple_tsquery_string(fts_query)

        final_params = []
        # Semantic CTE parameters
        final_params.extend([query_vector, query_vector])
        final_params.extend(semantic_filter_params)
        final_params.extend([query_vector, fetch_limit])

        # Keyword CTE parameters
        final_params.extend([tsquery_str, tsquery_str, tsquery_str])
        final_params.extend(keyword_filter_params)
        final_params.append(fetch_limit)

        # Final LIMIT — trim to k after RRF scoring
        final_params.append(k)

        with self._pool_connection() as conn:
            rows = conn.execute(sql, final_params).fetchall()

        documents: List[Document] = []
        for row in rows:
            metadata = _sanitize_json(row["metadata"] or {})
            document_metadata = _sanitize_json(row["document_metadata"] or {})
            merged_metadata = {
                **document_metadata,
                **metadata,
                "chunk_id": str(row["chunk_id"]),
                "source_key": row["source_key"],
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "document_id": str(row["document_id"]),
                "chunk_index": row["chunk_index"],
                "page_number": row["page_number"],
                "similarity": float(row.get("rrf_score", 0.0)),
                "vector_score": float(row.get("vector_score") or 0.0),
                "keyword_score": float(row.get("keyword_score") or 0.0)
            }
            documents.append(
                Document(
                    page_content=row["content"],
                    metadata=merged_metadata,
                )
            )

        return documents

    def _postgres_similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> List[tuple]:
        documents = self._postgres_similarity_search(query=query, k=k)
        return [(document, document.metadata.get("similarity", 0.0)) for document in documents]

    def _postgres_keyword_search(
        self,
        query: str,
        k: int = 8,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Keyword-only PostgreSQL full-text search ranked by lexical score.

        This complements vector search for exact headings, names, years, and
        repeated technical phrases. It intentionally avoids embedding calls.
        """
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        self._init_postgres_schema()

        where_clause, filter_params = self._build_access_sql_filter(
            filter,
            chunk_alias="c",
            document_alias="d",
        )

        tsquery_str = self._to_simple_tsquery_string(query)

        sql = f"""
        SELECT
            c.id as chunk_id,
            c.content,
            c.metadata,
            c.page_number,
            c.chunk_index,
            c.document_id,
            d.source_key,
            d.file_name,
            d.file_path,
            d.metadata AS document_metadata,
            ts_rank_cd(c.fts_vector, to_tsquery('simple', %s)) AS keyword_score
        FROM {self.postgres_schema}.{self.postgres_table_name} c
        JOIN {self.postgres_schema}.documents d ON d.id = c.document_id
        WHERE c.fts_vector @@ to_tsquery('simple', %s) {where_clause}
        ORDER BY keyword_score DESC, c.chunk_index ASC
        LIMIT %s
        """

        params: List[Any] = [tsquery_str, tsquery_str]
        params.extend(filter_params)
        params.append(k)

        with self._pool_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        documents: List[Document] = []
        for row in rows:
            metadata = _sanitize_json(row["metadata"] or {})
            document_metadata = _sanitize_json(row["document_metadata"] or {})
            merged_metadata = {
                **document_metadata,
                **metadata,
                "chunk_id": str(row["chunk_id"]),
                "source_key": row["source_key"],
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "document_id": str(row["document_id"]),
                "chunk_index": row["chunk_index"],
                "page_number": row["page_number"],
                "keyword_score": float(row.get("keyword_score") or 0.0),
                "retrieval_method": "keyword",
            }
            documents.append(
                Document(
                    page_content=row["content"],
                    metadata=merged_metadata,
                )
            )

        return documents

    def _postgres_delete_collection(self) -> None:
        self._init_postgres_schema()

        with self._pool_connection() as conn:
            conn.execute(
                f"DELETE FROM {self.postgres_schema}.{self.postgres_table_name}"
            )
            conn.execute(
                f"""
                DELETE FROM {self.postgres_schema}.documents d
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {self.postgres_schema}.{POSTGRES_VECTOR_TABLE} c
                    WHERE c.document_id = d.id
                )
                """
            )

    def _postgres_collection_stats(self) -> Dict[str, Any]:
        self._init_postgres_schema()

        with self._pool_connection() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM {self.postgres_schema}.{self.postgres_table_name}"
            ).fetchone()

        return {
            "name": self.postgres_table_name,
            "count": int(row["count"] if row else 0),
            "backend": "postgres",
        }

    # ------------------------------------------------------------------
    # MMR (Maximum Marginal Relevance) helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _mmr_rerank(
        self,
        query: str,
        candidates: List[Document],
        k: int,
        lambda_mult: float = 0.6,
    ) -> List[Document]:
        """Apply Maximum Marginal Relevance to reduce redundancy.

        Picks `k` documents from `candidates` that maximise relevance
        to `query` while minimising similarity to already-selected docs.

        Args:
            query: The original search query (used to embed for comparison).
            candidates: Pool of retrieved documents to rerank.
            k: Number of documents to return.
            lambda_mult: λ in (0,1]. Higher → more relevance, lower → more diversity.
        """
        if not candidates or k <= 0:
            return []

        # If the candidate pool is smaller than k, just return all
        if len(candidates) <= k:
            return candidates

        # Embed the query once
        query_emb: List[float] = self.embedding_manager.embed_query(query)

        # Fetch stored embeddings for the candidate chunk_ids from the DB
        # to avoid re-embedding every document (expensive).
        chunk_ids = [
            doc.metadata.get("chunk_id") or doc.metadata.get("document_id")
            for doc in candidates
        ]

        # Build a dict: chunk_id -> embedding vector
        id_to_emb: Dict[str, List[float]] = {}
        with self._pool_connection() as conn:
            placeholders = ",".join(["%s"] * len(chunk_ids))
            rows = conn.execute(
                f"SELECT id, embedding::text AS emb "
                f"FROM {self.postgres_schema}.{self.postgres_table_name} "
                f"WHERE id::text IN ({placeholders})",
                chunk_ids,
            ).fetchall()
            for row in rows:
                id_to_emb[str(row["id"])] = eval(row["emb"])  # pgvector returns list

        # Pair each document with its embedding (fallback: skip if not found)
        doc_embs: List[Tuple[Document, List[float]]] = []
        for doc in candidates:
            cid = str(
                doc.metadata.get("chunk_id") or doc.metadata.get("document_id") or ""
            )
            if cid in id_to_emb:
                doc_embs.append((doc, id_to_emb[cid]))
            else:
                # Embedding not found in DB — fall back to re-embedding
                doc_embs.append((doc, self._safe_embed(doc.page_content)))

        # MMR greedy selection
        selected: List[Tuple[Document, List[float]]] = []
        remaining = list(doc_embs)

        # Pre-compute relevance scores (query ↔ each candidate)
        relevance = {id(emb): self._cosine_sim(query_emb, emb) for _, emb in remaining}

        for _ in range(k):
            if not remaining:
                break
            if not selected:
                # First pick: highest relevance to query
                best = max(remaining, key=lambda de: relevance[id(de[1])])
            else:
                best = None
                best_score = -float("inf")
                sel_embs = [emb for _, emb in selected]
                for de in remaining:
                    doc, emb = de
                    rel = relevance[id(emb)]
                    # Maximum similarity to any already-selected doc
                    max_sim = max(self._cosine_sim(emb, s) for s in sel_embs)
                    score = lambda_mult * rel - (1.0 - lambda_mult) * max_sim
                    if score > best_score:
                        best_score = score
                        best = de
            selected.append(best)  # type: ignore[arg-type]
            remaining.remove(best)  # type: ignore[arg-type]

        return [doc for doc, _ in selected]

    def mmr_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.6,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Hybrid search followed by MMR reranking for diverse results."""
        candidates = self.similarity_search(query=query, k=fetch_k, filter=filter)
        return self._mmr_rerank(query=query, candidates=candidates, k=k, lambda_mult=lambda_mult)


    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store."""
        if self.backend == "postgres":
            return self._postgres_add_documents(documents)
        return self.vector_store.add_documents(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        keyword_query: Optional[str] = None,
    ) -> List[Document]:
        """Search for similar documents."""
        if self.backend == "postgres":
            return self._postgres_similarity_search(
                query=query, k=k, filter=filter, keyword_query=keyword_query
            )
        chroma_filter = compact_filter_for_chroma(filter)
        return self.vector_store.similarity_search(query=query, k=k, filter=chroma_filter)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> List[tuple]:
        """Search for similar documents with relevance scores."""
        if self.backend == "postgres":
            return self._postgres_similarity_search_with_score(query=query, k=k)
        return self.vector_store.similarity_search_with_score(query=query, k=k)

    def keyword_search(
        self,
        query: str,
        k: int = 8,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Search by lexical keyword ranking when the backend supports it."""
        if self.backend == "postgres":
            return self._postgres_keyword_search(query=query, k=k, filter=filter)
        return []

    def delete_collection(self):
        """Delete the entire collection."""
        if self.backend == "postgres":
            self._postgres_delete_collection()
            return

        self.vector_store.delete_collection()
        self._chroma_store = None

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        if self.backend == "postgres":
            return self._postgres_collection_stats()

        collection = self.vector_store._collection
        return {
            "name": collection.name,
            "count": collection.count(),
            "backend": "chroma",
        }

    def get_document_version(self) -> str:
        """Return a coarse collection version for access-safe answer caching."""
        if self.backend == "postgres":
            self._init_postgres_schema()
            with self._pool_connection() as conn:
                row = conn.execute(
                    f"""
                    SELECT
                        COUNT(*) AS chunk_count,
                        COALESCE(MAX(c.updated_at), MAX(d.updated_at)) AS updated_at
                    FROM {self.postgres_schema}.{self.postgres_table_name} c
                    JOIN {self.postgres_schema}.documents d ON d.id = c.document_id
                    """
                ).fetchone()
            if not row:
                return "postgres:0:none"
            return f"postgres:{int(row['chunk_count'] or 0)}:{row['updated_at'] or 'none'}"

        collection = self.vector_store._collection
        return f"chroma:{collection.count()}"

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents from the database."""
        if self.backend != "postgres":
            return []
        self._init_postgres_schema()
        with self._pool_connection() as conn:
            rows = conn.execute(
                f"SELECT id, source_key, file_name, file_path, status, embedding_status, metadata, created_at, updated_at "
                f"FROM {self.postgres_schema}.documents "
                f"ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        if self.backend != "postgres":
            return []
        self._init_postgres_schema()
        with self._pool_connection() as conn:
            rows = conn.execute(
                f"SELECT id, chunk_index, content, metadata, page_number "
                f"FROM {self.postgres_schema}.{self.postgres_table_name} "
                f"WHERE document_id = %s "
                f"ORDER BY chunk_index ASC",
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

