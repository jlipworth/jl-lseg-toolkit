# Testing Guide

This document describes the test workflow for `jl-lseg-toolkit`.

## Quick reference

```bash
# Exact local mirror of Woodpecker CI
make ci-local

# All tests (includes integration; requires LSEG Workspace)
uv run pytest tests/ --no-cov

# Unit-test CI slice only
uv run pytest tests/ -m "not integration" --no-cov

# Integration tests only
uv run pytest tests/ -m "integration" -v
```

## What CI actually runs

Woodpecker currently checks:

```bash
uv sync --frozen --only-group test
ruff check src/ tests/
ruff format --check src/ tests/
MYPYPATH=src mypy src/
pytest tests/ -m "not integration" --no-cov -v
```

So if you want one reliable pre-push command, use:

```bash
make ci-local
```

## Test layout

Top-level tests cover:
- core client behavior
- earnings pipeline
- equity screener
- timeseries extraction and storage
- Fed Funds and FOMC workflows
- scheduler behavior
- Kalshi / Polymarket / FedWatch logic

Current timeseries suite includes files such as:
- `tests/timeseries/test_cache.py`
- `tests/timeseries/test_cli.py`
- `tests/timeseries/test_fetch.py`
- `tests/timeseries/test_storage.py`
- `tests/timeseries/test_scheduler.py`
- `tests/timeseries/test_fed_funds_extraction.py`
- `tests/timeseries/test_fomc.py`
- `tests/timeseries/test_kalshi_*.py`
- `tests/timeseries/test_polymarket_*.py`
- `tests/timeseries/test_fedwatch_loader.py`

## Markers

| Marker | Meaning |
|--------|---------|
| `integration` | Calls real external systems, especially LSEG Workspace |
| `unit` | Pure logic/unit test |
| `slow` | Longer-running test |

Examples:

```bash
uv run pytest tests/ -m "not integration"
uv run pytest tests/ -m "integration"
uv run pytest tests/ -k "polymarket"
```

## Prediction-markets focused commands

```bash
uv run pytest tests/timeseries/test_pm_models.py \
  tests/timeseries/test_pm_schema.py \
  tests/timeseries/test_pm_storage.py \
  tests/timeseries/test_kalshi_client.py \
  tests/timeseries/test_kalshi_extractor.py \
  tests/timeseries/test_polymarket_client.py \
  tests/timeseries/test_polymarket_extractor.py \
  tests/timeseries/test_polymarket_trades.py \
  tests/timeseries/test_polymarket_resolution.py \
  tests/timeseries/test_polymarket_candles_orchestration.py \
  tests/timeseries/test_polymarket_workflow.py -v
```

### Bloomberg quick commands

```bash
# Supported Bloomberg unit tests
uv run pytest tests/bloomberg/ -v

# Run just the supported Bloomberg CLI/normalization tests
uv run pytest tests/bloomberg/test_cli.py \
  tests/bloomberg/test_connection.py \
  tests/bloomberg/test_normalize.py \
  tests/bloomberg/test_jgb.py \
  tests/bloomberg/test_fx_atm_vol.py -v

# Bloomberg Desktop API smoke tests (opt-in only)
RUN_BLOOMBERG_INTEGRATION=1 uv run pytest tests/bloomberg/test_integration.py -m integration -v
```

Bloomberg live/Desktop-API integration tests should remain opt-in and should not
run in CI by default. For Bloomberg specifically, keep live smoke tests gated
behind `RUN_BLOOMBERG_INTEGRATION=1`.

## When to run what

- Editing docs only: usually no Python test run required, but check examples/commands you changed
- Editing Python code: run targeted pytest + `make ci-local`
- Editing schema/CLI/scheduler behavior: prefer full `make ci-local`
- Editing integration-only behavior: run the relevant integration test manually if you have LSEG access
