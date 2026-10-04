# Dust-off merge-readiness review — 2026-10-03

Scope: `codex/dust-off-fixes` into `master`, PR #12. Reviewed baseline
`d1cb310010e1074bfb74ba5bd12dfcbe7f965b50` in an isolated temporary clone.
No repository `AGENTS.md` instructions were present. See the September dust-off
review for original remediation and operator follow-up requirements.

## Additional findings fixed

1. **Scheduler completeness / watermark:** a successful but incomplete daily
   Treasury response could advance `last_success_date` past missing sessions.
   Recheck closed-date coverage before advancing state. The instrument transaction
   rolls back observations and coverage on failure, then records failure state.
2. **Absent scheduler response:** `None` was not recorded as coverage, but was
   nevertheless reported as success. Reject it rather than advancing state.
   A successful empty DataFrame remains valid request coverage for unknown
   calendars; it is not proof of complete expected daily Treasury observations.
3. **Disconnected volume roll chain:** when an early pair had no observed
   crossover but a later pair did, the continuous builder started from the later
   pair and silently discarded the actual front contract. Require consecutive
   transitions from the first delivery contract; do not guess missing rolls.
4. **Truncated continuous output:** nonempty quarterly frames could still produce
   a history missing an observed tail. Reject stitched histories that drop observed
   dates and, for daily Treasury front-month histories, missing closed CME sessions.
   The following quarter is optional only when complete output can still be built.
5. **Post-fetch unknown-calendar checks:** `refresh_mutable=False` previously
   ignored mutable dates only for known schedules. Apply the closed-date bound to
   unknown-calendar request coverage as well, avoiding false incomplete failures.

## Validation

- Frozen runtime/test environment, restored after disposable PostgreSQL testing:
  **599 passed, 100 integration tests deselected**.
- Ruff lint and format checks: pass, **183 files**.
- Full-runtime mypy: pass, **118 source files**.
- `git diff --check`: pass.
- **10 real disposable PostgreSQL tests passed**: existing scheduler CRUD, five
  data shapes through COPY/upsert/read/Parquet and metadata export, concurrent
  transaction-local staging (including preservation of a legacy public staging
  table), rollback on partial Treasury coverage, and recovery from a real SQL
  transaction-abort error.
- Docker was not available. The PostgreSQL tests were run through a temporary
  out-of-repository harness replacing the container lifecycle with fresh
  `pgserver==0.1.4` socket-only PostgreSQL instances. Every instance was stopped
  and deleted. This exercised ordinary PostgreSQL semantics, not the Docker image
  or TimescaleDB extension, hypertable, compression, or migration behavior.
  The committed opt-in tests use explicit disposable `postgres:16-alpine`
  containers and no operator database environment variables.
- Offline tests used a scratch HOME and scrubbed environment. A new negative
  regression initially lacked a connection mock and attempted the default
  localhost connection; it was interrupted before any SQL. No ambient database
  or LSEG environment variables were present. The regression now explicitly
  mocks database access and subsequent runs also set an unreachable test socket.

No production database access/migration, live provider extraction, deployment,
or production credential use was performed. Test logs for this local review:
`/tmp/lseg-dustoff-final-tests.log`, `/tmp/lseg-dustoff-postgres-tests.log`.

## Remaining operator follow-up / limitations

- Provision the new `fetch_coverage` table via the normal reviewed schema process
  before using the updated cache/scheduler. This review did not run that process.
- Migrate existing persisted numeric weekday cron strings separately; source
  defaults do not rewrite stored jobs.
- Previously stored continuous histories and exports require a separate audit;
  code fixes do not rebuild or repair them.
- Unknown calendars prove successful requested intervals, not every expected bar.
  Non-Treasury continuous histories receive observed-date checks, not an exchange
  calendar completeness guarantee. Intraday bars do not receive a new inferred
  market calendar.
- Live LSEG/archive naming, Bloomberg, and full TimescaleDB deployment remain
  unvalidated in this merge review. Expiry/fixed-day pipeline rolling remains
  intentionally rejected without verified exchange metadata.
