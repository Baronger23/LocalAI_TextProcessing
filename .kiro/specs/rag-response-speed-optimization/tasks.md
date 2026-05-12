# Kế hoạch triển khai: RAG Response Speed Optimization

## Tổng quan

Tối ưu hóa pipeline RAG để giảm perceived latency (TTFT) và actual latency (E2E) thông qua 8 nhóm cải tiến: Adaptive Keep-Alive, Token Streaming, Async Post-Processing, Connection Pooling, Dynamic LIMIT Search, Prompt Fusion, LLM Concurrency Control, và Basic Caching. Triển khai theo thứ tự từ nền tảng (config, data models) đến từng component, sau đó wire toàn bộ vào RAGPipeline và Streamlit UI.

## Tasks

- [x] 1. Thêm environment variables và cấu hình mới vào settings.py
  - Thêm các hằng số mới vào `src/config/settings.py`: `OLLAMA_KEEP_ALIVE`, `OLLAMA_MAX_LOADED_MODELS`, `STREAMING_ENABLED`, `ASYNC_POST_PROCESSING_ENABLED`, `POSTGRES_POOL_MIN_SIZE`, `POSTGRES_POOL_MAX_SIZE`, `PROMPT_FUSION_ENABLED`, `LLM_MAX_CONCURRENT_CALLS`, `LLM_MAX_QUEUE_SIZE`, `QUERY_CACHE_ENABLED`, `EMBEDDING_CACHE_ENABLED`, `CACHE_TTL_SECONDS`, `EMBEDDING_CACHE_MAX_SIZE`, `SEARCH_RESULT_BUFFER`
  - Mỗi biến đọc từ `os.getenv()` với giá trị mặc định theo design
  - Xử lý invalid env var: log WARNING, dùng default (không crash)
  - Cập nhật `.env.example` với tất cả biến mới kèm comment giải thích
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11, 10.12_

- [x] 2. Tạo data models và custom exceptions
  - [x] 2.1 Tạo file `src/rag/models.py` với các dataclass: `TimingBreakdown`, `FusedLLMResponse`, `CacheEntry`
    - `TimingBreakdown`: các field float với default 0.0, method `to_dict()`
    - `FusedLLMResponse`: field `answer`, `rewritten_query`, `confidence`; classmethods `from_json()` (parse JSON, fallback về raw text nếu fail) và `from_raw_text()`
    - `CacheEntry`: field `value` và `expire_at: float`, method `is_expired()`
    - _Requirements: 7.7, 7.8, 7.9, 7.10_

  - [x] 2.2 Tạo file `src/rag/exceptions.py` với custom exceptions: `LLMTimeoutError`, `LLMQueueFullError`, `PoolTimeoutError`
    - Mỗi exception có docstring mô tả rõ khi nào được raise
    - _Requirements: 8.3, 8.8, 5.6_

  - [ ]* 2.3 Viết unit tests cho `FusedLLMResponse.from_json()`
    - Test parse JSON hợp lệ đầy đủ fields
    - Test parse JSON thiếu field `confidence` → `confidence=None`
    - Test parse JSON invalid → fallback về raw text, không raise exception
    - _Requirements: 7.8, 7.9, 7.10_

- [x] 3. Triển khai PerformanceBenchmark
  - [x] 3.1 Tạo file `src/rag/benchmark.py` với class `PerformanceBenchmark`
    - `__init__`: khởi tạo `deque` rolling window với `window_seconds=60`
    - Context manager `measure(step_name)`: đo thời gian, log WARNING nếu > 5000ms, log DEBUG cho mọi timing
    - Method `record_query()`: thêm timestamp vào rolling window
    - Method `get_qps()`: đếm queries trong 60s gần nhất
    - Method `build_timing_dict(timings)`: tạo dict với các timing keys chuẩn
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [ ]* 3.2 Viết property test cho QPS counter (Property 3)
    - **Property 3: QPS counter phản ánh đúng số queries trong rolling window**
    - **Validates: Requirements 1.6**
    - Dùng `hypothesis` với strategy `st.integers(1, 100)` cho N queries

  - [ ]* 3.3 Viết property test cho timing dict completeness (Property 1)
    - **Property 1: Timing dict luôn đầy đủ**
    - **Validates: Requirements 1.1, 1.2, 1.7, 1.8**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho query

- [x] 4. Triển khai QueryCache
  - [x] 4.1 Tạo file `src/rag/query_cache.py` với class `QueryCache`
    - `__init__`: khởi tạo `_store: dict`, `_lock: threading.Lock`, counters `_hits`, `_misses`
    - Method `make_key(query, top_k, filters, model_version)`: normalize text → hash SHA256
    - Static method `normalize_text(text)`: lowercase → strip → collapse whitespace
    - Method `get(key)`: trả về `None` nếu miss hoặc expired (xóa entry expired)
    - Method `set(key, value)`: lưu với TTL
    - Method `get_stats()`: trả về `{"hits": N, "misses": N}`
    - Khi `enabled=False`: `get()` luôn trả về `None`, `set()` là no-op
    - _Requirements: 9.1, 9.5, 9.7, 9.8, 9.9_

  - [ ]* 4.2 Viết property test cho cache stats accuracy (Property 15)
    - **Property 15: Cache stats phản ánh đúng hits và misses**
    - **Validates: Requirements 9.8**
    - Dùng `hypothesis` với strategy `st.lists(st.text())` cho query sequence

  - [ ]* 4.3 Viết property test cho text normalization cache key (Property 16)
    - **Property 16: Text normalization đảm bảo cache key nhất quán**
    - **Validates: Requirements 9.9, 9.10**
    - Dùng `hypothesis` với strategy `st.text()` + whitespace/case variants

  - [ ]* 4.4 Viết unit tests cho QueryCache
    - Test TTL expiry xóa entry và xử lý như query mới
    - Test cache disabled khi `QUERY_CACHE_ENABLED=false`
    - Test thread-safety với concurrent reads/writes
    - _Requirements: 9.5, 9.7_

- [x] 5. Cập nhật EmbeddingManager với keep_alive và embedding cache
  - [x] 5.1 Cập nhật `src/embeddings/embedding_manager.py`
    - Thêm params `keep_alive: int = OLLAMA_KEEP_ALIVE` và `cache_enabled: bool = EMBEDDING_CACHE_ENABLED`, `cache_max_size: int = EMBEDDING_CACHE_MAX_SIZE`
    - Khởi tạo `OllamaEmbeddings` với `keep_alive=keep_alive` thay vì hardcode `0`
    - Implement LRU cache thread-safe dùng `collections.OrderedDict` + `threading.Lock`
    - Method `_normalize_text(text)`: lowercase → strip → collapse whitespace
    - Method `_cache_key(normalized_text)`: SHA256 hash, lấy 16 ký tự đầu
    - Cập nhật `embed_query()`: lookup cache trước, nếu miss thì gọi Ollama rồi lưu cache
    - Khi `cache_enabled=False`: bỏ qua cache, luôn gọi Ollama
    - _Requirements: 2.2, 2.4, 9.3, 9.4, 9.6, 9.10_

  - [ ]* 5.2 Viết property test cho keep-alive env var override (Property 4)
    - **Property 4: Keep-alive env var override**
    - **Validates: Requirements 2.3, 2.4**
    - Dùng `hypothesis` với strategy `st.integers(0, 3600)` cho keep_alive value

  - [ ]* 5.3 Viết property test cho embedding cache hit (Property 14)
    - **Property 14: Embedding cache hit tránh gọi Ollama**
    - **Validates: Requirements 9.3, 9.4**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho text

  - [ ]* 5.4 Viết unit tests cho EmbeddingManager
    - Test default `keep_alive=300` khi không có env var
    - Test LRU cache eviction khi đạt max size
    - Test cache disabled khi `EMBEDDING_CACHE_ENABLED=false`
    - _Requirements: 2.2, 9.6_

- [x] 6. Cập nhật LLMManager với keep_alive, semaphore, streaming, và prompt fusion
  - [x] 6.1 Cập nhật `src/llm/llm_manager.py` — keep_alive và semaphore
    - Thêm params: `keep_alive: int = OLLAMA_KEEP_ALIVE`, `max_concurrent_calls: int = LLM_MAX_CONCURRENT_CALLS`, `max_queue_size: int = LLM_MAX_QUEUE_SIZE`
    - Khởi tạo `OllamaLLM` với `keep_alive=keep_alive`
    - Implement `threading.Semaphore(max_concurrent_calls)` + `_queue_lock` + `_active_count` + `_queue_count`
    - Validate `max_concurrent_calls < 1`: log WARNING, dùng default 2
    - Cập nhật `invoke()`: acquire semaphore với timeout 120s, đo `queue_wait_time`, raise `LLMTimeoutError` nếu timeout, raise `LLMQueueFullError` nếu queue đầy, release semaphore trong `finally`
    - _Requirements: 2.1, 2.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

  - [x] 6.2 Thêm streaming support vào LLMManager
    - Thêm method `stream(prompt)`: generator yield từng token từ Ollama với semaphore control
    - Xử lý streaming connection bị ngắt: log ERROR, trả về phần đã nhận
    - _Requirements: 4.1, 4.5_

  - [x] 6.3 Thêm `generate_response_fused()` vào LLMManager
    - Method nhận `query, context, system_prompt, chat_history, stream=True`
    - Xây dựng fused prompt hướng dẫn LLM đồng thời rewrite + generate theo `Fused_Response_Format`
    - Gọi LLM 1 lần duy nhất (không phải 2 lần)
    - Parse JSON response dùng `FusedLLMResponse.from_json()`; nếu fail: log WARNING, fallback `from_raw_text()`
    - Trả về `dict` với keys `answer`, `rewritten_query`, `confidence`
    - _Requirements: 7.1, 7.2, 7.3, 7.7, 7.8, 7.9_

  - [ ]* 6.4 Viết property test cho semaphore always released (Property 11)
    - **Property 11: Semaphore luôn được release sau mỗi LLM call**
    - **Validates: Requirements 8.6**
    - Dùng `hypothesis` với strategy `st.booleans()` cho success/fail scenario

  - [ ]* 6.5 Viết property test cho semaphore FIFO order (Property 12)
    - **Property 12: Semaphore queue theo thứ tự FIFO**
    - **Validates: Requirements 8.7**
    - Dùng `hypothesis` với strategy `st.lists(st.integers())` cho request sequence

  - [ ]* 6.6 Viết property test cho prompt fusion single LLM call (Property 8)
    - **Property 8: Prompt Fusion giảm xuống còn 1 LLM call**
    - **Validates: Requirements 7.1, 7.2**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho query

  - [ ]* 6.7 Viết property test cho fused response parsing (Property 9)
    - **Property 9: Fused response parsing xử lý đúng mọi JSON hợp lệ**
    - **Validates: Requirements 7.8, 7.10**
    - Dùng `hypothesis` với strategy `st.fixed_dictionaries({"answer": st.text(), "rewritten_query": st.text()})`

  - [ ]* 6.8 Viết unit tests cho LLMManager
    - Test default `keep_alive=300`
    - Test semaphore reject khi queue đầy (`LLMQueueFullError`)
    - Test semaphore timeout sau 120s (`LLMTimeoutError`)
    - Test fused response JSON parse thành công
    - Test fused response fallback khi JSON invalid
    - Test streaming trả về generator
    - _Requirements: 2.1, 8.3, 8.5, 8.8, 7.8, 7.9, 4.1_

- [x] 7. Checkpoint — Kiểm tra các components độc lập
  - Đảm bảo tất cả tests pass cho `QueryCache`, `EmbeddingManager`, `LLMManager`, `PerformanceBenchmark`
  - Đảm bảo không có import errors trong các module mới
  - Hỏi user nếu có vấn đề cần làm rõ.

- [x] 8. Cập nhật VectorStoreManager với connection pool và dynamic LIMIT
  - [x] 8.1 Thêm connection pool vào `src/rag/vector_store.py`
    - Thêm params: `pool_min_size: int = POSTGRES_POOL_MIN_SIZE`, `pool_max_size: int = POSTGRES_POOL_MAX_SIZE`
    - Thêm `_pool: Optional[psycopg.pool.ConnectionPool]` attribute
    - Implement `_get_pool()`: lazy-init `psycopg.pool.ConnectionPool` với `min_size`, `max_size`, `timeout=30`
    - Cập nhật `_postgres_similarity_search()` và các methods khác dùng pool thay vì `_get_postgres_connection()`
    - Xử lý pool timeout: raise `PoolTimeoutError`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 8.2 Cập nhật dynamic LIMIT trong `_postgres_similarity_search()`
    - Thêm param `search_result_buffer: int = SEARCH_RESULT_BUFFER`
    - Thêm params `mmr_enabled: bool = False`, `mmr_fetch_k: int = MMR_FETCH_K`
    - Logic: nếu `mmr_enabled=True` → `fetch_limit = mmr_fetch_k`; nếu `False` → `fetch_limit = k + search_result_buffer`
    - Thay `LIMIT 50` hardcode trong SQL bằng `LIMIT %s` với tham số động
    - Validate `k < 1`: raise `ValueError` với message rõ ràng
    - Document HNSW index đã tồn tại trong docstring
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 6.9_

  - [ ]* 8.3 Viết property test cho dynamic LIMIT (Property 6)
    - **Property 6: Dynamic LIMIT trong hybrid search**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.8**
    - Dùng `hypothesis` với strategy `st.integers(1, 20)` cho k

  - [ ]* 8.4 Viết property test cho metadata filter (Property 7)
    - **Property 7: Metadata filter pre-filters kết quả**
    - **Validates: Requirements 6.6**
    - Dùng `hypothesis` với strategy `st.dictionaries(st.text(), st.text())`

  - [ ]* 8.5 Viết property test cho connection pool size (Property 17)
    - **Property 17: Connection pool size tuân theo env var configuration**
    - **Validates: Requirements 5.4, 5.5**
    - Dùng `hypothesis` với strategy `st.integers(1, 5)` cho min, `st.integers(5, 20)` cho max

  - [ ]* 8.6 Viết unit tests cho VectorStoreManager
    - Test connection pool khởi tạo với đúng min/max size
    - Test `k < 1` raise `ValueError`
    - Test dynamic LIMIT với MMR disabled
    - Test dynamic LIMIT với MMR enabled
    - _Requirements: 5.1, 6.1, 6.2, 6.5_

- [x] 9. Triển khai PostResponseTaskExecutor
  - [x] 9.1 Tạo file `src/rag/post_response_executor.py` với class `PostResponseTaskExecutor`
    - `__init__`: khởi tạo `ThreadPoolExecutor`, `timeout_seconds=60`
    - Method `submit(fn, *args, task_name, **kwargs)`: submit task vào thread pool
    - Bắt exception trong background task: log ERROR, không crash main thread
    - Cancel task nếu vượt quá `timeout_seconds`: log WARNING
    - _Requirements: 3.3, 3.4, 3.5, 3.7_

  - [ ]* 9.2 Viết unit tests cho PostResponseTaskExecutor
    - Test exception trong background task không crash main thread
    - Test task timeout sau 60s bị cancel
    - _Requirements: 3.5, 3.7_

- [x] 10. Cập nhật RAGPipeline — wire tất cả components
  - [x] 10.1 Cập nhật constructor `RAGPipeline.__init__()`
    - Thêm params: `query_cache`, `benchmark`, `post_task_executor`, `prompt_fusion_enabled`, `streaming_enabled`, `async_post_processing_enabled`
    - Khởi tạo các components mới nếu không được inject
    - _Requirements: 10.1–10.10_

  - [x] 10.2 Thêm method `warmup()` vào RAGPipeline
    - Gọi LLM với prompt ngắn để load model vào VRAM
    - Nếu fail: log WARNING, không crash
    - Embedding model KHÔNG preload trong warmup (load on-demand)
    - _Requirements: 2.5, 2.6_

  - [x] 10.3 Cập nhật method `query()` với đầy đủ tối ưu hóa
    - Bước 1: Cache lookup — nếu hit, trả về ngay
    - Bước 2: Embed query (với benchmark `embedding_ms`)
    - Bước 3: Hybrid search với dynamic LIMIT (với benchmark `search_ms`)
    - Bước 4: LLM generation — nếu `prompt_fusion_enabled=True` dùng `generate_response_fused()`, nếu `False` dùng flow cũ (với benchmark `llm_ms`, `queue_wait_ms`)
    - Bước 5: Lưu cache
    - Bước 6: Submit post-response tasks vào background (nếu `async_post_processing_enabled=True`)
    - Trả về dict với keys: `answer`, `sources`, `context`, `rewritten_query`, `timing`
    - _Requirements: 1.2, 3.1, 3.2, 3.6, 7.4, 7.5, 7.6, 9.1, 9.2_

  - [x] 10.4 Thêm method `query_stream()` vào RAGPipeline
    - Generator yield từng token từ LLM
    - Tích hợp cache lookup trước khi stream
    - Đo TTFT (thời gian đến token đầu tiên)
    - _Requirements: 4.1, 4.2, 1.3_

  - [ ]* 10.5 Viết property test cho timing dict completeness (Property 1)
    - **Property 1: Timing dict luôn đầy đủ**
    - **Validates: Requirements 1.1, 1.2, 1.7, 1.8**
    - Dùng `hypothesis` với strategy `st.text(min_size=1, max_size=200)` cho query

  - [ ]* 10.6 Viết property test cho TTFT <= E2E (Property 2)
    - **Property 2: TTFT luôn nhỏ hơn hoặc bằng E2E Latency**
    - **Validates: Requirements 1.3**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho query

  - [ ]* 10.7 Viết property test cho non-blocking response (Property 5)
    - **Property 5: Response được trả về trước khi background tasks hoàn thành**
    - **Validates: Requirements 3.1, 3.2, 3.6**
    - Dùng `hypothesis` với strategy `st.integers(1, 10)` cho task delay (giây)

  - [ ]* 10.8 Viết property test cho query cache hit (Property 13)
    - **Property 13: Query cache hit tránh gọi LLM**
    - **Validates: Requirements 9.1, 9.2**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho query

  - [ ]* 10.9 Viết property test cho rewritten_query in response (Property 10)
    - **Property 10: Response dict luôn có rewritten_query khi Prompt Fusion enabled**
    - **Validates: Requirements 7.6**
    - Dùng `hypothesis` với strategy `st.text(min_size=1)` cho query

  - [ ]* 10.10 Viết unit tests cho RAGPipeline
    - Test warm-up fail không crash pipeline
    - Test Prompt Fusion disabled dùng 2 LLM calls
    - Test cache hit trả về ngay không gọi LLM
    - _Requirements: 2.5, 2.6, 7.4, 9.2_

- [x] 11. Cập nhật Streamlit UI để hỗ trợ token streaming
  - [x] 11.1 Cập nhật `app.py` — thay typing effect bằng streaming thực
    - Thay vòng lặp `time.sleep(0.008)` bằng `rag.query_stream()` khi `STREAMING_ENABLED=True`
    - Dùng `st.write_stream()` hoặc `message_placeholder.markdown()` để hiển thị từng token
    - Khi `STREAMING_ENABLED=False`: giữ nguyên flow `rag.query()` hiện tại
    - _Requirements: 4.2, 4.3, 4.4_

  - [x] 11.2 Cập nhật `app.py` — gọi `rag.warmup()` khi khởi động
    - Gọi `warmup()` trong `init_rag()` sau khi khởi tạo `RAGPipeline`
    - _Requirements: 2.5_

  - [ ]* 11.3 Viết unit tests cho Streamlit UI integration
    - Test streaming mode không dùng `time.sleep()`
    - Test fallback về non-streaming khi `STREAMING_ENABLED=False`
    - _Requirements: 4.3, 4.4_

- [x] 12. Checkpoint cuối — Đảm bảo toàn bộ hệ thống hoạt động
  - Đảm bảo tất cả unit tests và property tests pass
  - Kiểm tra không có regression trong flow hiện tại
  - Hỏi user nếu có vấn đề cần làm rõ.

## Ghi chú

- Tasks đánh dấu `*` là optional và có thể bỏ qua để triển khai MVP nhanh hơn
- Mỗi task tham chiếu đến requirements cụ thể để đảm bảo traceability
- Checkpoints tại task 7 và 12 để validate tiến độ
- Property tests dùng thư viện `hypothesis` với tối thiểu 100 iterations mỗi test
- Thứ tự triển khai: config → data models → cache → embedding → LLM → vector store → executor → pipeline → UI
