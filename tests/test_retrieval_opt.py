"""Manual smoke test for query rewriting and MMR retrieval.

This module intentionally does not define pytest tests because it calls real
Ollama/Chroma resources. Run it directly when a local RAG stack is available:

    python tests/test_retrieval_opt.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline

pytestmark = [pytest.mark.integration, pytest.mark.ollama]


def main() -> None:
    rag = RAGPipeline()

    print("=== Test 1: Query Rewriting ===")
    q = "CNTB ra doi nhu the nao"
    rewritten = rag._rewrite_query(q)
    print(f"Original : {q}")
    print(f"Rewritten: {rewritten}")

    print("\n=== Test 2: MMR deduplication ===")
    result = rag.query("Thời gian và cách thức ra đời của CNTB", k=4)
    print("Rewritten query:", result.get("rewritten_query"))
    print(f"\nAnswer:\n{result['answer']}")
    print("\nSources used:")
    for i, src in enumerate(result["sources"], 1):
        fname = src["metadata"].get("file_name", "?")
        sim = src["metadata"].get("similarity", 0.0)
        print(f"  [{i}] {fname}  (rrf_score={sim:.4f})")
        print(f"       {src['content'][:120].strip()}...")


if __name__ == "__main__":
    main()
