"""Debug embedding return count."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import EmbeddingManager


def test_embedding_count():
    """Check if embedding returns correct count of vectors."""
    
    # Create test texts
    test_texts = [f"Test text number {i} with some content." for i in range(1, 11)]
    
    print(f"\n[DEBUG] Testing embedding with {len(test_texts)} texts")
    
    embedding_manager = EmbeddingManager()
    
    # Test single embed
    print(f"\n[DEBUG] Test 1: Single embed_query")
    vector = embedding_manager.embed_query(test_texts[0])
    print(f"  Result: {type(vector)} with length {len(vector)}")
    
    # Test batch embed
    print(f"\n[DEBUG] Test 2: Batch embed_documents")
    vectors = embedding_manager.embed_documents(test_texts)
    print(f"  Input: {len(test_texts)} texts")
    print(f"  Output: {len(vectors)} vectors")
    
    # Test batched embed
    print(f"\n[DEBUG] Test 3: Batched embed_documents_batched")
    vectors_batched = embedding_manager.embed_documents_batched(test_texts, batch_size=3)
    print(f"  Input: {len(test_texts)} texts")
    print(f"  Batch size: 3")
    print(f"  Output: {len(vectors_batched)} vectors")
    
    # Verify count match
    if len(vectors) != len(test_texts):
        print(f"\n[ERROR] embed_documents returned {len(vectors)} vectors for {len(test_texts)} texts!")
    
    if len(vectors_batched) != len(test_texts):
        print(f"\n[ERROR] embed_documents_batched returned {len(vectors_batched)} vectors for {len(test_texts)} texts!")
    
    # Test with 344 texts (simulate actual case)
    print(f"\n[DEBUG] Test 4: Large batch (344 texts)")
    large_texts = [f"Large batch text {i}: " + "test content " * 50 for i in range(1, 345)]
    try:
        vectors_large = embedding_manager.embed_documents_batched(large_texts, batch_size=32)
        print(f"  Input: {len(large_texts)} texts")
        print(f"  Output: {len(vectors_large)} vectors")
        if len(vectors_large) != len(large_texts):
            print(f"  [MISMATCH] Expected {len(large_texts)}, got {len(vectors_large)}")
    except Exception as e:
        print(f"  [ERROR] {e}")


if __name__ == "__main__":
    test_embedding_count()
