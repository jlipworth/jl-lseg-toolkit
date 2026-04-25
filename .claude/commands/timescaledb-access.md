---
description: Run the TimescaleDB access workflow (env discovery, namespace normalization, read-only validation) before touching the database.
---

Follow `.claude/skills/timescaledb-access/SKILL.md` as the canonical workflow for any TimescaleDB/PostgreSQL access in this repo.

Core rules:
- Prefer existing env, then local `.env`, then Infisical injection.
- Normalize across `TSDB_*`, `POSTGRES_*`, and `PG*` using the inline export block in the skill file.
- Never print secret values — redact when inspecting.
- Validate with a read-only `psql` or `psycopg` check before running write operations.

For multi-step DB tasks, dispatch the `timescaledb-access` agent (`.claude/agents/timescaledb-access.md`) so the work happens in an isolated context.

$ARGUMENTS
