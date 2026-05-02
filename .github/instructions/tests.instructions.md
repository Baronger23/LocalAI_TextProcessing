---
applyTo: "tests/**/*.py"
description: "Testing guidance for RAG, storage, and streamlit-related Python changes"
---

When adding or updating tests:

1. Prefer deterministic tests
- Mock LLM and network-dependent calls where possible.
- Avoid tests that require live Ollama unless explicitly intended.

2. Cover behavior, not internals
- Validate user-visible outputs and key side effects.
- For storage, verify tenant isolation and permission checks.

3. Keep scope focused
- Add tests only for changed behavior.
- Avoid broad snapshot tests for unstable text output.

4. Suggested test priorities
- Ownership checks for conversations and messages.
- Rolling summary persistence by conversation.
- User memories filtering by type and confidence.
