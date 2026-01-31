"""
Document loader module for loading and processing various document types.
"""
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.config import CHUNK_SIZE, CHUNK_OVERLAP


class DocumentProcessor:
    """Process and load documents from various sources."""
    
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
    
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
        glob_pattern: str = "**/*.*"
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
        """Split documents into chunks."""
        return self.text_splitter.split_documents(documents)
    
    def process_documents(
        self,
        source: str,
        is_directory: bool = True
    ) -> List[Document]:
        """Load and split documents from source."""
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
        
        return self.split_documents(documents)
