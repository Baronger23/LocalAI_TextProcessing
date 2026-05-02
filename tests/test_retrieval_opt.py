"""Quick smoke-test for Query Rewriting and MMR."""
import sys
sys.path.insert(0, ".")

from src.rag import RAGPipeline

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
