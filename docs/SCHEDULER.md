# Scheduler Documentation

Reference for `lseg-scheduler` and the scheduler tables/state model.

## Scope

The scheduler manages recurring timeseries extraction jobs backed by the same
TimescaleDB/PostgreSQL storage layer used by `lseg-extract`.

## Quick start

```bash
export POSTGRES_HOST=timescaledb.example.com
export POSTGRES_PORT=5432
export POSTGRES_USER=timescale
export POSTGRES_PASSWORD=example
export POSTGRES_DB=jlfinance

# List groups
uv run lseg-scheduler groups

# Seed default Fed Funds strip jobs
uv run lseg-scheduler seed-ff-strip

# Add a job
uv run lseg-scheduler add-job \
  --name benchmark_daily \
  --group benchmark_fixings \
  --granularity daily \
  --cron "0 18 * * 1-5"

# Run manually
uv run lseg-scheduler run benchmark_daily

# Start daemon
uv run lseg-scheduler start --foreground
```

## Commands

| Command | Purpose |
|---------|---------|
| `groups` | List available instrument groups |
| `jobs` | List configured jobs |
| `add-job` | Create a job |
| `seed-ff-strip` | Seed default Fed Funds strip jobs |
| `enable` / `disable` | Toggle a job |
| `delete-job` | Delete a job |
| `run` | Run a job immediately |
| `status` | Show enabled jobs and recent runs |
| `state` | Show extraction state per instrument |
| `reset` | Reset failures for a specific instrument |
| `history` | Show recent run history |
| `start` | Start the scheduler daemon |

> The current CLI does **not** implement a distinct background mode. `start`
> runs the daemon in the foreground.

## Available group families

The full list is defined in `timeseries/scheduler/universes.py` and can be
printed with `uv run lseg-scheduler groups`.

Current groups include:
- `treasury_futures`
- `european_bond_futures`
- `asian_bond_futures`
- `index_futures`
- `fx_futures`
- `commodity_futures`
- `stir_futures`
- `stir_ff`
- `fx_spot`
- `ois_usd`, `ois_eur`, `ois_gbp`, `ois_g7`
- `irs_usd`, `irs_eur`, `irs_gbp`
- `fra_usd`, `fra_eur`, `fra_gbp`
- `repo_usd`
- `ust_yields`, `de_yields`, `gb_yields`, `sovereign_g7`
- `equity_indices`, `volatility_indices`
- `benchmark_fixings`, `euribor_fixings`

## Configuration

Database credentials may be supplied via either `TSDB_*` or `POSTGRES_*`
variables.

Common scheduler settings:
- `SCHEDULER_MAX_WORKERS`
- `SCHEDULER_RATE_LIMIT`
- `SCHEDULER_MAX_RICS_PER_BATCH`
- `SCHEDULER_INTRADAY_RETENTION`

## Schema summary

### `scheduler_jobs`

Stores job definitions such as group, granularity, cron, priority, and chunking
settings.

Key columns:
- `name`
- `description`
- `instrument_group`
- `granularity`
- `schedule_cron`
- `priority`
- `enabled`
- `lookback_days`
- `max_chunk_days`

### `scheduler_state`

Per-job, per-instrument state.

Key columns:
- `job_id`
- `instrument_id`
- `last_success_date`
- `last_attempt_at`
- `last_success_at`
- `consecutive_failures`
- `next_retry_at`
- `error_message`

### `scheduler_runs`

Audit/history table for job executions.

Key columns:
- `job_id`
- `started_at`
- `completed_at`
- `status`
- `instruments_total`
- `instruments_success`
- `instruments_failed`
- `rows_extracted`
- `error_summary`

## Operating model

1. build an instrument universe from `universes.py`
2. fetch gaps/lookback windows
3. extract data in chunks
4. save results into the appropriate `timeseries_*` table
5. update `scheduler_state` and `scheduler_runs`

See [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md) for the broader database model.
