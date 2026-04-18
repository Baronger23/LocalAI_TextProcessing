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

# ChromaDB settings
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(VECTOR_DB_DIR / "chroma_db"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "documents")

# Document processing settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Adaptive Chunking settings
CHUNK_STRATEGY = os.getenv("CHUNK_STRATEGY", "adaptive")  # "adaptive" or "recursive"
MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1500"))
MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", "200"))
CONTEXT_DEPTH = int(os.getenv("CONTEXT_DEPTH", "3"))
CONTEXT_PREFIX_ENABLED = os.getenv("CONTEXT_PREFIX_ENABLED", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
