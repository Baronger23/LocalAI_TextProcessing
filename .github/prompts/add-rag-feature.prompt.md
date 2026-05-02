---
agent: ask
description: "Add a new RAG feature with retrieval-grounded behavior, citations, and minimal-risk implementation"
---

Implement a requested feature in this Python RAG system.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Workflow (inspired by skills-first ECC style):
1. Plan the smallest implementation slice.
2. Update only necessary files.
3. Keep answers grounded in retrieval.
4. Preserve source citation metadata.
5. Validate with compile/tests.

Quality gate (must pass):
- Do not mark feature complete if changed behavior has no test coverage.
- Prefer adding/updating focused unit tests in tests/.
- If test coverage is blocked, return FAIL with blocker and minimal recovery plan.

Hard constraints:
- Do not switch user QA flow from RAG to direct raw LLM unless explicitly asked.
- Keep tenant ownership checks for persisted chat data.
- Avoid unrelated refactors.

Validation:
- .\\venv\\Scripts\\python.exe -m py_compile app.py src/storage/chat_store.py
- .\\venv\\Scripts\\python.exe -m pytest -v

Output format:
1. Feature summary
2. File-level changes
3. Why this design
4. Test/validation result
