---
agent: ask
description: "Debug PostgreSQL connection pool or deadlock issues in Streamlit or storage layer with safe, minimal fixes"
---

You are debugging PostgreSQL connection contention or deadlocks in this repository.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Focus areas:
1. Reproduce and isolate the connection or lock path.
2. Inspect write/read concurrency in src/storage/chat_store.py.
3. Check nested transactions, retry strategy, connection pool limits, timeout, and transaction isolation.
4. Propose the smallest safe fix that preserves tenant isolation and audit behavior.

Execution expectations:
- Prefer root-cause evidence before editing.
- Keep audit logging best-effort (must not break core auth/chat flow).
- Do not remove ownership checks.

Validation:
- .\venv\Scripts\python.exe -m py_compile app.py src/storage/chat_store.py
- .\venv\Scripts\python.exe -m pytest -v

Output format:
1. Root cause
2. Minimal fix
3. Files changed
4. Residual risks
