---
applyTo: "src/**/*.py,app.py"
description: "RAG Python implementation guidance for retrieval-grounded responses and safe local architecture changes"
---

When editing Python RAG code in this repo:

1. Keep retrieval-grounded behavior
- Prefer using RAGPipeline query flow over direct raw model invocation for user QA.
- Keep source metadata and citation fields intact where available.

2. Preserve storage and security boundaries
- For chat persistence, always scope reads and writes by user ownership checks.
- Do not bypass user_id or conversation ownership validation.

3. Keep changes incremental
- Avoid changing public method names unless requested.
- Avoid changing data schema names without migration strategy.

4. Error handling
- Prefer explicit errors with actionable messages.
- Do not let non-critical audit logging break main user flows.

5. Performance and reliability
- Be cautious with extra LLM calls in hot paths.
- Keep retry and lock-safe behavior for SQLite write paths.
