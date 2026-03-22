---
name: timescaledb-access
description: Use when work in this repo needs TimescaleDB/PostgreSQL access: running storage-backed tests, inspecting schema/data, initializing the database, or preparing a shell that may need credentials from local env files or Infisical. The skill focuses on safe env discovery, namespace normalization across TSDB_* / POSTGRES_* / PG*, and read-only connection validation without printing secrets.
---

# TimescaleDB Access

Use this skill when you need a working database shell or command context for this repo's TimescaleDB-backed storage.

## What this repo expects

- The Python code prefers `TSDB_*` and falls back to `POSTGRES_*`.
- Local `.env` may define `POSTGRES_*`.
- Credentials may also be injected at runtime with `infisical run ... -- <command>`.
- Never print secret values. Only show key presence or redact values.

## Workflow

1. **Inspect the current environment safely**
   - Check whether `TSDB_*` or `POSTGRES_*` already exist.
   - If you show them, redact values.

2. **Prefer existing env over re-fetching secrets**
   - If the shell already has valid DB env, use it.
   - Otherwise, check whether a local `.env` is present.
   - If neither is sufficient, wrap the command with Infisical using the repo's documented project/env/path rather than hardcoding anything new.

3. **Normalize env names before using tools**
   - Export all three namespaces consistently:
     - `TSDB_*`
     - `POSTGRES_*`
     - `PG*` for `psql`
   - Prefer a single inline block so the agent can paste/adapt it in the current shell.

4. **Validate access with a read-only command first**
   - Prefer `psql -c 'select current_database(), current_user, version();'`
   - Or a short Python/psycopg connection check.
   - Do this before running migrations, schema init, or integration tests.

5. **Then run the actual repo task**
   - Examples:
     - `uv run pytest tests/timeseries/test_integration.py -m integration`
     - `uv run python -c 'from lseg_toolkit.timeseries.storage import init_db; init_db()'`
     - `psql -c '\dt'`

## Safe operating rules

- Never echo raw passwords, DSNs, or full secret env values.
- Avoid putting passwords directly on command lines when `PG*` env vars will work.
- Prefer read-only verification before write operations.
- If the documented Infisical location is ambiguous or missing, search the repo/docs/shell history and then ask the user instead of guessing.

## Quick patterns

### Safe env inspection

```bash
env | rg '^(TSDB|POSTGRES|PG)' | sed -E 's/=.*/=***REDACTED***/'
```

### Normalize whichever namespace is available

```bash
set -a
[ -f .env ] && source .env
set +a

export TSDB_HOST="${TSDB_HOST:-${POSTGRES_HOST:-$PGHOST}}"
export TSDB_PORT="${TSDB_PORT:-${POSTGRES_PORT:-${PGPORT:-5432}}}"
export TSDB_DATABASE="${TSDB_DATABASE:-${POSTGRES_DB:-$PGDATABASE}}"
export TSDB_USER="${TSDB_USER:-${POSTGRES_USER:-$PGUSER}}"
export TSDB_PASSWORD="${TSDB_PASSWORD:-${POSTGRES_PASSWORD:-$PGPASSWORD}}"

export POSTGRES_HOST="${POSTGRES_HOST:-$TSDB_HOST}"
export POSTGRES_PORT="${POSTGRES_PORT:-$TSDB_PORT}"
export POSTGRES_DB="${POSTGRES_DB:-$TSDB_DATABASE}"
export POSTGRES_USER="${POSTGRES_USER:-$TSDB_USER}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$TSDB_PASSWORD}"

export PGHOST="${PGHOST:-$TSDB_HOST}"
export PGPORT="${PGPORT:-$TSDB_PORT}"
export PGDATABASE="${PGDATABASE:-$TSDB_DATABASE}"
export PGUSER="${PGUSER:-$TSDB_USER}"
export PGPASSWORD="${PGPASSWORD:-$TSDB_PASSWORD}"
```

### Read-only connectivity check

```bash
set -a
[ -f .env ] && source .env
set +a

export TSDB_HOST="${TSDB_HOST:-${POSTGRES_HOST:-$PGHOST}}"
export TSDB_PORT="${TSDB_PORT:-${POSTGRES_PORT:-${PGPORT:-5432}}}"
export TSDB_DATABASE="${TSDB_DATABASE:-${POSTGRES_DB:-$PGDATABASE}}"
export TSDB_USER="${TSDB_USER:-${POSTGRES_USER:-$PGUSER}}"
export TSDB_PASSWORD="${TSDB_PASSWORD:-${POSTGRES_PASSWORD:-$PGPASSWORD}}"

export POSTGRES_HOST="${POSTGRES_HOST:-$TSDB_HOST}"
export POSTGRES_PORT="${POSTGRES_PORT:-$TSDB_PORT}"
export POSTGRES_DB="${POSTGRES_DB:-$TSDB_DATABASE}"
export POSTGRES_USER="${POSTGRES_USER:-$TSDB_USER}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$TSDB_PASSWORD}"

export PGHOST="${PGHOST:-$TSDB_HOST}"
export PGPORT="${PGPORT:-$TSDB_PORT}"
export PGDATABASE="${PGDATABASE:-$TSDB_DATABASE}"
export PGUSER="${PGUSER:-$TSDB_USER}"
export PGPASSWORD="${PGPASSWORD:-$TSDB_PASSWORD}"

psql -c 'select current_database(), current_user;'
```

### Run a repo command with Infisical

```bash
infisical run ... -- zsh -lc '
  set -a
  [ -f .env ] && source .env
  set +a
  export TSDB_HOST="${TSDB_HOST:-${POSTGRES_HOST:-$PGHOST}}"
  export TSDB_PORT="${TSDB_PORT:-${POSTGRES_PORT:-${PGPORT:-5432}}}"
  export TSDB_DATABASE="${TSDB_DATABASE:-${POSTGRES_DB:-$PGDATABASE}}"
  export TSDB_USER="${TSDB_USER:-${POSTGRES_USER:-$PGUSER}}"
  export TSDB_PASSWORD="${TSDB_PASSWORD:-${POSTGRES_PASSWORD:-$PGPASSWORD}}"
  export POSTGRES_HOST="${POSTGRES_HOST:-$TSDB_HOST}"
  export POSTGRES_PORT="${POSTGRES_PORT:-$TSDB_PORT}"
  export POSTGRES_DB="${POSTGRES_DB:-$TSDB_DATABASE}"
  export POSTGRES_USER="${POSTGRES_USER:-$TSDB_USER}"
  export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$TSDB_PASSWORD}"
  export PGHOST="${PGHOST:-$TSDB_HOST}"
  export PGPORT="${PGPORT:-$TSDB_PORT}"
  export PGDATABASE="${PGDATABASE:-$TSDB_DATABASE}"
  export PGUSER="${PGUSER:-$TSDB_USER}"
  export PGPASSWORD="${PGPASSWORD:-$TSDB_PASSWORD}"
  uv run pytest tests/timeseries/test_integration.py -m integration
'
```

Use the concrete `infisical run` arguments already documented in the repo or already present in the user’s environment; do not invent new ones.
