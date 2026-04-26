# Storage Schema

Current database model summary for the repo.

> **Source of truth:**
> - `src/lseg_toolkit/timeseries/storage/pg_schema.py`
> - `src/lseg_toolkit/timeseries/prediction_markets/schema.py`
>
> Keep this document high-level and current; the Python schema files are the
> authoritative DDL.

## Scope

The database now covers four areas:

1. **Instrument registry**
2. **Timeseries fact tables**
3. **Scheduler state**
4. **FOMC + prediction-market data**

## 1. Instrument registry

Core table:
- `instruments`

Typed detail tables currently include:
- `instrument_futures`
- `instrument_fx`
- `instrument_rate`
- `instrument_bond`
- `instrument_fixing`
- `instrument_equity`
- `instrument_etf`
- `instrument_index`
- `instrument_commodity`
- `instrument_cds`
- `instrument_option`

These tables hold instrument-specific metadata while `instruments` provides the
shared identity and classification layer.

## 2. Timeseries fact tables

Current fact tables are grouped by data shape:

| Table | Purpose |
|-------|---------|
| `timeseries_ohlcv` | Futures and other OHLCV-style series |
| `timeseries_quote` | Quote-style series such as FX spot |
| `timeseries_rate` | OIS / IRS / FRA / repo-style rate series |
| `timeseries_bond` | Sovereign/bond yield series |
| `timeseries_fixing` | Daily fixing series |
| `roll_events` | Continuous-contract roll metadata |
| `extraction_progress` | Extraction bookkeeping |

These tables are used by both direct extraction and scheduler workflows.

## 3. Scheduler tables

| Table | Purpose |
|-------|---------|
| `scheduler_jobs` | Job definitions |
| `scheduler_state` | Per-job / per-instrument retry and success state |
| `scheduler_runs` | Run history and audit trail |

Notable current `scheduler_state` columns:
- `last_success_date`
- `last_attempt_at`
- `last_success_at`
- `consecutive_failures`
- `next_retry_at`
- `error_message`

## 4. Central-bank meeting and prediction-market tables

| Table | Purpose |
|-------|---------|
| `fomc_meetings` | FOMC calendar and rate-decision history |
| `ecb_meetings` | ECB Governing Council monetary-policy decisions (Deposit Facility Rate) |
| `boe_meetings` | BoE MPC decisions (Bank Rate) |
| `boc_meetings` | BoC Fixed Announcement Date decisions (Target Overnight Rate) |
| `pm_platforms` | Prediction-market platforms |
| `pm_series` | Event/group layer |
| `pm_markets` | Market/outcome layer |
| `pm_candlesticks` | Stored PM candles |

This is the active schema used by:
- `timeseries/fomc/`, `timeseries/ecb/`, `timeseries/boe/`, `timeseries/boc/`
- `timeseries/prediction_markets/kalshi/`
- `timeseries/prediction_markets/polymarket/`
- comparison helpers such as `compare_markets_to_fedwatch()`

## Recommended reader workflow

- Read this file for the current shape of the schema
- Read `docs/TIMESERIES.md` for extraction/storage behavior
- Read `docs/SCHEDULER.md` for scheduler semantics
- Read `docs/PREDICTION_MARKETS.md` for the PM/FOMC domain model
- Read the schema Python files when you need exact column definitions
