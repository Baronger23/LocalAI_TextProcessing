---
agent: ask
description: "TDD workflow for RAG and storage changes with RED-GREEN-REFACTOR and strict unit-test gate"
---

Run strict TDD for this repository.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

TDD protocol:
1. RED: write or update a failing unit test that reproduces the requested behavior.
2. GREEN: implement the minimal production change to pass the test.
3. REFACTOR: improve code clarity without changing behavior.
4. VERIFY: run focused tests first, then broader checks when relevant.

Rules:
- No feature completion without tests.
- Keep changes minimal and scoped.
- Preserve retrieval-grounded RAG behavior and source metadata.
- Preserve tenant isolation and authorization checks in storage layer.

Output format:
1. RED test added/updated
2. GREEN code changes
3. REFACTOR notes
4. Test evidence (commands + result)
5. Residual risks

Validation:
- .\\venv\\Scripts\\python.exe -m py_compile app.py src/storage/chat_store.py
- .\\venv\\Scripts\\python.exe -m pytest -v
