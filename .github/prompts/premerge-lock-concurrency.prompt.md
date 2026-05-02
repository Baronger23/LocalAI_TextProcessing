---
agent: ask
description: "Run pre-merge lock and concurrency checks for PostgreSQL/chat storage and Streamlit flow"
---

Perform a pre-merge concurrency and lock-safety review for this project.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Scope:
- src/storage/chat_store.py
- app.py chat and auth flows
- Any migration or schema changes affecting write paths

Pre-merge gate checklist:
1. PostgreSQL connection/lock safety
- connection pool limits, timeouts, and retry strategy are present and consistent.
- write operations are properly scoped in transactions.
- nested write connections do not cause connection pool exhaustion or deadlocks.

2. Transaction integrity
- user/conversation/message writes are atomic where required.
- non-critical audit logging does not break critical paths.

3. Multi-user concurrency
- no cross-user data leakage under concurrent reads/writes.
- ownership checks enforced before data access.

4. Failure behavior
- transient connection errors handled with bounded retries.
- clear, non-sensitive error messages.

Output format:
1. Pre-merge status: PASS/FAIL
2. Blocking issues (ordered by severity)
3. Suggested minimal fixes
4. Re-test checklist

Validation commands:
- .\venv\Scripts\python.exe -m py_compile app.py src/storage/chat_store.py
- .\venv\Scripts\python.exe -m pytest -v
