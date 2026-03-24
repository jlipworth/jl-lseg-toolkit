# Troubleshooting Guide

Common issues and solutions for `jl-lseg-toolkit`.

## Quick diagnostics

```bash
# LSEG Workspace should answer on localhost
curl -v --connect-timeout 5 http://localhost:9000

# Project Python session check
uv run python -c "import lseg.data as rd; rd.open_session(); print('Session opened successfully'); rd.close_session()"
```

## LSEG connection issues

### "Connection refused"

Cause: LSEG Workspace Desktop is not running or not logged in.

Fix:
1. start LSEG Workspace Desktop
2. log in fully
3. retry the quick diagnostics above

### "Invalid ApplicationId" / missing app key

```bash
uv run lseg-setup
```

You can also create `~/.lseg/config.json` manually if needed.

### WSL2 localhost issues

If you see localhost restrictions or routing problems, go to
[GETTING_STARTED.md](GETTING_STARTED.md). That is the canonical WSL2 setup doc.

## Timeseries / database issues

### Database connection failures

Symptoms:
- `psycopg` connection errors
- scheduler commands fail before doing any work
- extraction can fetch from LSEG but cannot persist

Checks:
- verify `TSDB_*` or `POSTGRES_*` env vars
- verify the target database is reachable from your shell
- verify required schema has been initialized

### Wrong or missing table expectations

The current fact tables are:
- `timeseries_ohlcv`
- `timeseries_quote`
- `timeseries_rate`
- `timeseries_bond`
- `timeseries_fixing`

If docs/code/examples mention older names, trust the current schema files and
`docs/STORAGE_SCHEMA.md`.

## Scheduler issues

### Jobs exist but do not run as expected

Checks:
- `uv run lseg-scheduler jobs --all`
- `uv run lseg-scheduler status`
- `uv run lseg-scheduler history --limit 20`
- `uv run lseg-scheduler state --failed`

### Repeated instrument failures

Use:

```bash
uv run lseg-scheduler state --failed
uv run lseg-scheduler reset --job <job> --symbol <symbol>
```

Also verify:
- symbol/group is still supported
- database writes are succeeding
- your LSEG session is healthy

## Prediction-market ingestion issues

### Kalshi freshness looks stale

For Kalshi rate products, prefer `pm_markets.last_trade_time` over source
`updated_time` when reasoning about market freshness.

### Polymarket linkage is ambiguous

That is expected in some cases. The repo intentionally keeps automatic
Polymarket resolution conservative. Use:
- `docs/PREDICTION_MARKETS.md`
- `docs/POLYMARKET_RESOLUTION.md`
- `docs/TEMP_POLYMARKET_FOMC_LINKS.md`

## Getting help

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [TIMESERIES.md](TIMESERIES.md)
- [SCHEDULER.md](SCHEDULER.md)
- [PREDICTION_MARKETS.md](PREDICTION_MARKETS.md)
- [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md)
