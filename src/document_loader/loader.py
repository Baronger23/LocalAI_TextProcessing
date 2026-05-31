"""
Document loader module for loading and processing various document types.
Supports both adaptive (structure-aware) and recursive chunking strategies.
Supports parallel file parsing via ThreadPoolExecutor.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.chunking import AdaptiveChunkingPipeline
from src.config import CHUNK_OVERLAP, CHUNK_SIZE, CHUNK_STRATEGY, PARSE_WORKERS


class DocumentProcessor:
    """Process and load documents from various sources."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        strategy: str = CHUNK_STRATEGY,
        parse_workers: int = PARSE_WORKERS,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        self.parse_workers = parse_workers

        # Legacy recursive splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        # Adaptive chunking pipeline
        self.adaptive_pipeline = AdaptiveChunkingPipeline(
            strategy=strategy,
            fallback_chunk_size=chunk_size,
            fallback_chunk_overlap=chunk_overlap,
        )

    def load_pdf(self, file_path: str) -> List[Document]:
        """Load a PDF file."""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        print(f"[INGESTION_DEBUG] PDF loader: {Path(file_path).name} → {len(docs)} pages")
        return docs

    def load_txt(self, file_path: str) -> List[Document]:
        """Load a text file."""
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        print(f"[INGESTION_DEBUG] TXT loader: {Path(file_path).name} → {len(docs)} documents")
        return docs

    def load_docx(self, file_path: str) -> List[Document]:
        """Load a Word document."""
        loader = UnstructuredWordDocumentLoader(file_path)
        docs = loader.load()
        print(f"[INGESTION_DEBUG] DOCX loader: {Path(file_path).name} → {len(docs)} sections")
        return docs

    def _load_single_file(self, file_path: Path) -> List[Document]:
        """Load a single file based on its extension. Returns [] on error."""
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".pdf":
                return self.load_pdf(str(file_path))
            elif suffix in (".txt", ".md"):
                return self.load_txt(str(file_path))
            elif suffix == ".docx":
                # Skip temporary Word files (e.g. ~$filename.docx)
                if file_path.name.startswith("~$"):
                    return []
                return self.load_docx(str(file_path))
            else:
                return []
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return []

    def load_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.*",
    ) -> List[Document]:
        """Load all documents from a directory using parallel parsing.

        Uses ThreadPoolExecutor to parse multiple files concurrently.
        Each file failure is caught individually — partial failures
        do NOT block other files from being loaded.
        """
        path = Path(directory_path)

        # Collect all supported files
        supported_extensions = {".pdf", ".txt", ".docx", ".md"}
        all_files = [
            f
            for f in path.rglob("*")
            if f.is_file()
            and f.suffix.lower() in supported_extensions
            and not f.name.startswith("~$")  # Skip temp Word files
        ]


        if not all_files:
            return []

        documents: List[Document] = []

        # Parse files in parallel
        with ThreadPoolExecutor(max_workers=self.parse_workers) as executor:
            future_to_file = {
                executor.submit(self._load_single_file, f): f for f in all_files
            }
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    docs = future.result()
                    documents.extend(docs)
                except Exception as e:
                    # Partial failure: log error but continue with other files
                    print(f"Error loading {file_path}: {e}")

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents using recursive strategy with outline enrichment."""
        merged_documents = self._merge_pages_by_source(documents)
        return self.adaptive_pipeline.chunk_documents(merged_documents)

    def _merge_pages_by_source(self, documents: List[Document]) -> List[Document]:
        """Merge page-level loader output by source before chunking.

        PDF loaders usually return one Document per page. Academic section
        headings often span page boundaries, so outline detection works better
        on the complete source text.
        """
        grouped: Dict[str, List[Document]] = {}
        source_order: List[str] = []

        for doc in documents:
            source = str(
                doc.metadata.get("source")
                or doc.metadata.get("file_path")
                or doc.metadata.get("file_name")
                or f"document-{len(source_order)}"
            )
            if source not in grouped:
                grouped[source] = []
                source_order.append(source)
            grouped[source].append(doc)

        if all(len(items) == 1 for items in grouped.values()):
            return documents

        merged: List[Document] = []
        for source in source_order:
            items = grouped[source]
            if len(items) == 1:
                merged.append(items[0])
                continue

            sorted_items = sorted(
                items,
                key=lambda item: item.metadata.get("page", item.metadata.get("page_number", 0)),
            )
            merged_metadata = dict(sorted_items[0].metadata)
            pages = [
                item.metadata.get("page", item.metadata.get("page_number"))
                for item in sorted_items
                if item.metadata.get("page", item.metadata.get("page_number")) is not None
            ]
            if pages:
                merged_metadata["page_start"] = min(pages)
                merged_metadata["page_end"] = max(pages)
                merged_metadata.pop("page", None)
                merged_metadata.pop("page_number", None)
            merged_metadata["source"] = source
            merged_metadata["merged_pages"] = len(sorted_items)

            merged_text = "\n\n".join(item.page_content for item in sorted_items)
            merged.append(Document(page_content=merged_text, metadata=merged_metadata))

        return merged

    def split_documents_adaptive(
        self, documents: List[Document],
    ) -> List[Document]:
        """Split documents using adaptive chunking pipeline.

        Uses Regex-based structure detection for Vietnamese legal docs,
        with automatic fallback to recursive splitting for unstructured text.
        """
        return self.adaptive_pipeline.chunk_documents(documents)

    def process_documents(
        self,
        source: str,
        is_directory: bool = True,
    ) -> List[Document]:
        """Load and split documents from source.

        Automatically selects chunking strategy based on config.
        """
        if is_directory:
            documents = self.load_directory(source)
        else:
            # Determine file type
            file_path = Path(source)
            if file_path.suffix.lower() == ".pdf":
                documents = self.load_pdf(source)
            elif file_path.suffix.lower() in (".txt", ".md"):
                documents = self.load_txt(source)
            elif file_path.suffix.lower() == ".docx":
                documents = self.load_docx(source)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

        print(f"[INGESTION_DEBUG] Loaded {len(documents)} raw documents from {source}")

        # Choose chunking strategy
        if self.strategy == "adaptive":
            chunks = self.split_documents_adaptive(documents)
        else:
            chunks = self.split_documents(documents)

        print(f"[INGESTION_DEBUG] After chunking: {len(chunks)} chunks")
        return chunks
