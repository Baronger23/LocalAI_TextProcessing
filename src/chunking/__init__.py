"""
Chunking module — Adaptive + Context-Enriched Chunking
for Vietnamese legal/regulatory documents.
"""
from .chunking_pipeline import AdaptiveChunkingPipeline
from .context_enricher import ContextEnricher
from .vietnamese_chunker import DocumentSection, VietnameseDocumentParser

__all__ = [
    "AdaptiveChunkingPipeline",
    "VietnameseDocumentParser",
    "DocumentSection",
    "ContextEnricher",
]
