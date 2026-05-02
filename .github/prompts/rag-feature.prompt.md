---
agent: ask
description: "Plan and implement a small RAG feature safely in this repo"
---

You are working in this local Python RAG repository.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Task:
1. Understand the requested feature.
2. Identify the smallest set of files to change.
3. Implement with minimal risk.
4. Run focused validation commands.
5. Summarize exact behavior change and residual risks.

Quality gate (must pass):
- Do not mark task as complete if there is no test covering changed behavior.
- If no existing test can cover it, add a focused unit test.
- If tests cannot be added, explicitly return FAIL with reason and next action.

Constraints:
- Keep retrieval-grounded answer behavior.
- Do not remove citation/source support.
- Preserve user ownership checks in storage.

Validation:
- .\venv\Scripts\python.exe -m py_compile app.py src/storage/chat_store.py
- .\venv\Scripts\python.exe -m pytest -v
