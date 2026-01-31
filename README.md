# Local AI RAG System

Hệ thống RAG (Retrieval-Augmented Generation) sử dụng AI chạy local với Ollama.

## 🚀 Tính năng

- **LLM Local**: Qwen 2.5 7B chạy qua Ollama
- **Embedding**: Nomic-embed-text v1.5
- **Vector Database**: ChromaDB
- **Framework**: LangChain

## 📁 Cấu trúc dự án

```
Project/
├── data/                   # Dữ liệu đầu vào
│   ├── raw/               # File gốc (PDF, DOCX, TXT...)
│   └── processed/         # Dữ liệu đã xử lý
├── src/                    # Source code
│   ├── config/            # Cấu hình
│   ├── document_loader/   # Load và xử lý tài liệu
│   ├── embeddings/        # Embedding models
│   ├── llm/               # LLM wrapper
│   ├── rag/               # RAG pipeline
│   └── utils/             # Tiện ích
├── vector_db/             # ChromaDB storage
├── tests/                 # Unit tests
├── notebooks/             # Jupyter notebooks
├── requirements.txt       # Dependencies
└── README.md
```

## 🛠️ Cài đặt

### 1. Cài đặt Ollama
```bash
# Windows: Tải từ https://ollama.ai
# Hoặc dùng winget:
winget install Ollama.Ollama
```

### 2. Tải Models
```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text:v1.5
```

### 3. Tạo Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# hoặc
source venv/bin/activate      # Linux/Mac
```

### 4. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

## 🎯 Sử dụng

### Quick Start
```python
from src.rag.rag_pipeline import RAGPipeline

# Khởi tạo RAG
rag = RAGPipeline()

# Load documents
rag.load_documents("data/raw/")

# Query
response = rag.query("Câu hỏi của bạn?")
print(response)
```

### Chạy demo
```bash
python -m src.main
```

## 📋 Yêu cầu hệ thống

- Python 3.10+
- RAM: 8GB+ (khuyến nghị 16GB)
- GPU: Không bắt buộc (có thì tốt hơn)
- Dung lượng: ~5GB cho models

## 📝 License

MIT License

## 👥 Đóng góp

Mọi đóng góp đều được chào đón! Hãy tạo Issue hoặc Pull Request.
