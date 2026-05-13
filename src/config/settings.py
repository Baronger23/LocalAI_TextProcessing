"""
Configuration module for RAG system.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# LLM settings
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Embedding settings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:v1.5")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "768"))


def _normalize_postgres_connection_string(connection_string: str) -> str:
	normalized = connection_string.strip()
	if normalized.startswith("postgresql+psycopg://"):
		return "postgresql://" + normalized.split("postgresql+psycopg://", 1)[1]
	if normalized.startswith("postgresql+asyncpg://"):
		return "postgresql://" + normalized.split("postgresql+asyncpg://", 1)[1]
	return normalized

# ChromaDB settings
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(VECTOR_DB_DIR / "chroma_db"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "documents")

# PostgreSQL settings
VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE_BACKEND", "chroma").lower()
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5430"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "secure_docs_ai")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "public")
POSTGRES_CONNECTION_STRING = os.getenv(
	"POSTGRES_CONNECTION_STRING",
	"postgresql://"
	f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)
POSTGRES_CONNECTION_STRING = _normalize_postgres_connection_string(POSTGRES_CONNECTION_STRING)
POSTGRES_VECTOR_TABLE = os.getenv("POSTGRES_VECTOR_TABLE", "document_chunks")

# Document processing settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Adaptive Chunking settings
# Use "recursive" for academic documents (theses, reports) that don't follow
# Vietnamese legal structure (Chương/Điều). Use "adaptive" only for legal docs.
CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "recursive")
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1500"))
MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", "200"))
CONTEXT_DEPTH = int(os.getenv("CONTEXT_DEPTH", "3"))
CONTEXT_PREFIX_ENABLED = os.getenv("CONTEXT_PREFIX_ENABLED", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# RAG Retrieval optimisation settings
# Query rewriting expands abbreviations before search (e.g. CNTB → Chủ nghĩa Tư bản).
# Disabled by default — adds an extra LLM call and can degrade answer quality
# for queries that don't contain abbreviations.
QUERY_REWRITE_ENABLED = os.getenv("QUERY_REWRITE_ENABLED", "false").lower() == "true"

# MMR (Maximum Marginal Relevance) settings
MMR_ENABLED = os.getenv("MMR_ENABLED", "true").lower() == "true"
# λ: 1.0 = pure relevance, 0.0 = pure diversity. 0.8 is focused on high relevance.
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.8"))
# How many candidates to fetch from DB before MMR filtering down to k
MMR_FETCH_K = int(os.getenv("MMR_FETCH_K", "30"))

# Ingestion performance settings
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
PARSE_WORKERS = int(os.getenv("PARSE_WORKERS", "4"))


def _safe_int(env_var: str, default: int) -> int:
    """Read an integer env var; log WARNING and return default if invalid."""
    import logging
    raw = os.getenv(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logging.getLogger(__name__).warning(
            "Invalid value for %s=%r — using default %d", env_var, raw, default
        )
        return default


def _safe_bool(env_var: str, default: bool) -> bool:
    """Read a boolean env var; log WARNING and return default if invalid."""
    import logging
    raw = os.getenv(env_var)
    if raw is None:
        return default
    if raw.lower() in ("true", "1", "yes"):
        return True
    if raw.lower() in ("false", "0", "no"):
        return False
    logging.getLogger(__name__).warning(
        "Invalid value for %s=%r — using default %s", env_var, raw, default
    )
    return default


# ---------------------------------------------------------------------------
# Performance optimisation settings
# ---------------------------------------------------------------------------

# Ollama model keep-alive duration in seconds.
# 300 = 5 minutes (safe default for production).
# Set to -1 for dev/local to keep model loaded indefinitely.
OLLAMA_KEEP_ALIVE = _safe_int("OLLAMA_KEEP_ALIVE", 300)

# Maximum number of models Ollama is allowed to load into VRAM simultaneously.
# Keeping this at 1 prevents VRAM overflow when LLM and embedding model compete.
OLLAMA_MAX_LOADED_MODELS = _safe_int("OLLAMA_MAX_LOADED_MODELS", 1)

# Enable true token streaming from Ollama → Streamlit UI.
# When False, falls back to the original non-streaming flow.
STREAMING_ENABLED = _safe_bool("STREAMING_ENABLED", True)

# Run rolling-summary update and memory extraction in background threads
# so the user receives the answer immediately after LLM generation.
ASYNC_POST_PROCESSING_ENABLED = _safe_bool("ASYNC_POST_PROCESSING_ENABLED", True)

# PostgreSQL connection pool sizes (sync psycopg pool).
POSTGRES_POOL_MIN_SIZE = _safe_int("POSTGRES_POOL_MIN_SIZE", 2)
POSTGRES_POOL_MAX_SIZE = _safe_int("POSTGRES_POOL_MAX_SIZE", 10)

# Fuse query-rewriting into the main generation prompt to reduce LLM calls
# from 2 → 1 in the critical path.
# NOTE: Disabled by default — small models (qwen2.5:7b) often produce lower-quality
# answers when asked to simultaneously rewrite + answer + return JSON.
# Enable only if your model handles structured output reliably.
PROMPT_FUSION_ENABLED = _safe_bool("PROMPT_FUSION_ENABLED", False)

# LLM concurrency control — limits simultaneous Ollama calls to avoid GPU thrash.
LLM_MAX_CONCURRENT_CALLS = _safe_int("LLM_MAX_CONCURRENT_CALLS", 2)

# Maximum number of requests that can queue while waiting for the LLM semaphore.
# Requests beyond this limit are rejected immediately.
LLM_MAX_QUEUE_SIZE = _safe_int("LLM_MAX_QUEUE_SIZE", 10)

# Query-level answer cache (in-memory, TTL-based).
QUERY_CACHE_ENABLED = _safe_bool("QUERY_CACHE_ENABLED", True)
CACHE_TTL_SECONDS = _safe_int("CACHE_TTL_SECONDS", 300)

# Embedding vector cache (in-memory LRU).
EMBEDDING_CACHE_ENABLED = _safe_bool("EMBEDDING_CACHE_ENABLED", True)
EMBEDDING_CACHE_MAX_SIZE = _safe_int("EMBEDDING_CACHE_MAX_SIZE", 1000)

# Extra candidates fetched beyond k in hybrid search to compensate for
# ranking noise before trimming back to k at the application layer.
SEARCH_RESULT_BUFFER = _safe_int("SEARCH_RESULT_BUFFER", 5)

# ---------------------------------------------------------------------------
# Response quality settings
# ---------------------------------------------------------------------------

# Default retrieval size for focused/fact-style questions.
DEFAULT_TOP_K = _safe_int("DEFAULT_TOP_K", 8)

# Retrieval size for broad synthesis/analysis questions that need wider coverage.
BROAD_QUERY_TOP_K = _safe_int("BROAD_QUERY_TOP_K", 15)

# Maximum number of characters packed into the LLM context.
MAX_CONTEXT_CHARS = _safe_int("MAX_CONTEXT_CHARS", 18000)

# Add keyword-only retrieval results for broad questions to recover exact
# headings, names, years, and technical phrases missed by vector search.
KEYWORD_SUPPLEMENT_ENABLED = _safe_bool("KEYWORD_SUPPLEMENT_ENABLED", True)
KEYWORD_SUPPLEMENT_TOP_K = _safe_int("KEYWORD_SUPPLEMENT_TOP_K", 8)
