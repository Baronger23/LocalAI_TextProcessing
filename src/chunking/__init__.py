"""
Chunking module — Adaptive + Context-Enriched Chunking
for Vietnamese legal/regulatory documents.
"""
from .chunking_pipeline import AdaptiveChunkingPipeline
from .vietnamese_chunker import VietnameseDocumentParser, DocumentSection
from .context_enricher import ContextEnricher

__all__ = [
    "AdaptiveChunkingPipeline",
    "VietnameseDocumentParser",
    "DocumentSection",
    "ContextEnricher",
]
