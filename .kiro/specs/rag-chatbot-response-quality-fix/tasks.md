# Implementation Plan

- [x] 1. Write bug condition exploration tests (BEFORE implementing fix)
  - **Property 1: Bug Condition** - Fused Response Cleanup & Semaphore Leak
  - **CRITICAL**: Các test này PHẢI FAIL trên code chưa fix — failure xác nhận bug tồn tại
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples chứng minh bug tồn tại, hiểu root cause
  - **Scoped PBT Approach**: Scope property đến các concrete failing cases để đảm bảo reproducibility

  **Bug 1 — Fused Response Cleanup:**
  - Test case 1a — Breadcrumb-only output: Mock LLM trả về `"Chương 1: Phần I > Điều 3"` → `FusedLLMResponse.from_raw_text()` hiện tại trả về breadcrumb nguyên xi làm answer
    - `isBugCondition_Bug1(X)` = True vì `isOnlyBreadcrumb("Chương 1: Phần I > Điều 3")` = True
    - Assert: `result.answer == "Chương 1: Phần I > Điều 3"` (xác nhận bug — answer là breadcrumb)
    - Document counterexample: `from_raw_text("Chương 1: Phần I > Điều 3").answer` = breadcrumb string
  - Test case 1b — JSON fragment output: Mock LLM trả về `'{"answer": "Điều 5", "rewritten_query"'` (truncated JSON)
    - `isBugCondition_Bug1(X)` = True vì `NOT isValidCompleteJSON(raw)` = True
    - `from_json()` parse fail → fallback `from_raw_text()` → answer chứa `{"answer":` JSON syntax
    - Assert: `result.answer` starts with `{` hoặc contains `"answer":` (xác nhận bug)
    - Document counterexample: answer chứa raw JSON fragment
  - Test case 1c — Empty answer in valid JSON: Mock LLM trả về `'{"answer": "", "confidence": 0.5}'`
    - `isBugCondition_Bug1(X)` = True vì `NOT hasNonEmptyAnswerField(raw)` = True
    - `from_json()` fallback về `from_raw_text()` → answer là toàn bộ JSON string
    - Assert: `result.answer` contains `"answer":` (xác nhận bug)
  - Run tests trên UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (xác nhận bug tồn tại)
  - Document tất cả counterexamples tìm được để hiểu root cause

  **Bug 2 — Semaphore Leak:**
  - Test case 2a — Generator abandonment: Tạo generator từ `query_stream()` với `prompt_fusion_enabled=True`, mock `generate_response_fused()` để acquire semaphore, consume 0 tokens, delete generator
    - `isBugCondition_Bug2(X)` = True vì `generator_exhausted = false`
    - Kiểm tra `semaphore._value` trước và sau khi delete generator
    - Assert: `slots_before == slots_after` (sẽ FAIL nếu semaphore bị leak)
    - Document counterexample: `semaphore._value` giảm sau khi generator bị abandon
  - Test case 2b — Exception trong fused path: Mock `llm.invoke()` raise `RuntimeError("unexpected error")`
    - `isBugCondition_Bug2(X)` = True vì `exception_raised = true`
    - Kiểm tra semaphore count trước và sau call
    - Assert: `slots_before == slots_after` (có thể PASS vì `generate_response_fused()` có `try/finally` nội bộ — cần verify)
    - Document kết quả: xác nhận `generate_response_fused()` internal `try/finally` có hoạt động không
  - Run tests trên UNFIXED code
  - **EXPECTED OUTCOME**: Test 2a FAILS (semaphore leak khi generator bị abandon), Test 2b có thể PASS
  - Document counterexamples và xác nhận root cause
  - _Requirements: 1.4, 1.5, 1.6_

  _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Valid JSON Parsing & Non-Fused Stream Behavior
  - **IMPORTANT**: Follow observation-first methodology — observe behavior trên UNFIXED code trước
  - **GOAL**: Capture baseline behavior để đảm bảo fix không gây regression

  **Observe trên UNFIXED code:**
  - Observe: `FusedLLMResponse.from_json('{"answer": "Theo Điều 5, người lao động có quyền nghỉ phép...", "rewritten_query": null, "confidence": 0.9}')` → `answer = "Theo Điều 5, người lao động có quyền nghỉ phép..."`, `rewritten_query = None`, `confidence = 0.9`
  - Observe: `FusedLLMResponse.from_json('```json\n{"answer": "Nội dung đầy đủ...", "rewritten_query": "câu hỏi mở rộng"}\n```')` → code fence được strip, parse thành công
  - Observe: `query_stream()` với `prompt_fusion_enabled=False` → stream tokens trực tiếp, không qua JSON parsing
  - Observe: `query_stream()` với cache hit → yield words từ cached answer, không acquire semaphore

  **Write property-based tests:**
  - Property 2a — Valid JSON preservation: For all valid JSON strings với `answer` field không rỗng và có nội dung thực (không phải breadcrumb), `from_json()` SHALL trả về đúng `answer`, `rewritten_query`, `confidence`
    - Generate: random Vietnamese text làm answer, optional rewritten_query, optional confidence 0.0–1.0
    - Assert: `result.answer == generated_answer`
    - Assert: `result.rewritten_query == generated_rewritten_query`
    - Assert: `result.confidence == generated_confidence`
    - Verify tests PASS trên UNFIXED code
  - Property 2b — Code fence stripping preservation: JSON wrapped trong markdown code fence vẫn được parse đúng
    - Generate: valid JSON wrapped trong ` ```json\n...\n``` `
    - Assert: `result.answer` equals expected answer (không chứa code fence)
    - Verify tests PASS trên UNFIXED code
  - Property 2c — Classic flow preservation: `query_stream()` với `prompt_fusion_enabled=False` không thay đổi
    - Mock `llm_manager.stream()` trả về sequence of tokens
    - Assert: tokens yielded bởi `query_stream()` khớp với mock stream output
    - Verify tests PASS trên UNFIXED code
  - Property 2d — Cache hit preservation: `query_stream()` với cache hit không acquire semaphore
    - Setup: pre-populate cache với answer
    - Assert: `semaphore._value` không thay đổi sau cache hit
    - Assert: yielded tokens khớp với cached answer words
    - Verify tests PASS trên UNFIXED code
  - Property 2e — Semaphore blocking preservation: Với 2 concurrent requests đang giữ semaphore, request thứ 3 bị block đúng cách
    - Setup: `max_concurrent_calls=2`, acquire 2 slots manually
    - Assert: `query_stream()` với `prompt_fusion_enabled=True` raise `LLMTimeoutError` sau timeout (hoặc `LLMQueueFullError` nếu queue full)
    - Verify tests PASS trên UNFIXED code
  - Run tất cả preservation tests trên UNFIXED code
  - **EXPECTED OUTCOME**: Tất cả preservation tests PASS (xác nhận baseline behavior)
  - Mark task complete khi tests được viết, chạy, và pass trên unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 3. Fix Bug 1 — Fused Prompt / JSON Parsing

  - [x] 3.1 Cập nhật `_FUSED_SYSTEM_PROMPT` trong `src/llm/llm_manager.py`
    - Thêm instruction rõ ràng: "Giải thích đầy đủ nội dung của Điều/Khoản đó, không chỉ liệt kê tên hay số hiệu"
    - Thêm instruction: "Trường `answer` phải là câu trả lời hoàn chỉnh bằng tiếng Việt, không phải chỉ mục hay breadcrumb"
    - Nhấn mạnh: "KHÔNG trả về chỉ breadcrumb dạng 'Chương X > Điều Y' — phải giải thích nội dung thực sự"
    - Giữ nguyên cấu trúc JSON format yêu cầu (`answer`, `rewritten_query`, `confidence`)
    - _Bug_Condition: isBugCondition_Bug1(X) where isOnlyBreadcrumb(X.llm_raw_output) = True_
    - _Expected_Behavior: result.answer contains meaningful Vietnamese explanatory content, not just breadcrumb reference_
    - _Preservation: JSON format requirement unchanged, rewritten_query and confidence fields unchanged_
    - _Requirements: 2.3_

  - [x] 3.2 Cải thiện `FusedLLMResponse.from_raw_text()` trong `src/rag/models.py`
    - Thêm cleanup logic: strip code fences (` ```json `, ` ``` `)
    - Loại bỏ JSON fragment patterns: nếu text bắt đầu bằng `{` hoặc chứa `"answer":`, extract phần text có nghĩa hoặc trả về message mặc định
    - Nếu sau cleanup text rỗng hoặc chỉ là JSON syntax, trả về `"Không đủ thông tin để trả lời câu hỏi này."`
    - Giữ nguyên behavior khi input là plain text hợp lệ (không phải JSON, không phải breadcrumb)
    - _Bug_Condition: isBugCondition_Bug1(X) where from_raw_text() receives JSON fragment or code fence_
    - _Expected_Behavior: result.answer does NOT contain raw JSON syntax as primary content_
    - _Preservation: from_raw_text() with plain Vietnamese text returns same result as before_
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Cải thiện `FusedLLMResponse.from_json()` trong `src/rag/models.py`
    - Khi JSON parse thất bại, thử extract answer bằng regex: `"answer"\s*:\s*"([^"]+)"` trước khi fallback về `from_raw_text()`
    - Nếu regex tìm được answer text có nghĩa (len > 10, không phải breadcrumb), dùng extracted text
    - Nếu không tìm được, gọi `from_raw_text()` với cleaned version (đã strip code fence, JSON fragment)
    - Giữ nguyên behavior khi JSON parse thành công (valid JSON path không thay đổi)
    - _Bug_Condition: isBugCondition_Bug1(X) where NOT isValidCompleteJSON(X.llm_raw_output)_
    - _Expected_Behavior: result.answer contains extracted meaningful text, not raw JSON fragment_
    - _Preservation: from_json() with valid complete JSON returns identical result as before_
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify bug condition exploration test (Bug 1) now passes
    - **Property 1: Expected Behavior** - Fused Response Cleanup
    - **IMPORTANT**: Re-run the SAME tests từ task 1 (Bug 1 cases) — do NOT write new tests
    - Test case 1a: `from_raw_text("Chương 1: Phần I > Điều 3").answer` KHÔNG còn là breadcrumb string
    - Test case 1b: `from_json('{"answer": "Điều 5", "rewritten_query"')` KHÔNG còn chứa `"answer":` trong result
    - Test case 1c: `from_json('{"answer": "", "confidence": 0.5}')` trả về message mặc định, không phải JSON string
    - **EXPECTED OUTCOME**: Tất cả Bug 1 exploration tests PASS (xác nhận bug đã được fix)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.5 Verify preservation tests (Bug 1) still pass
    - **Property 2: Preservation** - Valid JSON Parsing Unchanged
    - **IMPORTANT**: Re-run the SAME preservation tests từ task 2 (Property 2a, 2b) — do NOT write new tests
    - Property 2a: Valid JSON với answer đầy đủ vẫn parse đúng
    - Property 2b: Code fence stripping vẫn hoạt động đúng
    - **EXPECTED OUTCOME**: Tất cả preservation tests PASS (không có regression trong valid JSON path)

- [x] 4. Fix Bug 2 — Semaphore Leak trong `query_stream()`

  - [x] 4.1 Bọc fused call trong `try/finally` tại `query_stream()` trong `src/rag/rag_pipeline.py`
    - Tách phần `if self.prompt_fusion_enabled:` thành block có `try/except/finally` rõ ràng
    - Đảm bảo `generate_response_fused()` được gọi trong context mà nếu generator bị abandon, semaphore vẫn được release
    - Thêm `except Exception as exc` để catch unhandled exception types từ fused path (ngoài `LLMQueueFullError`, `LLMTimeoutError`)
    - Log exception với `logger.exception()` trước khi yield error message
    - Giữ nguyên behavior của classic flow (`prompt_fusion_enabled=False`) — không thay đổi gì trong else branch
    - Giữ nguyên behavior của `except (LLMQueueFullError, LLMTimeoutError)` — vẫn yield error message và return
    - _Bug_Condition: isBugCondition_Bug2(X) where generator_exhausted=False OR exception_raised=True_
    - _Expected_Behavior: semaphore.available_slots() after call == semaphore.available_slots() before call_
    - _Preservation: classic flow (prompt_fusion_enabled=False) behavior unchanged; LLMQueueFullError/LLMTimeoutError handling unchanged_
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 4.2 Verify bug condition exploration test (Bug 2) now passes
    - **Property 1: Expected Behavior** - Semaphore Always Released
    - **IMPORTANT**: Re-run the SAME tests từ task 1 (Bug 2 cases) — do NOT write new tests
    - Test case 2a: Sau khi generator bị abandon, `semaphore._value` bằng giá trị trước call
    - Test case 2b: Sau exception trong fused path, `semaphore._value` bằng giá trị trước call
    - **EXPECTED OUTCOME**: Tất cả Bug 2 exploration tests PASS (xác nhận semaphore leak đã được fix)
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 4.3 Verify preservation tests (Bug 2) still pass
    - **Property 2: Preservation** - Non-Fused Stream & Semaphore Blocking Unchanged
    - **IMPORTANT**: Re-run the SAME preservation tests từ task 2 (Property 2c, 2d, 2e) — do NOT write new tests
    - Property 2c: Classic flow streaming không thay đổi
    - Property 2d: Cache hit không acquire semaphore
    - Property 2e: Semaphore blocking đúng khi 2 slots đang bận
    - **EXPECTED OUTCOME**: Tất cả preservation tests PASS (không có regression)

- [x] 5. Checkpoint — Ensure all tests pass
  - Chạy toàn bộ test suite: `pytest tests/ -v`
  - Đảm bảo tất cả exploration tests (Property 1) PASS sau fix
  - Đảm bảo tất cả preservation tests (Property 2) PASS
  - Kiểm tra không có regression trong các test hiện có
  - Nếu có test nào fail, phân tích root cause và fix trước khi tiếp tục
  - Hỏi user nếu có câu hỏi hoặc cần clarification về behavior mong muốn
