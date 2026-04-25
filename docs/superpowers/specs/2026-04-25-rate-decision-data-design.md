# Rate-Decision Data Design

**Date:** 2026-04-25
**Author:** brainstormed via Claude
**Status:** Draft — pending user review

## Goal

Stand up enough TimescaleDB-resident data to support central-bank rate-decision probability modeling (executed in a separate repo) for **US, EU, UK, and CA**. Backfill ~1Y of history and register scheduler jobs so the modeling repo always sees fresh data.

## Non-goals

- Probability modeling itself (lives in another repo).
- Any changes to `fomc_meetings`, prediction-market tables, or non-rate instruments.
- Coverage beyond US/EU/UK/CA.
- Integration tests against live LSEG/FRED in CI.

## Current state

The repo already has:
- Validated OIS RICs for USD, GBP, CAD (full curves 1M–30Y).
- Validated overnight benchmarks: `USDSOFR=`, `USONFFE=`, `EUROSTR=`, `GBPOND=`, `CADCORRA=`.
- EURIBOR fixings (1M, 3M, 6M, 12M) and futures (`FEIc1` continuous, `0#FEI:` chain).
- Storage tables `timeseries_rate`, `timeseries_fixing`, plus `fomc_meetings`.
- Scheduler infrastructure with universe groups `ois_usd`, `ois_eur`, `ois_gbp`, `ois_g7`, `benchmark_fixings`, `euribor_fixings`.

Known gaps that this spec closes:
1. **EUR OIS short-end**: `EUR{tenor}OIS=` is broken; `docs/instruments/OVERVIEW.md:43` notes `EUREST{tenor}=` as the proper pattern but it was never validated. `_build_ois_eur` (`scheduler/universes.py:306`) still uses the broken pattern.
2. **No central-bank meeting calendars** for ECB, BoE, BoC.
3. **No codified seed for rate-decision modeling jobs** — current setup requires manual `add-job` invocations.

## Phase 1 — Validate `EUREST{tenor}=`

Standalone probe script `dev_scripts/validate_eurest_ois.py` (gitignored per CLAUDE.md). Fetches 30 calendar days of daily history for each tenor in `[1W, 1M, 2M, 3M, 6M, 9M, 12M, 18M, 2Y]` via `get_client().fetch_timeseries()`. **No DB writes.** Logs per-tenor: row count, last value, last date.

**Decision rule** (sub-1Y is what matters for meeting pricing):
- ✅ **Full success**: ≥4 of `{1W, 1M, 3M, 6M, 12M}` return non-empty data.
- ⚠️ **Partial success**: 1–3 of those tenors work. Use whichever subset works; document gaps in `RATES.md`.
- ❌ **Failure**: 0 sub-1Y tenors work. Skip phase 2 entirely; document in `RATES.md` and `OVERVIEW.md`; user relies on EURIBOR fixings + `FEIc1` for short-end EUR.

## Phase 2 — EUR RIC pattern fix (conditional)

If phase 1 returned ✅ or ⚠️:

```python
# src/lseg_toolkit/timeseries/constants.py — new
EUR_OIS_TENORS: list[str] = [<validated tenors from phase 1>]
def get_eur_ois_ric(tenor: str) -> str:
    return f"EUREST{tenor}="
```

```python
# src/lseg_toolkit/timeseries/scheduler/universes.py:306 — _build_ois_eur
ric=get_eur_ois_ric(tenor),  # was: get_ois_ric("EUR", tenor)
```

Function signature unchanged; downstream callers don't change. Remove the `# Note: Short-end (< 1Y) not available - use EURIBOR for short rates` comment at `constants.py:569`.

If phase 1 returned ❌: no code change. The seed command (phase 4) skips `ois_eur_daily`.

## Phase 3 — Central-bank meeting tables

Three new tables in `src/lseg_toolkit/timeseries/storage/pg_schema.py`, column-identical to `fomc_meetings`:

```sql
CREATE TABLE IF NOT EXISTS <cb>_meetings (
    id SERIAL PRIMARY KEY,
    meeting_date DATE NOT NULL UNIQUE,
    meeting_start_date DATE,
    rate_upper DOUBLE PRECISION,
    rate_lower DOUBLE PRECISION,
    rate_change_bps INTEGER,
    decision TEXT,                  -- 'cut', 'hike', 'hold'
    dissent_count INTEGER DEFAULT 0,
    vote_for INTEGER,
    vote_against INTEGER,
    statement_url TEXT,
    minutes_url TEXT,
    is_scheduled BOOLEAN DEFAULT TRUE,
    has_sep BOOLEAN DEFAULT FALSE,
    has_presser BOOLEAN DEFAULT FALSE,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_<cb>_meetings_date     ON <cb>_meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_<cb>_meetings_decision ON <cb>_meetings(decision);
```

Tables: `ecb_meetings`, `boe_meetings`, `boc_meetings`.

**Single-rate CBs (BoE, BoC):** `rate_upper == rate_lower == policy_rate`.
**ECB:** both columns store the **deposit facility rate** — this is what ESTR tracks. MRO and marginal-lending rates are intentionally omitted to avoid scope creep; columns can be added later if needed.

**Module layout** (mirrors `timeseries/fomc/` exactly):

```
src/lseg_toolkit/timeseries/ecb/  {__init__, calendar_scraper, fetcher, models, storage}.py
src/lseg_toolkit/timeseries/boe/  {__init__, calendar_scraper, fetcher, models, storage}.py
src/lseg_toolkit/timeseries/boc/  {__init__, calendar_scraper, fetcher, models, storage}.py
```

Each package exposes a `sync_<cb>_meetings(conn)` upsert function (`ON CONFLICT (meeting_date) DO UPDATE`). Re-runnable.

**Data sources:**

| CB | Calendar source | Rate-history source |
|---|---|---|
| ECB | `ecb.europa.eu` calendar page (HTML scrape) | FRED `ECBDFR` (Deposit Facility Rate) |
| BoE | `bankofengland.co.uk` MPC calendar | FRED `IUDSOIA` (Bank Rate) |
| BoC | `bankofcanada.ca` Fixed Announcement Dates page | BoC Valet API series `V39079` (Target Overnight) |

FRED dependency matches the existing FOMC fetcher pattern. Same key-handling behavior as `fomc/fetcher.py:178`: missing FRED key downgrades to "calendar dates only, no rate history" — non-fatal, fillable on a later run.

> **Verify at implementation time:** the FRED series IDs above (`ECBDFR`, `IUDSOIA`) are best-current-knowledge — confirm against FRED before wiring. The BoC Valet series ID `V39079` should likewise be confirmed against `https://www.bankofcanada.ca/valet/`. If any series turns out to be wrong or paywalled, fall back to scraping the CB's own published rate history; record the change in the seeder docstring.

**Idiosyncrasies — handled in seeders, marked `is_scheduled=FALSE`:**
- BoE: emergency MPC 2022-09-22 (mini-budget); inter-meeting cuts during pandemic.
- BoC: 2020-03-04, 2020-03-13, 2020-03-27 inter-meeting cuts.
- ECB: pre-2025 cadence was ~6 weeks (this is informational, not a special case in code).

**Historical scope per CB:** all completed meetings within last 1Y + all CB-published future meetings (typically 12–24 months ahead).

## Phase 4 — Seed CLI subcommand

New subcommand in `src/lseg_toolkit/timeseries/scheduler/cli.py`, placed next to `cmd_seed_ff_strip` (`cli.py:350`):

```bash
uv run lseg-scheduler seed-rate-decision-modeling [--skip-eur-ois]
```

Implementation: Python function that calls the existing `add_job` helper in a loop. Idempotent — skips any job whose `name` already exists. `--skip-eur-ois` is set automatically when `EUR_OIS_TENORS` is missing from `constants.py` or evaluates to an empty list (i.e., phase 1 not yet run, or phase 1 returned ❌). When auto-skip triggers, the command logs a single warning line and continues with the other 5 jobs.

**Jobs registered** (defaults; flags allow per-job override):

| Name | Group | Granularity | Cron | Lookback (days) |
|---|---|---|---|---|
| `ois_usd_daily` | `ois_usd` | daily | `0 22 * * 1-5` | 365 |
| `ois_eur_daily` | `ois_eur` | daily | `0 22 * * 1-5` | 365 |
| `ois_gbp_daily` | `ois_gbp` | daily | `0 22 * * 1-5` | 365 |
| `ois_g7_daily` | `ois_g7` | daily | `0 22 * * 1-5` | 365 |
| `benchmark_fixings_daily` | `benchmark_fixings` | daily | `0 22 * * 1-5` | 365 |
| `euribor_fixings_daily` | `euribor_fixings` | daily | `0 22 * * 1-5` | 365 |

22:00 UTC is after US close, before APAC open — matches existing daily-job patterns.

## Phase 5 — Backfill execution

After phase 4, run each job once to fulfill the 1Y backfill:

```bash
for j in ois_usd_daily ois_eur_daily ois_gbp_daily ois_g7_daily \
         benchmark_fixings_daily euribor_fixings_daily; do
  uv run lseg-scheduler run "$j"
done
```

(Skip `ois_eur_daily` if phase 1 failed.)

Existing chunking, retry, and `scheduler_state` machinery handle weekends, holidays, and partial RIC failures.

**Meeting-table backfill** (separate from scheduler):

```bash
uv run python -c "
from lseg_toolkit.timeseries.storage import get_connection
from lseg_toolkit.timeseries.ecb import sync_ecb_meetings
from lseg_toolkit.timeseries.boe import sync_boe_meetings
from lseg_toolkit.timeseries.boc import sync_boc_meetings
with get_connection() as c:
    sync_ecb_meetings(c)
    sync_boe_meetings(c)
    sync_boc_meetings(c)
"
```

A small CLI wrapper can come later if you find yourself running this often. Out of scope for this spec.

## Error handling

- **EUREST validation failure** — script logs per-tenor result, exits 0 (informational, not an error). Decision logic baked into the `--skip-eur-ois` flag.
- **Scheduler RIC failures** — handled by existing machinery: per-instrument `consecutive_failures` counter in `scheduler_state`, exponential backoff via `next_retry_at`, error captured in `error_message`. No new code.
- **Meeting-calendar scrape failure** — seeders raise on HTTP errors; FRED unavailability degrades to "calendar dates only, no rate history" matching the FOMC fetcher pattern (`fomc/fetcher.py:178`). Re-running fills the gap once FRED is reachable.
- **Idempotency** — meeting upserts use `ON CONFLICT (meeting_date) DO UPDATE`; seed command checks job name before insert. Re-running anything is safe.

## Testing

Match the existing FOMC test posture (no integration tests in CI; deterministic units + manual smoke):

- **Unit:** schema migration applies cleanly (existing `pg_schema` test pattern).
- **Unit:** meeting-record upsert is idempotent.
- **Unit:** seed command is idempotent — invoking twice doesn't duplicate jobs.
- **Unit:** each CB seeder parses a fixed HTML/JSON fixture into the expected `<CB>Meeting` objects (mirrors FOMC fixture-based parsing tests).
- **Smoke (manual, post-deploy):** run validation script → run seed command → inspect `scheduler_jobs` and the three meeting tables → run one job and confirm rows land in `timeseries_rate` / `timeseries_fixing`.

## Documentation deliverables

All are part of the implementation, not optional follow-ups:

- `docs/instruments/RATES.md` — replace EUR-OIS section with phase-1 validation results table; date-stamp.
- `docs/instruments/OVERVIEW.md` — confirm or downgrade the `EUREST{tenor}=` row at `OVERVIEW.md:43` based on phase 1 result.
- `docs/STORAGE_SCHEMA.md` — add `ecb_meetings`, `boe_meetings`, `boc_meetings` to section 4.
- `docs/SCHEDULER.md` — add `seed-rate-decision-modeling` to the commands table.
- `src/lseg_toolkit/timeseries/constants.py:569` — remove the "short-end not available — use EURIBOR" comment if EUREST validates.

## Files touched

**New:**
- `dev_scripts/validate_eurest_ois.py` (gitignored)
- `src/lseg_toolkit/timeseries/ecb/{__init__,calendar_scraper,fetcher,models,storage}.py`
- `src/lseg_toolkit/timeseries/boe/{__init__,calendar_scraper,fetcher,models,storage}.py`
- `src/lseg_toolkit/timeseries/boc/{__init__,calendar_scraper,fetcher,models,storage}.py`
- Test files mirroring `tests/timeseries/test_fomc*.py`

**Edited:**
- `src/lseg_toolkit/timeseries/constants.py` — add `EUR_OIS_TENORS`, `get_eur_ois_ric`; remove obsolete comment (conditional on phase 1).
- `src/lseg_toolkit/timeseries/scheduler/universes.py` — fix `_build_ois_eur` (conditional on phase 1).
- `src/lseg_toolkit/timeseries/scheduler/cli.py` — add `cmd_seed_rate_decision_modeling` + arg parsing.
- `src/lseg_toolkit/timeseries/storage/pg_schema.py` — add three new `<cb>_meetings` tables.
- `docs/instruments/RATES.md`, `docs/instruments/OVERVIEW.md`, `docs/STORAGE_SCHEMA.md`, `docs/SCHEDULER.md`.

## Open questions

None blocking. Two notes:

1. **Phase-1 outcome** determines two conditional code paths (phase 2 code edits + phase 4 job inclusion). Both are spelled out above.
2. **External data-source IDs** (FRED series, BoC Valet series) should be confirmed at implementation time — see callout in phase 3.
