---
agent: ask
description: "Review and implement safe storage schema changes with migration and backward-compatibility checks"
---

Design or review storage schema updates for this repository with safety-first migration strategy.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Scope:
- src/storage/chat_store.py
- Any file that reads/writes PostgreSQL schema-dependent data

Safety workflow (ECC-style):
1. Map current schema usage paths before changing tables/columns.
2. Define migration strategy: additive-first, backward compatible, idempotent.
3. Prevent data loss: never drop or rewrite critical data without explicit migration plan.
4. Verify tenant isolation rules still hold after schema updates.
5. Add rollback/repair notes for operational recovery.

Required checks:
- New columns/tables have sensible defaults.
- Existing queries remain valid for old rows.
- Indexes are added for new high-frequency query paths.
- Migration scripts/DDL are safe to run multiple times.

Output format:
1. Migration risk summary
2. Proposed schema changes
3. Compatibility strategy
4. Validation and rollback steps
5. Follow-up hardening tasks

Validation commands:
- .\\venv\\Scripts\\python.exe -m py_compile app.py src/storage/chat_store.py
- .\\venv\\Scripts\\python.exe -m pytest -v
