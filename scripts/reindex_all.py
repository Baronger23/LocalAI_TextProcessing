import sys
from pathlib import Path

# Force stdout/stderr to be UTF-8 to prevent charmap errors on Windows cmd/powershell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline
from src.rag.vector_store import VectorStoreManager

def main():
    print("=== STARTING FULL RE-INDEXING PROCESS ===")
    
    # 1. Initialize VectorStoreManager and delete all old records
    vsm = VectorStoreManager()
    print("Connecting to database and clearing collections...")
    try:
        vsm.delete_collection()
        print("SUCCESS: Database cleared successfully.")
    except Exception as e:
        print(f"ERROR: Error clearing database: {e}")
        sys.exit(1)
        
    # 2. Initialize RAGPipeline
    rag = RAGPipeline()
    
    # 3. Locate files in data/raw
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        print(f"ERROR: Directory {raw_dir} does not exist!")
        sys.exit(1)
        
    supported_extensions = {".pdf", ".txt", ".docx", ".md"}
    files_to_index = [
        f for f in raw_dir.glob("*")
        if f.is_file() and f.suffix.lower() in supported_extensions and not f.name.startswith("~$")
    ]

    # Noise/legacy/archive/draft files get lower authority so they don't outrank
    # authoritative policy documents in hybrid search.
    _NOISE_PATTERNS = ("noise", "legacy", "archive", "draft")

    def _doc_authority(filename: str) -> float:
        """Return authority score 0.0-1.0. Noise/legacy docs get 0.25."""
        name_lower = filename.lower()
        if any(pat in name_lower for pat in _NOISE_PATTERNS):
            return 0.25
        return 1.0

    
    if not files_to_index:
        print("WARNING: No raw documents found to index.")
        return

    print(f"Found {len(files_to_index)} documents to index:")
    for f in files_to_index:
        safe_name = str(f.name).encode('ascii', 'replace').decode()
        print(f" - {safe_name}")
        
    # 4. Load metadata mapping from JSON if it exists
    import json
    mapping_path = Path("data/policy_metadata_mapping.json")
    mapping = {}
    if mapping_path.exists():
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            print(f"Loaded metadata mapping for {len(mapping)} files from {mapping_path}")
        except Exception as e:
            print(f"WARNING: Failed to load metadata mapping: {e}")

    default_metadata = {
        "department": "general",
        "sensitivity": "public",
        "allowed_roles": ["Admin", "Manager", "Employee"],
        "metadata_verified": True,
        "doc_authority": 1.0,
    }
    
    total_chunks = 0
    for file_path in files_to_index:
        safe_name = str(file_path.name).encode('ascii', 'replace').decode()
        print(f"\nIndexing: {safe_name}...")
        
        # Determine metadata for this file
        authority = _doc_authority(file_path.name)
        meta = {**default_metadata, "doc_authority": authority}
        if file_path.name in mapping:
            meta = {
                "department": mapping[file_path.name].get("department", "general"),
                "sensitivity": mapping[file_path.name].get("sensitivity", "public"),
                "allowed_roles": mapping[file_path.name].get("allowed_roles", ["Admin", "Manager", "Employee"]),
                "metadata_verified": True,
                "doc_authority": authority,
            }
            print(f"  Mapped Metadata -> Dept: {meta['department']} | Sens: {meta['sensitivity']} | Roles: {meta['allowed_roles']} | Authority: {authority}")
        else:
            print(f"  Warning: No mapping found. Using default metadata. Authority: {authority}")
            
        try:
            chunks_loaded = rag.load_documents(
                source=str(file_path),
                is_directory=False,
                metadata=meta
            )
            print(f"SUCCESS: Indexed {chunks_loaded} chunks for {safe_name}")
            total_chunks += chunks_loaded
        except Exception as e:
            print(f"ERROR: Failed to index {safe_name}: {e}")
            
    print(f"\n=== RE-INDEXING COMPLETED ===")
    print(f"Total chunks created and inserted: {total_chunks}")

if __name__ == "__main__":
    main()
