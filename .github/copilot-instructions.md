# Project Copilot Instructions

This repository is a local Python RAG system using Ollama, LangChain, and ChromaDB.

## Primary Goals
- Keep answers grounded in retrieved documents.
- Prefer minimal and safe edits.
- Preserve existing architecture and naming unless explicitly asked.

## Architecture Anchors
- Main CLI entry: src/main.py
- Streamlit app entry: app.py
- Core RAG orchestrator: src/rag/rag_pipeline.py
- Vector store manager: src/rag/vector_store.py
- Persistent chat and auth storage: src/storage/chat_store.py

## Runtime Expectations
- Python environment uses venv in this workspace.
- Ollama models expected:
  - qwen2.5:7b
  - nomic-embed-text:v1.5

## Editing Rules
- Do not replace RAG with direct LLM chat unless requested.
- Keep source citation support when changing answer pipelines.
- Keep tenant isolation checks in storage methods.
- Avoid broad refactors in unrelated files.

## Validation Commands
- Fast syntax check:
  - .\venv\Scripts\python.exe -m py_compile app.py src/storage/chat_store.py
- Run tests:
  - .\venv\Scripts\python.exe -m pytest -v

## Response Style for This Repo
- Explain root cause first for bugs.
- Include exact files changed and why.
- Propose smallest possible next step when blocked.

## Language Preference
- Prefer Vietnamese for explanations and final answers.
- If the user asks in English, reply in English.
- Keep technical terms and commands unchanged when needed.
