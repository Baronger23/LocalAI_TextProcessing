# Hướng dẫn cài đặt và chạy PostgreSQL (kèm pgvector) bằng Docker

Tài liệu này hướng dẫn các thành viên trong team cách khởi chạy cơ sở dữ liệu PostgreSQL đã được cài đặt sẵn extension `pgvector` để phục vụ cho dự án **SecureDocs AI**.

## 1. Yêu cầu hệ thống
- Đã cài đặt [Docker](https://www.docker.com/get-started) và [Docker Compose](https://docs.docker.com/compose/install/).
- Port `5432` trên máy của bạn đang trống (không có PostgreSQL nào khác đang chạy chiếm port này).

## 2. Cách Docker và pgvector hoạt động
Thay vì phải tự viết `Dockerfile` để tải PostgreSQL và biên dịch mã nguồn pgvector, dự án chúng ta sử dụng image chính thức `pgvector/pgvector:pg16`. Image này:
- Chạy dựa trên nền tảng PostgreSQL 16.
- Đã cài đặt sẵn extension `pgvector` phục vụ lưu trữ và tìm kiếm vector (embeddings).
- Tự động chạy file `database/postgres/schema.sql` vào lần khởi tạo đầu tiên để tạo toàn bộ các bảng (`documents`, `document_chunks`, v.v.) và kích hoạt các extension cần thiết (`pgcrypto`, `vector`).

## 3. Lệnh khởi chạy

Mở terminal/command prompt tại thư mục gốc của dự án (nơi có file `docker-compose.yml`) và chạy lệnh sau:

```bash
docker-compose up -d
```

- Tham số `-d` giúp container chạy ngầm (detached mode).
- Lần đầu chạy, Docker sẽ tải image `pgvector/pgvector:pg16` về máy (có thể mất một chút thời gian tùy mạng).

## 4. Kiểm tra trạng thái

Để xem database đã chạy thành công hay chưa:

```bash
docker-compose ps
```
Nếu cột `STATUS` hiển thị là `Up (healthy)`, nghĩa là database đã sẵn sàng nhận kết nối!

Xem log của database (để chắc chắn bảng đã được tạo thành công):
```bash
docker-compose logs -f postgres
```
Nhấn `Ctrl + C` để thoát chế độ xem log.

## 5. Kết nối đến Database
Ứng dụng (đã được cấu hình trong `src/config/settings.py`) sẽ tự động kết nối qua thông số sau:
- **Host**: `localhost`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `secure_docs_ai`

## 6. Dừng hoặc Xóa Database
- Để dừng database (không mất dữ liệu):
  ```bash
  docker-compose stop
  ```
- Để xóa container nhưng **giữ lại dữ liệu**:
  ```bash
  docker-compose down
  ```
- **[CẢNH BÁO]** Để xóa container VÀ xóa sạch dữ liệu (reset toàn bộ database):
  ```bash
  docker-compose down -v
  ```
