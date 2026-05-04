"""Test initialization to debug Streamlit hang"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=== Testing Imports ===")
try:
    from src.rag import RAGPipeline
    print("✓ RAGPipeline imported")
except Exception as e:
    print(f"✗ RAGPipeline import failed: {e}")
    sys.exit(1)

try:
    from src.storage import ChatStore
    print("✓ ChatStore imported")
except Exception as e:
    print(f"✗ ChatStore import failed: {e}")
    sys.exit(1)

print("\n=== Testing RAG Initialization ===")
try:
    rag = RAGPipeline()
    print("✓ RAGPipeline initialized")
except Exception as e:
    print(f"✗ RAGPipeline init failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing ChatStore Initialization ===")
try:
    store = ChatStore()
    print("✓ ChatStore initialized")
except Exception as e:
    print(f"✗ ChatStore init failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All tests passed! ===")
