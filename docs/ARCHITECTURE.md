# Architecture

Current subsystem map for `jl-lseg-toolkit`.

## Overview

The repo now has two major surfaces:

1. **Core LSEG client + report tools**
   - earnings reporting
   - equity screening
   - financial ratios / consensus / point-in-time snapshots
2. **Timeseries platform**
   - extraction
   - TimescaleDB/PostgreSQL storage
   - scheduler-driven collection
   - Fed Funds / FOMC support
   - Kalshi / Polymarket / FedWatch workflows

## CLI entrypoints

| Command | Layer |
|---------|-------|
| `lseg-setup` | LSEG app-key configuration |
| `lseg-earnings` | Earnings report pipeline |
| `lseg-screener` | Equity screener pipeline |
| `lseg-extract` | Timeseries extraction pipeline |
| `lseg-scheduler` | Scheduler management / daemon control |

## Top-level package structure

```text
src/lseg_toolkit/
├── client/                 # Modular LSEG client implementation
├── earnings/               # Earnings CLI + pipeline
├── equity_screener/        # Screener CLI + pipeline
├── timeseries/             # Main market-data platform
│   ├── cache.py
│   ├── fetch.py
│   ├── pipeline.py
│   ├── rolling.py
│   ├── storage/
│   ├── scheduler/
│   ├── fed_funds/
│   ├── fomc/
│   ├── prediction_markets/
│   ├── bond_basis/
│   └── stir_futures/
├── bonds/                  # Treasury-related helpers
├── shared/                 # Shared utility code
├── excel.py                # Workbook export helpers
└── exceptions.py           # Shared exceptions
```

## External systems

| System | Purpose |
|--------|---------|
| LSEG Workspace local API (`localhost:9000`) | Primary market-data and reference-data source |
| TimescaleDB / PostgreSQL | Durable storage for timeseries, scheduler, FOMC, and PM state |
| Kalshi public APIs | Prediction-market metadata and candles |
| Polymarket Gamma / Data / CLOB APIs | Event metadata, trades, and orderbook enrichment |
| FedWatch input files | Comparison reference data for FOMC probabilities |

## Main data flows

### Earnings / screener

```text
CLI -> config -> pipeline -> LsegClient -> LSEG Workspace -> DataFrame processing -> Excel export
```

### Timeseries extraction

```text
CLI -> TimeSeriesConfig -> TimeSeriesExtractionPipeline
    -> symbol resolution / fetch
    -> optional continuous-contract logic
    -> save to TimescaleDB + optional Parquet export
```

### Scheduler

```text
lseg-scheduler -> scheduler_jobs + scheduler_state + scheduler_runs
               -> build universe from scheduler/universes.py
               -> run extraction jobs -> update retry / success state
```

### Prediction markets

```text
FOMC sync + Kalshi/Polymarket ingest -> prediction-market schema tables
                                     -> comparison helpers (FedWatch / implied distributions)
```

## Storage boundaries

The database layer is split conceptually into four domains:
- instrument registry + typed detail tables
- unified `timeseries_*` fact tables
- scheduler state tables
- FOMC / prediction-market tables

See [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md) for the current schema summary.

## Design notes

- **Client modules stay focused**: earnings, financials, consensus, etc. live in
  separate `client/` modules.
- **Timeseries is a first-class subsystem**: it is no longer just an appendix to
  the original earnings/screener code.
- **Schema is explicit**: the authoritative DDL lives in
  `src/lseg_toolkit/timeseries/storage/pg_schema.py` and
  `src/lseg_toolkit/timeseries/prediction_markets/schema.py`.
- **Contributor validation is CI-shaped**: use `make ci-local`, not ad-hoc tool
  invocations, when checking whether a change is ready to push.
