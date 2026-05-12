# RAG Chatbot Response Quality Fix — Bugfix Design

## Overview

Hai bug hồi quy xuất hiện sau khi triển khai spec `rag-response-speed-optimization`:

**Bug 1 — Fused Prompt / JSON Parsing** (`src/llm/llm_manager.py`, `src/rag/models.py`):
Model `qwen2.5:7b` thường không tuân thủ JSON format nghiêm ngặt. Khi `FusedLLMResponse.from_json()` parse thất bại, `from_raw_text()` dùng toàn bộ raw output (JSON fragment, breadcrumb) làm answer. Ngoài ra, `_FUSED_SYSTEM_PROMPT` không yêu cầu rõ ràng trả lời đầy đủ nội dung, khiến LLM chỉ trả về breadcrumb/chỉ mục thay vì nội dung thực sự.

**Bug 2 — Semaphore Leak** (`src/rag/rag_pipeline.py`):
Trong `query_stream()` khi `prompt_fusion_enabled=True`, `generate_response_fused()` acquire semaphore bên trong. Nếu generator bị bỏ dở (Streamlit rerun) hoặc exception xảy ra, semaphore không được release, dẫn đến câu hỏi thứ 2 bị block tối đa 120 giây.

Chiến lược fix: tối thiểu, có mục tiêu — chỉ thay đổi đúng những gì cần thiết để không gây regression.

---

## Glossary

- **Bug_Condition (C)**: Điều kiện kích hoạt bug — `isBugCondition_Bug1` hoặc `isBugCondition_Bug2` trả về `true`
- **Property (P)**: Hành vi mong muốn khi bug condition xảy ra — answer sạch (Bug 1) hoặc semaphore được release (Bug 2)
- **Preservation**: Các hành vi hiện tại phải giữ nguyên sau khi fix — classic flow, valid JSON parsing, cache behavior, semaphore blocking đúng
- **`_FUSED_SYSTEM_PROMPT`**: Chuỗi system prompt trong `src/llm/llm_manager.py` hướng dẫn LLM trả về JSON với `answer`, `rewritten_query`, `confidence`
- **`FusedLLMResponse`**: Dataclass trong `src/rag/models.py` parse raw LLM output thành structured response
- **`from_json()`**: Class method của `FusedLLMResponse` — parse JSON, fallback về `from_raw_text()` khi thất bại
- **`from_raw_text()`**: Class method của `FusedLLMResponse` — hiện tại dùng toàn bộ raw text làm answer (cần cải thiện)
- **`generate_response_fused()`**: Method trong `LLMManager` — acquire semaphore, gọi LLM, release semaphore, parse response
- **`query_stream()`**: Method trong `RAGPipeline` — gọi `generate_response_fused()` khi `prompt_fusion_enabled=True`, không có `try/finally` bao quanh
- **Semaphore Leak**: Trạng thái semaphore bị acquire nhưng không được release, làm cạn kiệt slot cho các request tiếp theo
- **Breadcrumb**: Chuỗi phân cấp dạng `[Tài liệu] > [Chương] > [Điều]` trong metadata tài liệu, không phải nội dung thực sự

---

## Bug Details

### Bug 1 — Fused Prompt / JSON Parsing

Bug xảy ra khi `PROMPT_FUSION_ENABLED=true` và model trả về output không đúng JSON format hoặc chỉ là breadcrumb. `FusedLLMResponse.from_json()` parse thất bại và fallback về `from_raw_text()` — dùng toàn bộ raw text (bao gồm JSON fragment, code fence, breadcrumb) làm answer.

**Formal Specification:**

```
FUNCTION isBugCondition_Bug1(X)
  INPUT: X = (prompt_fusion_enabled: bool, llm_raw_output: str)
  OUTPUT: boolean

  RETURN X.prompt_fusion_enabled = true
    AND (
      NOT isValidCompleteJSON(X.llm_raw_output)
      OR NOT hasNonEmptyAnswerField(X.llm_raw_output)
      OR isOnlyBreadcrumb(X.llm_raw_output)
    )
END FUNCTION

// isValidCompleteJSON: JSON parse thành công VÀ là dict VÀ "answer" không rỗng
// isOnlyBreadcrumb: output chỉ chứa chuỗi dạng "X > Y > Z" không có nội dung thực
```

**Examples:**

- Input: `'{"answer": "", "rewritten_query": null}'` → Bug: answer rỗng, `from_raw_text()` trả về toàn bộ JSON string
- Input: `'```json\n{"answer": "Điều 5", "rewritten_query": null}\n```'` → Hiện tại: code fence được strip đúng, nhưng answer chỉ là breadcrumb "Điều 5"
- Input: `'Chương 1: Phần I > Điều 3'` → Bug: `from_raw_text()` trả về breadcrumb này nguyên xi làm answer
- Input: `'{"answer": "Theo Điều 5, người lao động có quyền...", "confidence": 0.9}'` → Không có bug: JSON hợp lệ, answer có nội dung

### Bug 2 — Semaphore Leak

Bug xảy ra khi `query_stream()` gọi `generate_response_fused()` với `prompt_fusion_enabled=True` và generator bị bỏ dở hoặc exception xảy ra. Semaphore được acquire bên trong `generate_response_fused()` nhưng `query_stream()` không có `try/finally` để đảm bảo release.

**Formal Specification:**

```
FUNCTION isBugCondition_Bug2(X)
  INPUT: X = (prompt_fusion_enabled: bool, generator_exhausted: bool, exception_raised: bool)
  OUTPUT: boolean

  RETURN X.prompt_fusion_enabled = true
    AND (X.generator_exhausted = false OR X.exception_raised = true)
END FUNCTION
```

**Examples:**

- Streamlit rerun giữa chừng: generator bị garbage collected, `finally` trong `generate_response_fused()` không được gọi → semaphore leak
- Exception trong `llm.invoke()`: `generate_response_fused()` có `try/finally` nội bộ → semaphore được release đúng (không phải bug path này)
- Exception trong `query_stream()` SAU khi `generate_response_fused()` trả về: không liên quan đến semaphore
- `LLMQueueFullError` hoặc `LLMTimeoutError` từ `generate_response_fused()`: được catch bởi `except (LLMQueueFullError, LLMTimeoutError)` trong `query_stream()` → không leak

**Lưu ý quan trọng**: Sau khi đọc code kỹ, `generate_response_fused()` đã có `try/finally` nội bộ bao quanh `llm.invoke()`. Bug thực sự xảy ra khi **generator của `query_stream()` bị bỏ dở trước khi `generate_response_fused()` được gọi xong** — cụ thể là khi Streamlit rerun xảy ra và Python garbage collector destroy generator object mà không exhaust nó. Trong trường hợp này, `generate_response_fused()` đang chờ semaphore hoặc đang trong `llm.invoke()` và bị interrupt.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- `PROMPT_FUSION_ENABLED=false`: classic 2-call flow (rewrite + generate riêng biệt) không bị ảnh hưởng
- JSON hợp lệ đầy đủ với field `answer`, `rewritten_query`, `confidence`: vẫn parse và trả về đúng các field đó
- `STREAMING_ENABLED=true` với `PROMPT_FUSION_ENABLED=false`: stream token trực tiếp từ Ollama không qua JSON parsing
- Cache hit: trả về cached answer ngay lập tức, không gọi LLM, không acquire semaphore
- `LLM_MAX_CONCURRENT_CALLS=2` với 2 request đồng thời hợp lệ: block request thứ 3 đúng cách (semaphore behavior đúng)
- `generate_response_fused()` được gọi trực tiếp và thành công: trả về dict với keys `answer`, `rewritten_query`, `confidence`, `queue_wait_ms`
- Warmup thread: acquire và release semaphore đúng cách

**Scope:**

Tất cả inputs không thuộc bug condition (JSON hợp lệ, classic flow, cache hit, non-fused streaming) phải hoàn toàn không bị ảnh hưởng bởi fix này.

---

## Hypothesized Root Cause

### Bug 1 — Fused Prompt / JSON Parsing

1. **Prompt không đủ rõ ràng về nội dung**: `_FUSED_SYSTEM_PROMPT` hiện tại chỉ nói "Trích dẫn đúng Điều/Khoản khi có thể" mà không yêu cầu rõ ràng phải giải thích nội dung chi tiết. Model `qwen2.5:7b` interpret điều này là chỉ cần liệt kê breadcrumb/chỉ mục.

2. **`from_raw_text()` không lọc artifact**: Khi `from_json()` fallback về `from_raw_text()`, toàn bộ raw text (bao gồm JSON fragment như `{"answer":`, code fence như ` ```json `, breadcrumb) được dùng làm answer mà không có bất kỳ cleanup nào.

3. **`from_json()` không extract partial content**: Khi JSON parse thất bại một phần (ví dụ: JSON bị truncate, có trailing text), không có cơ chế extract phần text có nghĩa từ raw output.

4. **Model compliance thấp với JSON format**: `qwen2.5:7b` không phải model được fine-tune cho JSON output, nên thường thêm text trước/sau JSON hoặc trả về plain text thay vì JSON.

### Bug 2 — Semaphore Leak

1. **Generator lifecycle không được kiểm soát**: `query_stream()` là generator function. Khi Streamlit rerun, Python destroy generator object. Nếu generator đang suspended tại `yield token` trong vòng lặp word-by-word của fused path, `generate_response_fused()` đã hoàn thành và semaphore đã được release — không có leak trong path này.

2. **Race condition với Streamlit rerun**: Nếu Streamlit rerun xảy ra TRONG KHI `generate_response_fused()` đang chạy (chờ semaphore hoặc chờ LLM response), generator bị destroy và `generate_response_fused()` có thể bị interrupt. Tuy nhiên, `generate_response_fused()` có `try/finally` nội bộ nên semaphore vẫn được release.

3. **Thực tế bug path**: Bug thực sự có thể xảy ra nếu có exception trong `query_stream()` TRƯỚC khi `generate_response_fused()` hoàn thành và NGOÀI `try/except (LLMQueueFullError, LLMTimeoutError)` block. Hoặc nếu có unhandled exception type khác từ `generate_response_fused()`.

4. **Defensive fix cần thiết**: Dù root cause chính xác cần được xác nhận qua exploratory testing, việc bọc fused call trong `try/finally` tại `query_stream()` là defensive fix đúng đắn và không có downside.

---

## Correctness Properties

Property 1: Bug Condition — Fused Response Cleanup

_For any_ input `X` where `isBugCondition_Bug1(X)` returns true (prompt_fusion_enabled=True AND LLM output is invalid JSON, empty answer, or breadcrumb-only), the fixed `FusedLLMResponse.from_json()` and `from_raw_text()` SHALL produce an `answer` that:
- Does NOT contain raw JSON syntax characters as the primary content (`{`, `}`, `"answer":`)
- Does NOT equal a bare breadcrumb string (e.g., `"Chương 1 > Điều 3"` without explanatory content)
- Contains meaningful Vietnamese text extracted from the raw output, or a clear "không đủ thông tin" message

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Valid JSON Parsing Unchanged

_For any_ input where `isBugCondition_Bug1(X)` returns false (LLM output is valid JSON with non-empty `answer` field), the fixed `FusedLLMResponse.from_json()` SHALL produce the same result as the original `from_json()`, preserving correct parsing of `answer`, `rewritten_query`, and `confidence` fields.

**Validates: Requirements 3.1, 3.2, 3.6**

Property 3: Bug Condition — Semaphore Always Released

_For any_ input `X` where `isBugCondition_Bug2(X)` returns true (prompt_fusion_enabled=True AND generator abandoned OR exception raised), the fixed `query_stream()` SHALL ensure `semaphore.available_slots()` after the call equals `semaphore.available_slots()` before the call — the semaphore slot is always returned regardless of how the generator terminates.

**Validates: Requirements 2.4, 2.5, 2.6**

Property 4: Preservation — Non-Fused Stream Behavior Unchanged

_For any_ input where `isBugCondition_Bug2(X)` returns false (prompt_fusion_enabled=False OR generator fully exhausted without exception), the fixed `query_stream()` SHALL produce exactly the same token sequence and side effects as the original `query_stream()`, preserving all existing streaming behavior.

**Validates: Requirements 3.1, 3.3, 3.4, 3.5, 3.7**

---

## Fix Implementation

### Bug 1 — Changes Required

**File**: `src/llm/llm_manager.py`

**Target**: `_FUSED_SYSTEM_PROMPT` (module-level constant)

**Specific Changes**:

1. **Yêu cầu nội dung đầy đủ**: Thêm instruction rõ ràng vào prompt: "Giải thích đầy đủ nội dung của Điều/Khoản đó, không chỉ liệt kê tên hay số hiệu. Answer phải là câu trả lời hoàn chỉnh, không phải chỉ mục hay breadcrumb."

2. **Nhấn mạnh format JSON**: Thêm ví dụ JSON mẫu hoặc nhấn mạnh rằng `answer` phải chứa nội dung giải thích, không phải chỉ reference.

---

**File**: `src/rag/models.py`

**Target**: `FusedLLMResponse.from_raw_text()` và `FusedLLMResponse.from_json()`

**Specific Changes**:

3. **Cải thiện `from_raw_text()`**: Thêm cleanup logic trước khi dùng text làm answer:
   - Strip code fences (` ```json `, ` ``` `)
   - Loại bỏ JSON fragment patterns (text bắt đầu bằng `{` hoặc chứa `"answer":`)
   - Nếu sau cleanup text rỗng hoặc chỉ là JSON syntax, trả về message mặc định

4. **Cải thiện `from_json()` partial extraction**: Khi JSON parse thất bại, thử extract text có nghĩa:
   - Tìm pattern `"answer"\s*:\s*"([^"]+)"` bằng regex để extract answer từ malformed JSON
   - Nếu tìm được, dùng extracted text thay vì toàn bộ raw text
   - Nếu không tìm được, gọi `from_raw_text()` với cleaned version

### Bug 2 — Changes Required

**File**: `src/rag/rag_pipeline.py`

**Target**: `query_stream()` method, phần `if self.prompt_fusion_enabled:`

**Specific Changes**:

5. **Bọc fused call trong `try/finally`**: Tách semaphore lifecycle ra khỏi `generate_response_fused()` hoặc thêm `try/finally` tại `query_stream()` để đảm bảo semaphore luôn được release.

   **Approach được chọn**: Thêm `try/finally` tại `query_stream()` bao quanh toàn bộ fused call block. Cách này ít invasive hơn và không thay đổi interface của `generate_response_fused()`.

   ```python
   if self.prompt_fusion_enabled:
       try:
           fused_result = self.llm_manager.generate_response_fused(...)
           clean_answer = fused_result["answer"]
           rewritten_query = fused_result.get("rewritten_query")
           # stream word-by-word...
           for i, word in enumerate(words):
               ...
               yield token
           full_answer = clean_answer
       except (LLMQueueFullError, LLMTimeoutError) as exc:
           yield f"\n\n❌ Lỗi: {exc}"
           return
       except Exception as exc:
           logger.exception("[pipeline] Fused generation failed in stream")
           yield f"\n\n❌ Lỗi không xác định: {exc}"
           return
   ```

   **Lưu ý**: `generate_response_fused()` đã có `try/finally` nội bộ bao quanh `llm.invoke()`. Fix tại `query_stream()` là defensive layer bổ sung để handle các edge case khác (exception trong word-by-word streaming, generator abandonment).

---

## Testing Strategy

### Validation Approach

Testing theo hai phase: (1) Exploratory — chạy trên code CHƯA FIX để xác nhận bug và root cause; (2) Fix + Preservation — chạy sau khi fix để verify correctness.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples trên code chưa fix. Xác nhận hoặc bác bỏ root cause analysis.

**Test Plan**: Viết unit tests mock LLM output với các raw text patterns khác nhau, chạy trên code hiện tại để quan sát failure.

**Test Cases**:

1. **Breadcrumb-only output** (Bug 1): Mock LLM trả về `"Chương 1: Phần I > Điều 3"` → `from_raw_text()` hiện tại trả về breadcrumb nguyên xi (sẽ fail sau fix)
2. **JSON fragment output** (Bug 1): Mock LLM trả về `'{"answer": "Điều 5", "rewritten_query"'` (truncated JSON) → `from_json()` parse fail, `from_raw_text()` trả về JSON fragment (sẽ fail sau fix)
3. **Empty answer in valid JSON** (Bug 1): Mock LLM trả về `'{"answer": "", "confidence": 0.5}'` → fallback về `from_raw_text()` với JSON string (sẽ fail sau fix)
4. **Semaphore count after exception** (Bug 2): Mock `llm.invoke()` để raise generic `RuntimeError`, kiểm tra semaphore count trước và sau `query_stream()` call (có thể pass vì `generate_response_fused()` có `try/finally` nội bộ — cần verify)
5. **Semaphore count after generator abandon** (Bug 2): Tạo generator từ `query_stream()`, consume 0 tokens, delete generator, kiểm tra semaphore count (sẽ fail nếu bug tồn tại)

**Expected Counterexamples**:

- Bug 1: `answer` field chứa `{`, `}`, `"answer":` hoặc chỉ là breadcrumb string
- Bug 2: `semaphore._value` sau call nhỏ hơn trước call (slot bị leak)

### Fix Checking

**Goal**: Verify rằng với tất cả inputs thuộc bug condition, fixed code trả về behavior đúng.

**Pseudocode:**

```
// Bug 1
FOR ALL X WHERE isBugCondition_Bug1(X) DO
  result ← FusedLLMResponse.from_json'(X.llm_raw_output)
  ASSERT result.answer DOES NOT start with '{'
  ASSERT result.answer DOES NOT contain '"answer":'
  ASSERT result.answer IS NOT breadcrumb_only_pattern
  ASSERT len(result.answer) > 10  // có nội dung thực
END FOR

// Bug 2
FOR ALL X WHERE isBugCondition_Bug2(X) DO
  slots_before ← semaphore._value
  TRY query_stream'(X) EXCEPT ANY
  slots_after ← semaphore._value
  ASSERT slots_before = slots_after
END FOR
```

### Preservation Checking

**Goal**: Verify rằng với tất cả inputs KHÔNG thuộc bug condition, fixed code cho kết quả giống original.

**Pseudocode:**

```
// Bug 1 Preservation
FOR ALL X WHERE NOT isBugCondition_Bug1(X) DO
  ASSERT FusedLLMResponse.from_json(X) = FusedLLMResponse.from_json'(X)
END FOR

// Bug 2 Preservation
FOR ALL X WHERE NOT isBugCondition_Bug2(X) DO
  ASSERT query_stream(X) produces same tokens as query_stream'(X)
END FOR
```

**Testing Approach**: Property-based testing được khuyến nghị cho preservation checking vì:
- Tự động generate nhiều test cases với valid JSON inputs khác nhau
- Catch edge cases mà manual test có thể bỏ sót (JSON với unicode, special chars, long text)
- Đảm bảo mạnh mẽ rằng valid JSON path không bị thay đổi

**Test Cases**:

1. **Valid JSON preservation**: Generate random valid JSON với `answer` field có nội dung → verify `from_json()` trả về đúng answer
2. **Classic flow preservation**: Verify `query_stream()` với `prompt_fusion_enabled=False` không thay đổi
3. **Cache hit preservation**: Verify cache hit path không acquire semaphore và trả về đúng cached answer
4. **Semaphore blocking preservation**: Verify request thứ 3 vẫn bị block khi 2 slots đang bận

### Unit Tests

- Test `from_raw_text()` với breadcrumb input → output không phải breadcrumb
- Test `from_raw_text()` với JSON fragment input → output không chứa JSON syntax
- Test `from_json()` với truncated JSON → extract answer bằng regex hoặc cleanup
- Test `from_json()` với valid JSON → parse đúng tất cả fields
- Test `query_stream()` semaphore count sau exception trong fused path
- Test `query_stream()` semaphore count sau generator abandonment

### Property-Based Tests

- Generate random strings chứa JSON patterns → `from_raw_text()` output không chứa JSON syntax
- Generate random valid JSON objects với `answer` field → `from_json()` luôn trả về đúng answer
- Generate random exception scenarios trong fused path → semaphore count không thay đổi
- Generate random non-fused inputs → `query_stream()` behavior không thay đổi so với original

### Integration Tests

- End-to-end test với mock Ollama trả về breadcrumb → UI nhận được nội dung có nghĩa
- End-to-end test với mock Ollama trả về JSON fragment → UI nhận được cleaned answer
- Concurrent request test: 2 requests hoàn thành, request thứ 3 được xử lý ngay sau đó (không bị block)
- Streamlit rerun simulation: abandon generator giữa chừng, verify next request không bị block
