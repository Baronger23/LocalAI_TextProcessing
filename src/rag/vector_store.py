"""Vector store manager with ChromaDB and PostgreSQL pgvector backends."""

from __future__ import annotations

import hashlib
import json
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
    POSTGRES_SCHEMA,
    POSTGRES_VECTOR_TABLE,
    VECTOR_DIMENSION,
    VECTOR_STORE_BACKEND,
)
from src.embeddings import EmbeddingManager


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
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.backend = backend.lower()
        self.postgres_connection_string = postgres_connection_string
        self.postgres_schema = postgres_schema
        self.postgres_table_name = postgres_table_name
        self.vector_dimension = vector_dimension

        self._chroma_store: Chroma | None = None
        self._postgres_ready = False

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

    def _get_postgres_connection(self):
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
        DROP INDEX IF EXISTS {self.postgres_schema}.uq_chunks_content_hash;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_content_hash ON {self.postgres_schema}.{self.postgres_table_name}(content_hash);
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
    _MAX_EMBED_CHARS = 8000
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

        with self._get_postgres_connection() as conn:
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
                print(f"  Sample chunk previews: {previews}")
                
                print(f"[INGESTION_DEBUG] Source: {source_key}")
                print(f"  Total chunks parsed: {len(chunk_data)}")
                print(f"  Existing chunks for THIS document in DB: {len(existing_hashes)}")
                print(f"  New chunks to embed: {len(new_chunks)}")

                # FIX: Provide better visibility for re-upload scenarios
                if existing_hashes and len(new_chunks) > 0:
                    print(f"  ℹ️  RE-UPLOAD DETECTED: Adding {len(new_chunks)} new chunks to {len(existing_hashes)} existing chunks")

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
                    print(f"Embedding failed for {source_document['file_name']}: {exc}")
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
                        ON CONFLICT (content_hash)
                            DO NOTHING
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
                
                print(f"  Chunks inserted: {inserted_count}")

                # Mark document as done
                conn.execute(
                    f"UPDATE {self.postgres_schema}.documents "
                    f"SET embedding_status = 'done', updated_at = NOW() "
                    f"WHERE id = %s",
                    (document_id,),
                )

        return ids

    def _postgres_similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        keyword_query: Optional[str] = None,
    ) -> List[Document]:
        self._init_postgres_schema()

        # If keyword_query is not provided, use the semantic query
        fts_query = keyword_query if keyword_query else query

        _, Vector, _, _ = self._import_postgres_dependencies()
        query_vector = Vector(self.embedding_manager.embed_query(query))
        
        where_clause_semantic = ""
        where_clause_keyword = ""
        filter_json = None

        if filter:
            where_clause_semantic = "AND c.metadata @> %s::jsonb"
            where_clause_keyword = "AND c.metadata @> %s::jsonb"
            filter_json = json.dumps(_sanitize_json(filter))

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
            LIMIT 50
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
                ts_rank(c.fts_vector, websearch_to_tsquery('simple', %s) || websearch_to_tsquery('simple', %s)) AS keyword_score,
                ROW_NUMBER() OVER (ORDER BY ts_rank(c.fts_vector, websearch_to_tsquery('simple', %s) || websearch_to_tsquery('simple', %s)) DESC) AS keyword_rank
            FROM {self.postgres_schema}.{self.postgres_table_name} c
            JOIN {self.postgres_schema}.documents d ON d.id = c.document_id
            WHERE (c.fts_vector @@ websearch_to_tsquery('simple', %s) OR c.fts_vector @@ websearch_to_tsquery('simple', %s)) {where_clause_keyword}
            ORDER BY keyword_score DESC
            LIMIT 50
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
            COALESCE(1.0 / (60 + k.keyword_rank), 0.0) AS rrf_score,
            s.vector_score,
            k.keyword_score
        FROM semantic_search s
        FULL OUTER JOIN keyword_search k ON s.chunk_id = k.chunk_id
        ORDER BY rrf_score DESC
        LIMIT %s
        """

        final_params = []
        # Semantic parameters
        final_params.extend([query_vector, query_vector])
        if filter:
            final_params.append(filter_json)
        final_params.append(query_vector)
        
        # Keyword parameters (Semantic Query + Keyword Query)
        # We repeat them for rank, rank_order, and where clause
        final_params.extend([query, fts_query, query, fts_query, query, fts_query])
        if filter:
            final_params.append(filter_json)
            
        # Limit parameter
        final_params.append(k)

        with self._get_postgres_connection() as conn:
            rows = conn.execute(sql, final_params).fetchall()

        documents: List[Document] = []
        for row in rows:
            metadata = _sanitize_json(row["metadata"] or {})
            document_metadata = _sanitize_json(row["document_metadata"] or {})
            merged_metadata = {
                **document_metadata,
                **metadata,
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

    def _postgres_delete_collection(self) -> None:
        self._init_postgres_schema()

        with self._get_postgres_connection() as conn:
            conn.execute(f"DELETE FROM {self.postgres_schema}.{self.postgres_table_name}")
            conn.execute(f"DELETE FROM {self.postgres_schema}.documents")

    def _postgres_collection_stats(self) -> Dict[str, Any]:
        self._init_postgres_schema()

        with self._get_postgres_connection() as conn:
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
        with self._get_postgres_connection() as conn:
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
        return self.vector_store.similarity_search(query=query, k=k, filter=filter)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> List[tuple]:
        """Search for similar documents with relevance scores."""
        if self.backend == "postgres":
            return self._postgres_similarity_search_with_score(query=query, k=k)
        return self.vector_store.similarity_search_with_score(query=query, k=k)

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
