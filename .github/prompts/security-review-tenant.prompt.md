---
agent: ask
description: "Review tenant isolation and data access security for auth, conversations, messages, summaries, and user memories"
---

Run a focused security review for multi-user data boundaries in this project.

Language:
- Prefer Vietnamese for explanation and summary unless the user asks for another language.

Review scope:
- src/storage/chat_store.py
- app.py auth and conversation flow
- Any query paths that touch conversations, messages, summaries, user_memories

Checklist:
1. Tenant isolation on all read/write operations.
2. Authorization checks before data mutation.
3. No cross-user leakage in list/load operations.
4. Audit behavior does not expose sensitive data.
5. Error messages are safe and actionable.

If issues are found:
- Prioritize by severity.
- Provide concrete fix per issue.
- Add focused tests where suitable.

Output format:
1. Findings (highest severity first)
2. Recommended fixes
3. Optional hardening follow-ups
