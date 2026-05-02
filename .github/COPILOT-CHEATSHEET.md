# Copilot Prompt Cheat Sheet (ECC + TDD)

Quick guide for this repository.

## 1) Quick Start

1. Open Copilot Chat.
2. Type `/` and choose a prompt.
3. Add your task in one sentence.
4. Follow the suggested flow below.

Language default:
- Prefer Vietnamese.
- If user asks in English, reply in English.

## 2) Recommended Flows

### A. Add a new feature safely

1. `/tdd-rag-storage`
2. `/add-rag-feature`
3. `/premerge-lock-concurrency`
4. `/security-review-tenant` (if auth/storage touched)

### B. Fix PostgreSQL connection/lock issues

1. `/debug-postgres-lock`
2. `/premerge-lock-concurrency`

### C. Improve answer grounding quality

1. `/rag-citation-quality`
2. `/add-rag-feature` (for minimal implementation fix)

### D. Storage/schema changes

1. `/storage-migration-safety`
2. `/tdd-rag-storage`
3. `/premerge-lock-concurrency`

## 3) Prompt Catalog

- `/rag-feature`: small RAG feature with minimal risk.
- `/add-rag-feature`: full feature flow with retrieval grounding and test gate.
- `/tdd-rag-storage`: strict RED-GREEN-REFACTOR workflow.
- `/debug-postgres-lock`: investigate and fix PostgreSQL connection or deadlock contention.
- `/premerge-lock-concurrency`: pre-merge concurrency and transaction gate.
- `/security-review-tenant`: tenant isolation and authorization review.
- `/rag-citation-quality`: citation grounding and hallucination risk scoring.
- `/storage-migration-safety`: migration and backward-compatibility safety plan.

## 4) Quality Gate Rules

Do not mark task complete when:
- Changed behavior has no tests.
- Critical lock/tenant issues remain unresolved.
- Validation commands were not run.

Minimum validation commands:
- `.\\venv\\Scripts\\python.exe -m py_compile app.py src/storage/chat_store.py`
- `.\\venv\\Scripts\\python.exe -m pytest -v`

## 5) Suggested Prompt Templates

### Feature request

`/add-rag-feature`

"Thêm [feature], giữ citation, không phá tenant isolation, ưu tiên sửa nhỏ nhất."

### Lock bug

`/debug-postgres-lock`

"Tìm root cause lock khi [action], đề xuất fix tối thiểu và kiểm tra pre-merge."

### Security review

`/security-review-tenant`

"Review toàn bộ đường read/write cho conversation/messages/summary/user_memories và xếp mức độ rủi ro."

## 6) Related Project Files

- `.github/copilot-instructions.md`
- `.github/instructions/rag-python.instructions.md`
- `.github/instructions/tests.instructions.md`
- `.github/prompts/`
- `tests/test_storage_chat_store.py`

## 7) Practical Tips

- Keep prompts specific: include file/module names and expected behavior.
- Ask for "root cause first" on bug triage.
- Ask for "minimal fix" to avoid broad refactors.
- Ask for "test evidence" in the final response.
