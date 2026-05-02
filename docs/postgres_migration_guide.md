# Hướng dẫn chuyển sang PostgreSQL cho SecureDocs AI

Tài liệu này hướng dẫn bằng tiếng Việt cách chuyển project từ SQLite/ChromaDB sang PostgreSQL. Ở máy bạn hiện tại, mình đang dùng Docker để chạy PostgreSQL vì cổng `5432` đã có instance khác chiếm, nên Docker sẽ map ra cổng `5433` trên máy host.

## PostgreSQL sẽ lưu gì

- `users`: thông tin người dùng và đăng nhập
- `documents`: thông tin tài liệu và đường dẫn file
- `document_chunks`: nội dung chunk, metadata và vector embedding
- `chat_sessions`: tiêu đề và tóm tắt hội thoại
- `chat_messages`: lịch sử chat và citations
- `audit_logs`: log hoạt động và bảo mật
- `user_memories`: bộ nhớ dài hạn của người dùng

File gốc vẫn nằm trên ổ đĩa, ví dụ trong `data/raw/`.

## Phần nào không lưu trong PostgreSQL

- File gốc: vẫn để trên máy / NAS / filesystem
- Chunking: sinh ra trong lúc ingest, không lưu cố định như một tầng riêng
- LLM: vẫn dùng Ollama
- ChromaDB: chỉ là backend dự phòng, không dùng khi bạn chuyển hẳn sang PostgreSQL

## Trạng thái hiện tại của máy bạn

Mình đã làm các việc sau trên máy bạn:

- Cài `psycopg[binary]` và `pgvector` vào `venv`
- Chạy PostgreSQL bằng Docker image `pgvector/pgvector:pg16-bookworm`
- Map cổng host `5433` vào cổng container `5432`
- Tạo container tên `secure-docs-pgvector`

Nghĩa là bạn có thể kết nối bằng DBeaver vào `localhost:5433` ngay bây giờ.

## Cấu hình Docker hiện tại

- Host: `localhost`
- Port: `5433`
- Database: `secure_docs_ai`
- User: `postgres`
- Password: `postgres`

## 1. Kết nối bằng DBeaver

Trong DBeaver, tạo kết nối PostgreSQL mới và điền:

- Host: `localhost`
- Port: `5433`
- Database: `secure_docs_ai`
- Username: `postgres`
- Password: `postgres`

Nếu kết nối được, nghĩa là container Docker đang chạy đúng.

## 2. Kiểm tra extension `vector`

Vì mình đang dùng image `pgvector/pgvector`, extension `vector` đã có sẵn trong container. Bạn chỉ cần mở SQL Editor trong DBeaver rồi chạy:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Nếu chạy thành công thì phần extension đã ổn.

## 3. Áp schema cho database

File schema nằm ở:

- `database/postgres/schema.sql`

Mở file này trong VS Code hoặc copy nội dung sang DBeaver rồi chạy trên database `secure_docs_ai`.

Lưu ý: hãy chạy toàn bộ file schema từ đầu đến cuối, không bôi đen chỉ một đoạn riêng lẻ. Mình đã kiểm tra file này trong container Docker và nó chạy bình thường.

Schema sẽ tạo các bảng:

- `departments`
- `users`
- `documents`
- `document_chunks`
- `chat_sessions`
- `chat_messages`
- `audit_logs`
- `user_memories`

## 4. Cấu hình `.env`

Mở file `.env` và đặt như sau:

```env
VECTOR_STORE_BACKEND=postgres
POSTGRES_CONNECTION_STRING=postgresql://postgres:postgres@localhost:5433/secure_docs_ai
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=secure_docs_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=public
POSTGRES_VECTOR_TABLE=document_chunks
VECTOR_DIMENSION=768
```

Nếu bạn đổi mật khẩu trong container, nhớ đổi lại trong connection string.

## 5. Chạy migrate từ ChromaDB sang PostgreSQL

Chạy lệnh này ở thư mục gốc project:

```powershell
.\venv\Scripts\python.exe scripts\migrate_chromadb_to_postgres.py
```

Script này sẽ:

- Đọc dữ liệu chunk và embedding từ ChromaDB cũ
- Tạo dữ liệu tương ứng trong PostgreSQL
- Ghi tài liệu vào `documents`
- Ghi chunk vào `document_chunks`

## 6. Chuyển app sang backend PostgreSQL

Sau khi migrate xong, giữ nguyên:

```env
VECTOR_STORE_BACKEND=postgres
```

Lúc này app sẽ query PostgreSQL thay vì ChromaDB.

Nếu muốn giữ ChromaDB tạm thời để so sánh, đổi lại:

```env
VECTOR_STORE_BACKEND=chroma
```

## 7. Smoke test nhanh

Chạy Python trong venv rồi test:

```powershell
.\venv\Scripts\python.exe
```

Sau đó nhập:

```python
from src.rag import RAGPipeline

rag = RAGPipeline()
result = rag.query("Câu hỏi kiểm tra retrieval là gì?")
print(result["answer"])
print(result["sources"])
```

Nếu ổn, bạn sẽ thấy:

- một câu trả lời
- một danh sách nguồn `sources` khi câu hỏi khớp dữ liệu đã index

## 8. Kiểm tra trong DBeaver

Chạy các câu lệnh sau để kiểm tra dữ liệu đã migrate:

```sql
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM document_chunks;
SELECT COUNT(*) FROM chat_sessions;
SELECT COUNT(*) FROM chat_messages;
```

Kiểm tra thử một số chunk:

```sql
SELECT id, document_id, chunk_index, page_number
FROM document_chunks
LIMIT 10;
```

## 9. DBeaver có dùng được không

Có. Nếu bạn dùng Docker container này thì kết nối như sau:

- Host: `localhost`
- Port: `5433`
- Database: `secure_docs_ai`
- User: `postgres`
- Password: `postgres`

Nếu bạn kết nối vào PostgreSQL cài trực tiếp trên máy, thì port có thể là `5432`.

## 10. Lỗi thường gặp

### `vector` không tìm thấy

Nếu báo `extension "vector" is not available`, nghĩa là bạn đang chạy vào PostgreSQL thường chứ không phải container pgvector, hoặc image/container chưa đúng.

Với Docker image mình đã tạo, lỗi này thường không còn.

### Kết nối không được từ DBeaver

Kiểm tra lại:

- Docker Desktop đã chạy chưa
- Container `secure-docs-pgvector` có đang `Up` không
- Port `5433` có bị firewall chặn không

### Migrate xong nhưng search không ra kết quả

Kiểm tra:

- `VECTOR_STORE_BACKEND=postgres`
- `POSTGRES_CONNECTION_STRING` trỏ đúng `localhost:5433`
- `document_chunks` có dữ liệu

### Script migrate lỗi

Kiểm tra:

- Database `secure_docs_ai` có tồn tại trong container
- DBeaver kết nối được vào container
- Gói `psycopg` và `pgvector` đã có trong `venv`

## Thứ tự làm chuẩn

1. Kết nối DBeaver vào `localhost:5433`
2. Chạy `CREATE EXTENSION vector;` và `pgcrypto`
3. Áp schema `database/postgres/schema.sql`
4. Sửa `.env` sang `localhost:5433`
5. Chạy `scripts/migrate_chromadb_to_postgres.py`
6. Test retrieval
7. Chạy app với `VECTOR_STORE_BACKEND=postgres`
