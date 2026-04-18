"""
Document loader module for loading and processing various document types.
Supports both adaptive (structure-aware) and recursive chunking strategies.
"""
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.config import CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_STRATEGY
from src.chunking import AdaptiveChunkingPipeline


class DocumentProcessor:
    """Process and load documents from various sources."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        strategy: str = CHUNK_STRATEGY,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

        # Legacy recursive splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        # Adaptive chunking pipeline
        self.adaptive_pipeline = AdaptiveChunkingPipeline(strategy=strategy)

    def load_pdf(self, file_path: str) -> List[Document]:
        """Load a PDF file."""
        loader = PyPDFLoader(file_path)
        return loader.load()

    def load_txt(self, file_path: str) -> List[Document]:
        """Load a text file."""
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()

    def load_docx(self, file_path: str) -> List[Document]:
        """Load a Word document."""
        loader = UnstructuredWordDocumentLoader(file_path)
        return loader.load()

    def load_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.*",
    ) -> List[Document]:
        """Load all documents from a directory."""
        documents = []
        path = Path(directory_path)

        # Load PDFs
        for pdf_file in path.glob("**/*.pdf"):
            try:
                documents.extend(self.load_pdf(str(pdf_file)))
            except Exception as e:
                print(f"Error loading {pdf_file}: {e}")

        # Load text files
        for txt_file in path.glob("**/*.txt"):
            try:
                documents.extend(self.load_txt(str(txt_file)))
            except Exception as e:
                print(f"Error loading {txt_file}: {e}")

        # Load Word documents
        for docx_file in path.glob("**/*.docx"):
            try:
                documents.extend(self.load_docx(str(docx_file)))
            except Exception as e:
                print(f"Error loading {docx_file}: {e}")

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents using the legacy recursive strategy."""
        return self.text_splitter.split_documents(documents)

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
            elif file_path.suffix.lower() == ".txt":
                documents = self.load_txt(source)
            elif file_path.suffix.lower() == ".docx":
                documents = self.load_docx(source)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

        # Choose chunking strategy
        if self.strategy == "adaptive":
            return self.split_documents_adaptive(documents)
        return self.split_documents(documents)
