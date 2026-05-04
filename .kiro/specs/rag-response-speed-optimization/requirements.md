# Requirements Document

## Introduction

Hệ thống RAG chatbot hiện tại sử dụng Ollama local (LLM: qwen2.5:7b, Embedding: nomic-embed-text:v1.5), PostgreSQL + pgvector (hybrid search), và Streamlit. Người dùng phản ánh tốc độ phản hồi "cảm giác rất chậm". Phân tích codebase xác định bốn nguyên nhân gốc rễ chính:

1. **Model unload/reload liên tục** — `keep_alive=0` trong cả `EmbeddingManager` và `LLMManager` khiến Ollama giải phóng model khỏi VRAM sau mỗi lần gọi, buộc phải load lại từ đầu cho lần gọi tiếp theo.
2. **4 lần gọi LLM tuần tự per query** — Query Rewrite → Generate → Update Rolling Summary → Extract User Memories, trong đó 3 lần cuối là blocking sau khi user đã nhận được câu trả lời.
3. **Không có connection pooling** — Mỗi lần truy vấn PostgreSQL tạo mới một kết nối TCP.
4. **Fetch 50 candidates không cần thiết** — MMR bị disabled nhưng SQL vẫn fetch 50 candidates thay vì chỉ fetch đúng `k` kết quả cần thiết.

Tính năng này tối ưu pipeline để giảm thời gian phản hồi cảm nhận được (perceived latency) và thời gian xử lý thực tế (actual latency), đồng thời duy trì chất lượng câu trả lời và tính ổn định của hệ thống.

---

## Glossary

- **RAG_Pipeline**: Hệ thống Retrieval-Augmented Generation bao gồm query rewriting, hybrid search, và LLM generation.
- **LLMManager**: Module quản lý kết nối và gọi LLM Ollama (qwen2.5:7b).
- **EmbeddingManager**: Module quản lý kết nối và gọi Embedding model Ollama (nomic-embed-text:v1.5).
- **VectorStoreManager**: Module quản lý truy vấn PostgreSQL + pgvector.
- **Ollama**: Runtime local để chạy LLM và embedding model.
- **keep_alive**: Tham số Ollama kiểm soát thời gian giữ model trong VRAM sau khi dùng xong. Giá trị `-1` nghĩa là giữ mãi mãi.
- **TTFT (Time To First Token)**: Thời gian từ khi user gửi câu hỏi đến khi token đầu tiên của câu trả lời xuất hiện trên màn hình.
- **E2E Latency**: Tổng thời gian từ khi user gửi câu hỏi đến khi toàn bộ câu trả lời được hiển thị.
- **Post-response Task**: Tác vụ chạy sau khi user đã nhận được câu trả lời (update rolling summary, extract user memories).
- **Connection Pool**: Tập hợp các kết nối PostgreSQL được tái sử dụng thay vì tạo mới mỗi lần.
- **Streaming**: Kỹ thuật hiển thị từng token LLM ngay khi được sinh ra, thay vì chờ toàn bộ câu trả lời.
- **Benchmark**: Đo lường thời gian thực tế của từng bước trong pipeline để xác định bottleneck.
- **Candidate Fetch Count**: Số lượng chunks được lấy từ database trước khi reranking.

---

## Requirements

### Requirement 1: Đo lường và quan sát hiệu năng (Performance Benchmarking)

**User Story:** Là một developer, tôi muốn đo được thời gian thực tế của từng bước trong pipeline, để tôi có thể xác định đúng bottleneck và đánh giá hiệu quả của từng tối ưu hóa.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL ghi lại thời gian thực thi (tính bằng milliseconds) của từng bước: query rewriting, embedding, hybrid search, LLM generation, post-response tasks.
2. WHEN a query is processed, THE RAG_Pipeline SHALL trả về timing breakdown trong response dict dưới key `"timing"`.
3. THE RAG_Pipeline SHALL tính và ghi lại TTFT riêng biệt với E2E Latency.
4. WHEN timing data is collected, THE RAG_Pipeline SHALL log timing breakdown ở mức DEBUG để không làm ô nhiễm production logs.
5. IF a pipeline step exceeds 5000ms, THEN THE RAG_Pipeline SHALL log một WARNING với tên bước và thời gian thực tế.

---

### Requirement 2: Giữ model trong VRAM (Model Keep-Alive)

**User Story:** Là một người dùng, tôi muốn chatbot phản hồi nhanh hơn từ câu hỏi thứ hai trở đi, để tôi không phải chờ model load lại mỗi lần hỏi.

#### Acceptance Criteria

1. THE LLMManager SHALL khởi tạo OllamaLLM với `keep_alive=-1` để giữ model trong VRAM vô thời hạn trong suốt phiên làm việc.
2. THE EmbeddingManager SHALL khởi tạo OllamaEmbeddings với `keep_alive=-1` để giữ embedding model trong VRAM vô thời hạn trong suốt phiên làm việc.
3. WHERE `OLLAMA_KEEP_ALIVE` environment variable is set, THE LLMManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `-1`.
4. WHERE `OLLAMA_KEEP_ALIVE` environment variable is set, THE EmbeddingManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `-1`.
5. WHEN the application starts, THE RAG_Pipeline SHALL thực hiện một warm-up call để load cả LLM và embedding model vào VRAM trước khi nhận query đầu tiên từ user.
6. IF the warm-up call fails, THEN THE RAG_Pipeline SHALL log một WARNING và tiếp tục khởi động bình thường mà không crash.

---

### Requirement 3: Tách post-response tasks ra khỏi critical path (Async Post-Processing)

**User Story:** Là một người dùng, tôi muốn nhận được câu trả lời ngay sau khi LLM sinh xong, để tôi không phải chờ thêm thời gian cho các tác vụ nền như cập nhật summary hay trích xuất memory.

#### Acceptance Criteria

1. WHEN the LLM finishes generating an answer, THE RAG_Pipeline SHALL trả về câu trả lời cho user ngay lập tức mà không chờ rolling summary update hoàn thành.
2. WHEN the LLM finishes generating an answer, THE RAG_Pipeline SHALL trả về câu trả lời cho user ngay lập tức mà không chờ user memory extraction hoàn thành.
3. THE Post-response Task executor SHALL chạy rolling summary update trong một background thread riêng biệt sau khi câu trả lời đã được trả về.
4. THE Post-response Task executor SHALL chạy user memory extraction trong một background thread riêng biệt sau khi câu trả lời đã được trả về.
5. IF a post-response background task raises an exception, THEN THE Post-response Task executor SHALL log lỗi đó ở mức ERROR và không làm crash luồng chính.
6. WHILE a post-response background task is running, THE RAG_Pipeline SHALL không block việc nhận query tiếp theo từ user.
7. THE Post-response Task executor SHALL hoàn thành tất cả background tasks trong vòng 60 giây; IF a task exceeds 60 seconds, THEN THE Post-response Task executor SHALL cancel task đó và log một WARNING.

---

### Requirement 4: Streaming LLM response (Token Streaming)

**User Story:** Là một người dùng, tôi muốn thấy câu trả lời xuất hiện từng từ ngay khi LLM đang sinh, để cảm giác chờ đợi giảm đi dù tổng thời gian không đổi.

#### Acceptance Criteria

1. THE LLMManager SHALL hỗ trợ streaming mode trả về từng token ngay khi Ollama sinh ra thay vì chờ toàn bộ response.
2. WHEN streaming mode is enabled, THE RAG_Pipeline SHALL truyền từng token lên Streamlit UI ngay khi nhận được từ LLMManager.
3. WHEN streaming mode is enabled, THE Streamlit UI SHALL hiển thị từng token mới mà không cần `time.sleep()` giữa các ký tự.
4. WHERE `STREAMING_ENABLED` is set to `false`, THE RAG_Pipeline SHALL sử dụng non-streaming mode như hiện tại để đảm bảo backward compatibility.
5. IF the streaming connection is interrupted, THEN THE LLMManager SHALL log lỗi và trả về phần response đã nhận được cho đến thời điểm đó.

---

### Requirement 5: PostgreSQL Connection Pooling

**User Story:** Là một developer, tôi muốn hệ thống tái sử dụng kết nối PostgreSQL thay vì tạo mới mỗi lần query, để giảm overhead TCP handshake và authentication.

#### Acceptance Criteria

1. THE VectorStoreManager SHALL duy trì một connection pool với tối thiểu 2 và tối đa 10 kết nối PostgreSQL.
2. WHEN a database query is needed, THE VectorStoreManager SHALL lấy kết nối từ pool thay vì tạo kết nối mới.
3. WHEN a database query completes, THE VectorStoreManager SHALL trả kết nối về pool thay vì đóng kết nối.
4. WHERE `POSTGRES_POOL_MIN_SIZE` environment variable is set, THE VectorStoreManager SHALL sử dụng giá trị đó làm kích thước tối thiểu của pool.
5. WHERE `POSTGRES_POOL_MAX_SIZE` environment variable is set, THE VectorStoreManager SHALL sử dụng giá trị đó làm kích thước tối đa của pool.
6. IF all connections in the pool are in use and a new query arrives, THEN THE VectorStoreManager SHALL chờ tối đa 30 giây để có kết nối khả dụng trước khi raise một timeout exception.
7. IF a pooled connection becomes stale or broken, THEN THE VectorStoreManager SHALL tự động thay thế kết nối đó bằng một kết nối mới.

---

### Requirement 6: Tối ưu Hybrid Search candidate fetch (Search Optimization)

**User Story:** Là một developer, tôi muốn hybrid search chỉ fetch đúng số lượng candidates cần thiết, để giảm I/O và thời gian xử lý SQL không cần thiết.

#### Acceptance Criteria

1. WHILE MMR is disabled, THE VectorStoreManager SHALL giới hạn số lượng candidates fetch từ database bằng đúng `k` (số kết quả cuối cùng cần trả về) thay vì hardcode 50.
2. WHERE MMR is enabled, THE VectorStoreManager SHALL fetch `mmr_fetch_k` candidates từ database để có đủ pool cho MMR reranking.
3. THE VectorStoreManager SHALL đọc giá trị `k` từ tham số của hàm `similarity_search` thay vì dùng giá trị hardcode trong SQL.
4. WHEN the hybrid search SQL is executed, THE VectorStoreManager SHALL sử dụng `LIMIT %s` với tham số động thay vì `LIMIT 50` hardcode.
5. IF `k` is less than 1, THEN THE VectorStoreManager SHALL raise một ValueError với message mô tả rõ ràng.

---

### Requirement 7: Cấu hình tối ưu hóa qua environment variables

**User Story:** Là một developer, tôi muốn bật/tắt từng tối ưu hóa qua environment variables, để tôi có thể kiểm soát và rollback từng thay đổi một cách độc lập.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL đọc `OLLAMA_KEEP_ALIVE` từ environment để cấu hình thời gian giữ model trong VRAM; giá trị mặc định là `-1`.
2. THE RAG_Pipeline SHALL đọc `STREAMING_ENABLED` từ environment để bật/tắt token streaming; giá trị mặc định là `true`.
3. THE RAG_Pipeline SHALL đọc `ASYNC_POST_PROCESSING_ENABLED` từ environment để bật/tắt async post-response tasks; giá trị mặc định là `true`.
4. THE RAG_Pipeline SHALL đọc `POSTGRES_POOL_MIN_SIZE` và `POSTGRES_POOL_MAX_SIZE` từ environment để cấu hình connection pool; giá trị mặc định lần lượt là `2` và `10`.
5. THE `.env.example` file SHALL được cập nhật với tất cả các environment variables mới kèm giá trị mặc định và comment giải thích.
6. IF an environment variable has an invalid value (ví dụ: `POSTGRES_POOL_MAX_SIZE=abc`), THEN THE RAG_Pipeline SHALL log một WARNING và sử dụng giá trị mặc định thay vì crash.
