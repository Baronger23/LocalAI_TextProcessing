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
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
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
CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "adaptive")  # "adaptive" or "recursive"
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1500"))
MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", "200"))
CONTEXT_DEPTH = int(os.getenv("CONTEXT_DEPTH", "3"))
CONTEXT_PREFIX_ENABLED = os.getenv("CONTEXT_PREFIX_ENABLED", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# RAG Retrieval optimisation settings
QUERY_REWRITE_ENABLED = os.getenv("QUERY_REWRITE_ENABLED", "true").lower() == "true"

# MMR (Maximum Marginal Relevance) settings
MMR_ENABLED = os.getenv("MMR_ENABLED", "true").lower() == "true"
# λ: 1.0 = pure relevance, 0.0 = pure diversity. 0.8 is focused on high relevance.
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.8"))
# How many candidates to fetch from DB before MMR filtering down to k
MMR_FETCH_K = int(os.getenv("MMR_FETCH_K", "30"))

# Ingestion performance settings
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
PARSE_WORKERS = int(os.getenv("PARSE_WORKERS", "4"))
