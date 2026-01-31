"""
Utility functions for the RAG system.
"""
import logging
from pathlib import Path
from typing import Optional

from src.config import LOG_LEVEL, BASE_DIR


def setup_logging(
    level: str = LOG_LEVEL,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Setup logging configuration."""
    logger = logging.getLogger("rag_system")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = BASE_DIR / "logs"
        log_path.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_path / log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        BASE_DIR / "data" / "raw",
        BASE_DIR / "data" / "processed",
        BASE_DIR / "vector_db",
        BASE_DIR / "logs",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    return Path(file_path).stat().st_size / (1024 * 1024)


def format_sources(sources: list) -> str:
    """Format sources for display."""
    if not sources:
        return "Không có nguồn tham khảo."
    
    formatted = []
    for i, source in enumerate(sources, 1):
        formatted.append(f"\n📄 Nguồn {i}:")
        formatted.append(f"   {source['content']}")
        if source.get('metadata'):
            formatted.append(f"   Metadata: {source['metadata']}")
    
    return "\n".join(formatted)
