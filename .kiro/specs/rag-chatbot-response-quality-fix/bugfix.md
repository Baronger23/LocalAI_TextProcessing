# Bugfix Requirements Document

## Introduction

Sau khi triển khai tối ưu tốc độ RAG (spec `rag-response-speed-optimization`), hai bug hồi quy xuất hiện:

**Bug 1 — Câu trả lời không đúng trọng tâm (Fused Prompt / JSON Parsing):**
Khi `PROMPT_FUSION_ENABLED=true`, model `qwen2.5:7b` thường không tuân thủ JSON format nghiêm ngặt. `FusedLLMResponse.from_json()` parse thất bại và fallback về `from_raw_text()` — dùng toàn bộ raw output (bao gồm JSON fragment, breadcrumb) làm answer. Ngoài ra, `_FUSED_SYSTEM_PROMPT` chỉ yêu cầu "trích dẫn Điều/Khoản khi có thể" mà không yêu cầu trả lời đầy đủ nội dung, khiến LLM chỉ trả về breadcrumb thay vì nội dung thực sự.

**Bug 2 — Câu hỏi thứ 2 bị block vô thời hạn (Semaphore Leak):**
Trong `query_stream()` khi `prompt_fusion_enabled=True`, code gọi `generate_response_fused()` — semaphore được acquire bên trong hàm này. Nếu có exception hoặc Streamlit rerun giữa chừng, generator bị bỏ dở mà không có cơ chế đảm bảo semaphore được release. Với `LLM_MAX_CONCURRENT_CALLS=2` và warmup thread đang giữ 1 slot, câu hỏi thứ 2 phải chờ đến khi timeout 120 giây.

---

## Bug Analysis

### Current Behavior (Defect)

**Bug 1 — Fused Prompt / JSON Parsing:**

1.1 WHEN `PROMPT_FUSION_ENABLED=true` VÀ model trả về text thường hoặc JSON không đầy đủ THEN hệ thống hiển thị raw output (JSON fragment, breadcrumb như "Chương 1: Phần I") thay vì câu trả lời thực sự

1.2 WHEN `PROMPT_FUSION_ENABLED=true` VÀ `FusedLLMResponse.from_json()` parse thất bại THEN hệ thống dùng toàn bộ raw text làm answer mà không lọc bỏ JSON artifact

1.3 WHEN `_FUSED_SYSTEM_PROMPT` được gửi đến LLM THEN hệ thống nhận về chỉ breadcrumb/chỉ mục tài liệu thay vì nội dung đầy đủ vì prompt không yêu cầu rõ ràng phải trả lời đầy đủ nội dung

**Bug 2 — Semaphore Leak:**

1.4 WHEN `query_stream()` được gọi với `prompt_fusion_enabled=True` VÀ xảy ra exception trong `generate_response_fused()` THEN hệ thống không release semaphore, khiến slot bị chiếm vĩnh viễn

1.5 WHEN Streamlit rerun xảy ra giữa chừng trong `query_stream()` (generator bị bỏ dở) VÀ `generate_response_fused()` đang giữ semaphore THEN hệ thống không release semaphore vì generator không được exhaust đến `finally` block

1.6 WHEN semaphore bị leak VÀ `LLM_MAX_CONCURRENT_CALLS=2` VÀ warmup thread đang giữ 1 slot THEN hệ thống block câu hỏi thứ 2 vô thời hạn (tối đa 120 giây) trước khi raise `LLMTimeoutError`

---

### Expected Behavior (Correct)

**Bug 1 — Fused Prompt / JSON Parsing:**

2.1 WHEN `PROMPT_FUSION_ENABLED=true` VÀ model trả về text thường hoặc JSON không đầy đủ THEN hệ thống SHALL trích xuất phần text có nghĩa nhất làm answer, không hiển thị JSON artifact hay breadcrumb đơn thuần

2.2 WHEN `FusedLLMResponse.from_json()` parse thất bại VÀ raw text chứa JSON fragment THEN hệ thống SHALL làm sạch raw text (loại bỏ JSON syntax, code fence) trước khi dùng làm fallback answer

2.3 WHEN `_FUSED_SYSTEM_PROMPT` được gửi đến LLM THEN hệ thống SHALL nhận về câu trả lời đầy đủ nội dung vì prompt yêu cầu rõ ràng phải giải thích nội dung chi tiết, không chỉ liệt kê chỉ mục

**Bug 2 — Semaphore Leak:**

2.4 WHEN `query_stream()` được gọi với `prompt_fusion_enabled=True` VÀ xảy ra exception trong `generate_response_fused()` THEN hệ thống SHALL release semaphore trong `finally` block, đảm bảo slot luôn được trả về

2.5 WHEN Streamlit rerun xảy ra giữa chừng trong `query_stream()` (generator bị bỏ dở) THEN hệ thống SHALL release semaphore thông qua context manager hoặc `try/finally` bao quanh toàn bộ fused call, không phụ thuộc vào việc generator có được exhaust hay không

2.6 WHEN semaphore được quản lý đúng cách THEN hệ thống SHALL xử lý câu hỏi thứ 2 ngay sau khi câu hỏi thứ 1 hoàn thành, không bị block quá 1 giây chờ semaphore

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `PROMPT_FUSION_ENABLED=false` THEN hệ thống SHALL CONTINUE TO dùng classic 2-call flow (rewrite + generate riêng biệt) không bị ảnh hưởng

3.2 WHEN model trả về JSON hợp lệ đầy đủ với field `answer`, `rewritten_query`, `confidence` THEN hệ thống SHALL CONTINUE TO parse và trả về đúng các field đó

3.3 WHEN `STREAMING_ENABLED=true` VÀ `PROMPT_FUSION_ENABLED=false` THEN hệ thống SHALL CONTINUE TO stream token trực tiếp từ Ollama không qua JSON parsing

3.4 WHEN câu hỏi đã có trong cache THEN hệ thống SHALL CONTINUE TO trả về cached answer ngay lập tức mà không gọi LLM hay acquire semaphore

3.5 WHEN `LLM_MAX_CONCURRENT_CALLS=2` VÀ có 2 request đang chạy đồng thời hợp lệ THEN hệ thống SHALL CONTINUE TO block request thứ 3 cho đến khi có slot trống (behavior đúng của semaphore)

3.6 WHEN `generate_response_fused()` được gọi trực tiếp (không qua `query_stream()`) VÀ thành công THEN hệ thống SHALL CONTINUE TO trả về dict với keys `answer`, `rewritten_query`, `confidence`, `queue_wait_ms`

3.7 WHEN warmup thread gọi `llm_manager.invoke()` THEN hệ thống SHALL CONTINUE TO acquire và release semaphore đúng cách, không ảnh hưởng đến các request thực

---

## Bug Condition Pseudocode

### Bug 1 — Fused Prompt / JSON Parsing

```pascal
FUNCTION isBugCondition_Bug1(X)
  INPUT: X = (prompt_fusion_enabled: bool, llm_raw_output: str)
  OUTPUT: boolean

  RETURN X.prompt_fusion_enabled = true
    AND (
      NOT isValidJSON(X.llm_raw_output)
      OR NOT hasNonEmptyAnswerField(X.llm_raw_output)
      OR isOnlyBreadcrumb(X.llm_raw_output)
    )
END FUNCTION

// Property: Fix Checking — Bug 1
FOR ALL X WHERE isBugCondition_Bug1(X) DO
  result ← generate_response_fused'(X)
  ASSERT result.answer DOES NOT contain raw JSON syntax
  ASSERT result.answer DOES NOT equal breadcrumb-only string
  ASSERT result.answer contains meaningful Vietnamese text
END FOR
```

### Bug 2 — Semaphore Leak

```pascal
FUNCTION isBugCondition_Bug2(X)
  INPUT: X = (prompt_fusion_enabled: bool, generator_exhausted: bool, exception_raised: bool)
  OUTPUT: boolean

  RETURN X.prompt_fusion_enabled = true
    AND (X.generator_exhausted = false OR X.exception_raised = true)
END FUNCTION

// Property: Fix Checking — Bug 2
FOR ALL X WHERE isBugCondition_Bug2(X) DO
  semaphore_before ← semaphore.available_slots()
  query_stream'(X)  // may raise or be abandoned
  semaphore_after ← semaphore.available_slots()
  ASSERT semaphore_before = semaphore_after  // slot always returned
END FOR

// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition_Bug2(X) DO
  ASSERT query_stream(X) = query_stream'(X)  // behavior unchanged
END FOR
```
