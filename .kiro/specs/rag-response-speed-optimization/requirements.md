# Requirements Document

## Introduction

Hệ thống RAG chatbot hiện tại sử dụng Ollama local (LLM: qwen2.5:7b, Embedding: nomic-embed-text:v1.5), PostgreSQL + pgvector (hybrid search), và Streamlit. Người dùng phản ánh tốc độ phản hồi "cảm giác rất chậm". Phân tích codebase xác định các nguyên nhân gốc rễ chính:

1. **Model unload/reload liên tục** — `keep_alive=0` trong cả `EmbeddingManager` và `LLMManager` khiến Ollama giải phóng model khỏi VRAM sau mỗi lần gọi, buộc phải load lại từ đầu cho lần gọi tiếp theo.
2. **Nhiều lần gọi LLM tuần tự per query** — Query Rewrite gọi LLM riêng (LLM call #1) → Generate gọi LLM riêng (LLM call #2) → Update Rolling Summary → Extract User Memories. Có thể giảm xuống còn 2 LLM calls bằng cách gộp query rewrite vào main generation prompt (Prompt Fusion).
3. **Không có connection pooling** — Mỗi lần truy vấn PostgreSQL tạo mới một kết nối TCP.
4. **Fetch 50 candidates không cần thiết** — MMR bị disabled nhưng SQL vẫn fetch 50 candidates thay vì chỉ fetch đúng `k` kết quả cần thiết.
5. **Không có concurrency control** — Nhiều Streamlit users có thể cùng gọi Ollama đồng thời, gây GPU thrash và latency tăng đột biến.
6. **Không có caching** — Các query lặp lại hoặc embedding giống nhau phải tính toán lại từ đầu mỗi lần.

Tính năng này tối ưu pipeline để giảm thời gian phản hồi cảm nhận được (perceived latency) và thời gian xử lý thực tế (actual latency), đồng thời duy trì chất lượng câu trả lời và tính ổn định của hệ thống.

**Scope tối ưu FINAL:**
- ✔ keep_alive có giới hạn (configurable, mặc định 300s — KHÔNG dùng -1 vô hạn)
- ✔ Token streaming từ Ollama → Streamlit
- ✔ Async post-processing (rolling summary, memory extraction)
- ✔ Connection pool sync với psycopg (KHÔNG chuyển asyncpg)
- ✔ LIMIT k search (dynamic, không hardcode)
- ✔ Prompt Fusion (gộp query rewrite vào main LLM call)
- ✔ LLM Concurrency Control (Semaphore)
- ✔ Basic Caching (query cache + embedding cache)

---

## Glossary

- **RAG_Pipeline**: Hệ thống Retrieval-Augmented Generation bao gồm query rewriting, hybrid search, và LLM generation.
- **LLMManager**: Module quản lý kết nối và gọi LLM Ollama (qwen2.5:7b).
- **EmbeddingManager**: Module quản lý kết nối và gọi Embedding model Ollama (nomic-embed-text:v1.5).
- **VectorStoreManager**: Module quản lý truy vấn PostgreSQL + pgvector.
- **Ollama**: Runtime local để chạy LLM và embedding model.
- **Adaptive_Keep_Alive**: Chiến lược giữ model trong VRAM với thời gian có giới hạn (mặc định 300s), configurable qua `OLLAMA_KEEP_ALIVE`. Khác với `-1` (vô hạn) vì tránh OOM khi load thêm model khác.
- **TTFT (Time To First Token)**: Thời gian từ khi user gửi câu hỏi đến khi token đầu tiên của câu trả lời xuất hiện trên màn hình.
- **E2E Latency**: Tổng thời gian từ khi user gửi câu hỏi đến khi toàn bộ câu trả lời được hiển thị.
- **Post_Response_Task**: Tác vụ chạy sau khi user đã nhận được câu trả lời (update rolling summary, extract user memories).
- **Connection_Pool**: Tập hợp các kết nối PostgreSQL sync (psycopg) được tái sử dụng thay vì tạo mới mỗi lần.
- **Streaming**: Kỹ thuật hiển thị từng token LLM ngay khi được sinh ra, thay vì chờ toàn bộ câu trả lời. Không dùng `time.sleep()`.
- **Prompt_Fusion**: Kỹ thuật gộp logic query rewriting vào main generation prompt, giảm số LLM calls từ 2 xuống còn 1 cho phần critical path.
- **LLM_Semaphore**: Cơ chế kiểm soát số lượng LLM calls đồng thời tối đa, tránh GPU thrash khi nhiều users cùng gọi Ollama.
- **Query_Cache**: Cache lưu kết quả câu trả lời theo hash(query + context_fingerprint) với TTL configurable.
- **Embedding_Cache**: Cache in-memory LRU lưu embedding vector theo hash(text), tránh gọi Ollama lại cho text đã embed.
- **Benchmark**: Đo lường thời gian thực tế của từng bước trong pipeline để xác định bottleneck.
- **QPS_Counter**: Bộ đếm queries per second đơn giản dùng rolling window.
- **HNSW_Index**: Chỉ mục vector `idx_document_chunks_embedding USING hnsw` đã được tạo trong schema hiện tại, dùng cho approximate nearest neighbor search.
- **Max_Loaded_Models**: Số lượng model tối đa Ollama được phép load vào VRAM cùng lúc, cấu hình qua `OLLAMA_MAX_LOADED_MODELS` (mặc định: 1). Giới hạn này tránh VRAM overflow khi nhiều model cùng được load.
- **Fused_Response_Format**: Định dạng JSON output của LLM khi Prompt Fusion được bật: `{"answer": "...", "rewritten_query": "...", "confidence": 0.92}`. Field `confidence` là optional.
- **FIFO_Queue**: Hàng đợi theo thứ tự First-In-First-Out — request đến trước được xử lý trước. Áp dụng cho LLM_Semaphore queue.
- **Cache_Key**: Khóa dùng để tra cứu và lưu cache. Với Query_Cache: `hash(normalized_query + str(top_k) + str(sorted_filters) + model_version)`. Với Embedding_Cache: `hash(normalized_text)`.
- **Text_Normalization**: Quy trình chuẩn hóa text trước khi hash: lowercase → strip whitespace đầu/cuối → collapse nhiều khoảng trắng liên tiếp thành một khoảng trắng duy nhất.

---

## Requirements

### Requirement 1: Đo lường và quan sát hiệu năng (Performance Benchmarking)

**User Story:** Là một developer, tôi muốn đo được thời gian thực tế của từng bước trong pipeline và theo dõi throughput đơn giản, để tôi có thể xác định đúng bottleneck và đánh giá hiệu quả của từng tối ưu hóa.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL ghi lại thời gian thực thi (tính bằng milliseconds) của từng bước: embedding, hybrid search, LLM generation, post-response tasks.
2. WHEN a query is processed, THE RAG_Pipeline SHALL trả về timing breakdown trong response dict dưới key `"timing"`.
3. THE RAG_Pipeline SHALL tính và ghi lại TTFT riêng biệt với E2E Latency.
4. WHEN timing data is collected, THE RAG_Pipeline SHALL log timing breakdown ở mức DEBUG để không làm ô nhiễm production logs.
5. IF a pipeline step exceeds 5000ms, THEN THE RAG_Pipeline SHALL log một WARNING với tên bước và thời gian thực tế.
6. THE QPS_Counter SHALL đếm số queries được xử lý trong rolling window 60 giây và expose giá trị đó qua `get_stats()`.
7. THE RAG_Pipeline SHALL đo và ghi lại `queue_wait_time` — thời gian request phải chờ trong LLM_Semaphore queue trước khi được xử lý.
8. WHEN timing data is collected, THE RAG_Pipeline SHALL include `queue_wait_ms` trong timing breakdown dict để phân biệt thời gian chờ queue với thời gian xử lý LLM thực tế.

---

### Requirement 2: Giữ model trong VRAM với thời gian có giới hạn (Adaptive Keep-Alive)

**User Story:** Là một người dùng, tôi muốn chatbot phản hồi nhanh hơn từ câu hỏi thứ hai trở đi mà không gây OOM khi hệ thống cần load thêm model khác, để tôi có trải nghiệm nhanh và ổn định.

#### Acceptance Criteria

1. THE LLMManager SHALL khởi tạo OllamaLLM với `keep_alive=300` (5 phút) làm giá trị mặc định để giữ model trong VRAM có giới hạn thời gian.
2. THE EmbeddingManager SHALL khởi tạo OllamaEmbeddings với `keep_alive=300` (5 phút) làm giá trị mặc định.
3. WHERE `OLLAMA_KEEP_ALIVE` environment variable is set, THE LLMManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `300`.
4. WHERE `OLLAMA_KEEP_ALIVE` environment variable is set, THE EmbeddingManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `300`.
5. WHEN the application starts, THE RAG_Pipeline SHALL thực hiện một warm-up call để load LLM vào VRAM trước khi nhận query đầu tiên từ user; embedding model SHALL được load on-demand (không preload trong warm-up).
6. IF the warm-up call fails, THEN THE RAG_Pipeline SHALL log một WARNING và tiếp tục khởi động bình thường mà không crash.
7. THE Ollama runtime SHALL được cấu hình với `OLLAMA_MAX_LOADED_MODELS` (giá trị mặc định: 1) để giới hạn số model được load vào VRAM cùng lúc, tránh VRAM overflow.
8. WHERE `OLLAMA_MAX_LOADED_MODELS` environment variable is set, THE RAG_Pipeline SHALL truyền giá trị đó vào cấu hình Ollama thay vì giá trị mặc định `1`.

---

### Requirement 3: Tách post-response tasks ra khỏi critical path (Async Post-Processing)

**User Story:** Là một người dùng, tôi muốn nhận được câu trả lời ngay sau khi LLM sinh xong, để tôi không phải chờ thêm thời gian cho các tác vụ nền như cập nhật summary hay trích xuất memory.

#### Acceptance Criteria

1. WHEN the LLM finishes generating an answer, THE RAG_Pipeline SHALL trả về câu trả lời cho user ngay lập tức mà không chờ rolling summary update hoàn thành.
2. WHEN the LLM finishes generating an answer, THE RAG_Pipeline SHALL trả về câu trả lời cho user ngay lập tức mà không chờ user memory extraction hoàn thành.
3. THE Post_Response_Task executor SHALL chạy rolling summary update trong một background thread riêng biệt sau khi câu trả lời đã được trả về.
4. THE Post_Response_Task executor SHALL chạy user memory extraction trong một background thread riêng biệt sau khi câu trả lời đã được trả về.
5. IF a post-response background task raises an exception, THEN THE Post_Response_Task executor SHALL log lỗi đó ở mức ERROR và không làm crash luồng chính.
6. WHILE a post-response background task is running, THE RAG_Pipeline SHALL không block việc nhận query tiếp theo từ user.
7. THE Post_Response_Task executor SHALL hoàn thành tất cả background tasks trong vòng 60 giây; IF a task exceeds 60 seconds, THEN THE Post_Response_Task executor SHALL cancel task đó và log một WARNING.

---

### Requirement 4: Streaming LLM response (Token Streaming)

**User Story:** Là một người dùng, tôi muốn thấy câu trả lời xuất hiện từng từ ngay khi LLM đang sinh, để cảm giác chờ đợi giảm đi dù tổng thời gian không đổi.

#### Acceptance Criteria

1. THE LLMManager SHALL hỗ trợ streaming mode trả về từng token ngay khi Ollama sinh ra thay vì chờ toàn bộ response.
2. WHEN streaming mode is enabled, THE RAG_Pipeline SHALL truyền từng token lên Streamlit UI ngay khi nhận được từ LLMManager.
3. WHEN streaming mode is enabled, THE Streamlit_UI SHALL hiển thị từng token mới mà không dùng `time.sleep()` giữa các ký tự.
4. WHERE `STREAMING_ENABLED` is set to `false`, THE RAG_Pipeline SHALL sử dụng non-streaming mode như hiện tại để đảm bảo backward compatibility.
5. IF the streaming connection is interrupted, THEN THE LLMManager SHALL log lỗi và trả về phần response đã nhận được cho đến thời điểm đó.

---

### Requirement 5: PostgreSQL Connection Pooling (Sync)

**User Story:** Là một developer, tôi muốn hệ thống tái sử dụng kết nối PostgreSQL thay vì tạo mới mỗi lần query, để giảm overhead TCP handshake và authentication mà không cần thay đổi sang asyncpg.

#### Acceptance Criteria

1. THE VectorStoreManager SHALL duy trì một psycopg connection pool (sync) với tối thiểu 2 và tối đa 10 kết nối PostgreSQL.
2. WHEN a database query is needed, THE VectorStoreManager SHALL lấy kết nối từ pool thay vì tạo kết nối mới.
3. WHEN a database query completes, THE VectorStoreManager SHALL trả kết nối về pool thay vì đóng kết nối.
4. WHERE `POSTGRES_POOL_MIN_SIZE` environment variable is set, THE VectorStoreManager SHALL sử dụng giá trị đó làm kích thước tối thiểu của pool.
5. WHERE `POSTGRES_POOL_MAX_SIZE` environment variable is set, THE VectorStoreManager SHALL sử dụng giá trị đó làm kích thước tối đa của pool.
6. IF all connections in the pool are in use and a new query arrives, THEN THE VectorStoreManager SHALL chờ tối đa 30 giây để có kết nối khả dụng trước khi raise một timeout exception.
7. IF a pooled connection becomes stale or broken, THEN THE VectorStoreManager SHALL tự động thay thế kết nối đó bằng một kết nối mới.

---

### Requirement 6: Tối ưu Hybrid Search (Search Optimization)

**User Story:** Là một developer, tôi muốn hybrid search chỉ fetch đúng số lượng candidates cần thiết và tận dụng HNSW index đã có, để giảm I/O và thời gian xử lý SQL không cần thiết.

#### Acceptance Criteria

1. WHILE MMR is disabled, THE VectorStoreManager SHALL giới hạn số lượng candidates fetch từ database bằng đúng `k` (số kết quả cuối cùng cần trả về) thay vì hardcode 50.
2. WHERE MMR is enabled, THE VectorStoreManager SHALL fetch `mmr_fetch_k` candidates từ database để có đủ pool cho MMR reranking.
3. THE VectorStoreManager SHALL đọc giá trị `k` từ tham số của hàm `similarity_search` thay vì dùng giá trị hardcode trong SQL.
4. WHEN the hybrid search SQL is executed, THE VectorStoreManager SHALL sử dụng `LIMIT %s` với tham số động thay vì `LIMIT 50` hardcode.
5. IF `k` is less than 1, THEN THE VectorStoreManager SHALL raise một ValueError với message mô tả rõ ràng.
6. WHERE metadata filter is provided, THE VectorStoreManager SHALL thêm điều kiện `WHERE metadata @> %s::jsonb` vào SQL query để pre-filter trước khi tính vector distance.
7. THE VectorStoreManager SHALL document rằng index `idx_document_chunks_embedding USING hnsw (embedding vector_cosine_ops)` đã tồn tại trong schema và được sử dụng tự động bởi PostgreSQL cho vector similarity search.
8. THE VectorStoreManager SHALL fetch `k + SEARCH_RESULT_BUFFER` candidates từ database, sau đó trim về `k` sau khi RRF scoring ở application layer; `SEARCH_RESULT_BUFFER` có giá trị mặc định là `5`.
9. WHERE `SEARCH_RESULT_BUFFER` environment variable is set, THE VectorStoreManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `5`.

---

### Requirement 7: Gộp Query Rewrite vào Main LLM Call (Prompt Fusion)

**User Story:** Là một developer, tôi muốn giảm số lần gọi LLM trong critical path từ 2 xuống còn 1, để giảm latency đáng kể mà không mất đi khả năng xử lý từ viết tắt.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL gộp logic mở rộng từ viết tắt (query rewriting) vào main generation prompt thay vì gọi LLM riêng biệt cho bước rewrite.
2. WHEN Prompt_Fusion is enabled, THE RAG_Pipeline SHALL thực hiện chỉ 1 LLM call cho toàn bộ critical path (generation), thay vì 2 LLM calls tuần tự (rewrite + generation).
3. THE Fused_Prompt SHALL hướng dẫn LLM đồng thời mở rộng từ viết tắt trong câu hỏi và sinh câu trả lời dựa trên ngữ cảnh tài liệu trong một lần inference duy nhất.
4. WHERE `PROMPT_FUSION_ENABLED` is set to `false`, THE RAG_Pipeline SHALL sử dụng lại flow query rewrite riêng biệt như hiện tại để đảm bảo backward compatibility.
5. IF Prompt_Fusion produces an empty or invalid response, THEN THE RAG_Pipeline SHALL fallback về non-fused flow và log một WARNING.
6. WHEN Prompt_Fusion is enabled, THE RAG_Pipeline SHALL vẫn trả về `rewritten_query` trong response dict (có thể là `null` nếu không có từ viết tắt cần mở rộng).
7. WHEN Prompt_Fusion is enabled, THE LLM SHALL trả về output theo Fused_Response_Format: `{"answer": "...", "rewritten_query": "...", "confidence": 0.92}`.
8. WHEN Prompt_Fusion is enabled, THE RAG_Pipeline SHALL parse JSON response từ fused prompt để trích xuất `answer` và `rewritten_query`.
9. IF JSON parse fails (LLM output không đúng Fused_Response_Format), THEN THE RAG_Pipeline SHALL fallback về raw answer text, log một WARNING, và không crash pipeline.
10. THE RAG_Pipeline SHALL xử lý field `confidence` trong Fused_Response_Format là optional; IF `confidence` không có trong response, THEN THE RAG_Pipeline SHALL gán giá trị `null` cho field đó.

---

### Requirement 8: Kiểm soát đồng thời LLM calls (LLM Concurrency Control)

**User Story:** Là một developer, tôi muốn giới hạn số lượng LLM calls đồng thời đến Ollama, để tránh GPU thrash khi nhiều Streamlit users cùng gửi câu hỏi và giữ latency ổn định.

#### Acceptance Criteria

1. THE LLMManager SHALL sử dụng một Semaphore để giới hạn số lượng LLM calls đồng thời tối đa là `max_concurrent_llm_calls` (giá trị mặc định: 2).
2. WHEN the number of concurrent LLM calls reaches `max_concurrent_llm_calls`, THE LLM_Semaphore SHALL queue các request tiếp theo thay vì reject ngay lập tức.
3. WHEN a queued LLM request waits longer than 120 giây, THE LLM_Semaphore SHALL raise một timeout exception và log một WARNING với thời gian chờ thực tế.
4. WHERE `LLM_MAX_CONCURRENT_CALLS` environment variable is set, THE LLMManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `2`.
5. IF `LLM_MAX_CONCURRENT_CALLS` is set to a value less than 1, THEN THE LLMManager SHALL log một WARNING và sử dụng giá trị mặc định `2`.
6. WHEN a LLM call completes or raises an exception, THE LLM_Semaphore SHALL release slot đó để request tiếp theo trong queue có thể được xử lý.
7. THE LLM_Semaphore SHALL giới hạn queue size tối đa là `LLM_MAX_QUEUE_SIZE` (giá trị mặc định: 10); queue discipline là FIFO — request đến trước được xử lý trước.
8. IF the queue is full (đã đạt `LLM_MAX_QUEUE_SIZE`) AND a new request arrives, THEN THE LLM_Semaphore SHALL reject request đó ngay lập tức với một lỗi rõ ràng thay vì để queue phình ra vô hạn.
9. WHERE `LLM_MAX_QUEUE_SIZE` environment variable is set, THE LLMManager SHALL sử dụng giá trị đó thay vì giá trị mặc định `10`.

---

### Requirement 9: Basic Caching (Query Cache và Embedding Cache)

**User Story:** Là một người dùng, tôi muốn các câu hỏi lặp lại nhận được câu trả lời gần như ngay lập tức, để hệ thống không lãng phí tài nguyên tính toán lại những gì đã biết.

#### Acceptance Criteria

1. THE Query_Cache SHALL lưu câu trả lời theo Cache_Key là `hash(normalized_query + str(top_k) + str(sorted_filters) + model_version)` với TTL configurable qua `CACHE_TTL_SECONDS` (giá trị mặc định: 300 giây).
2. WHEN a query matches a cached entry and the cache entry has not expired, THE RAG_Pipeline SHALL trả về cached answer mà không gọi LLM hay database.
3. THE Embedding_Cache SHALL lưu embedding vector theo key là `hash(normalized_text)` trong in-memory LRU cache với dung lượng tối đa configurable qua `EMBEDDING_CACHE_MAX_SIZE` (giá trị mặc định: 1000 entries).
4. WHEN an embedding is requested for a text that exists in Embedding_Cache, THE EmbeddingManager SHALL trả về cached vector mà không gọi Ollama.
5. WHERE `QUERY_CACHE_ENABLED` is set to `false`, THE RAG_Pipeline SHALL bỏ qua Query_Cache và luôn xử lý query từ đầu.
6. WHERE `EMBEDDING_CACHE_ENABLED` is set to `false`, THE EmbeddingManager SHALL bỏ qua Embedding_Cache và luôn gọi Ollama để embed.
7. IF a cached entry expires (TTL exceeded), THEN THE Query_Cache SHALL xóa entry đó và xử lý query từ đầu như một query mới.
8. THE Query_Cache SHALL expose số lượng cache hits và cache misses qua `get_stats()` để developer có thể đánh giá hiệu quả cache.
9. THE Query_Cache SHALL áp dụng Text_Normalization (lowercase → strip → collapse whitespace) lên query trước khi tính Cache_Key để đảm bảo các query chỉ khác nhau về khoảng trắng hoặc chữ hoa/thường đều trả về cùng cache entry.
10. THE EmbeddingManager SHALL áp dụng Text_Normalization lên text trước khi hash và lookup trong Embedding_Cache.

---

### Requirement 10: Cấu hình tối ưu hóa qua environment variables

**User Story:** Là một developer, tôi muốn bật/tắt từng tối ưu hóa qua environment variables, để tôi có thể kiểm soát và rollback từng thay đổi một cách độc lập.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL đọc `OLLAMA_KEEP_ALIVE` từ environment để cấu hình thời gian giữ model trong VRAM; giá trị mặc định là `300` (giây).
2. THE RAG_Pipeline SHALL đọc `STREAMING_ENABLED` từ environment để bật/tắt token streaming; giá trị mặc định là `true`.
3. THE RAG_Pipeline SHALL đọc `ASYNC_POST_PROCESSING_ENABLED` từ environment để bật/tắt async post-response tasks; giá trị mặc định là `true`.
4. THE RAG_Pipeline SHALL đọc `POSTGRES_POOL_MIN_SIZE` và `POSTGRES_POOL_MAX_SIZE` từ environment để cấu hình connection pool; giá trị mặc định lần lượt là `2` và `10`.
5. THE RAG_Pipeline SHALL đọc `PROMPT_FUSION_ENABLED` từ environment để bật/tắt Prompt Fusion; giá trị mặc định là `true`.
6. THE RAG_Pipeline SHALL đọc `LLM_MAX_CONCURRENT_CALLS` từ environment để cấu hình LLM Semaphore; giá trị mặc định là `2`.
7. THE RAG_Pipeline SHALL đọc `QUERY_CACHE_ENABLED`, `EMBEDDING_CACHE_ENABLED`, `CACHE_TTL_SECONDS`, và `EMBEDDING_CACHE_MAX_SIZE` từ environment để cấu hình caching; giá trị mặc định lần lượt là `true`, `true`, `300`, và `1000`.
8. THE RAG_Pipeline SHALL đọc `OLLAMA_MAX_LOADED_MODELS` từ environment để cấu hình số model tối đa Ollama load vào VRAM cùng lúc; giá trị mặc định là `1`.
9. THE RAG_Pipeline SHALL đọc `LLM_MAX_QUEUE_SIZE` từ environment để cấu hình kích thước tối đa của LLM Semaphore queue; giá trị mặc định là `10`.
10. THE RAG_Pipeline SHALL đọc `SEARCH_RESULT_BUFFER` từ environment để cấu hình số candidates bổ sung fetch thêm ngoài `k` trong hybrid search; giá trị mặc định là `5`.
11. THE `.env.example` file SHALL được cập nhật với tất cả các environment variables mới kèm giá trị mặc định và comment giải thích.
12. IF an environment variable has an invalid value (ví dụ: `POSTGRES_POOL_MAX_SIZE=abc`), THEN THE RAG_Pipeline SHALL log một WARNING và sử dụng giá trị mặc định thay vì crash.
