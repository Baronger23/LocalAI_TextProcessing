---
agent: ask
description: "Evaluate RAG answer quality using citation grounding, source relevance, and hallucination risk checks"
---

Run a focused RAG answer quality evaluation for this repository.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Objective:
- Score whether each answer is grounded in retrieved sources and citations.

Workflow (ECC-style quality gate):
1. Collect sample Q/A pairs and attached sources from current pipeline.
2. Verify citation-grounding: does the answer match cited chunks?
3. Rate source relevance: are cited chunks actually relevant to the user question?
4. Detect unsupported claims and hallucination risk.
5. Propose minimal fixes in retrieval, prompt, or post-processing.

Evaluation rubric (0-5):
- Citation coverage: number of key claims backed by cited source.
- Citation precision: citation truly supports the claim.
- Answer faithfulness: no content beyond available evidence.
- Retrieval relevance: top-k chunks aligned with question intent.
- Clarity and uncertainty handling: states "không đủ thông tin" when evidence is missing.

Output format:
1. Score summary table
2. Critical failures (if any)
3. Root causes
4. Minimal fix plan
5. Suggested regression checks

Validation suggestions:
- .\\venv\\Scripts\\python.exe -m py_compile app.py src/rag/rag_pipeline.py src/storage/chat_store.py
- .\\venv\\Scripts\\python.exe -m pytest -v
