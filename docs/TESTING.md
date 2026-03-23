# Testing Guide

This document describes the test infrastructure, conventions, and best practices for `jl-lseg-toolkit`.

## Quick Reference

```bash
# Mirror Woodpecker CI locally
make ci-local

# Run all tests (including integration - requires LSEG Workspace)
uv run pytest tests/ --no-cov

# Run unit tests only (CI behavior - no LSEG required)
uv run pytest tests/ -m "not integration" --no-cov

# Run integration tests only
uv run pytest tests/ -m "integration" -v

# Run specific test file
uv run pytest tests/test_client.py -v

# Run tests matching a pattern
uv run pytest tests/ -k "earnings" -v
```

### Prediction-markets quick commands

```bash
# Kalshi + Polymarket prediction-market unit tests
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

# Polymarket-focused tests only
uv run pytest tests/timeseries/test_polymarket_client.py \
  tests/timeseries/test_polymarket_extractor.py \
  tests/timeseries/test_polymarket_trades.py \
  tests/timeseries/test_polymarket_resolution.py \
  tests/timeseries/test_polymarket_candles_orchestration.py \
  tests/timeseries/test_polymarket_workflow.py -v
```

---

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and pytest configuration
├── helpers.py            # Common assertion helpers
├── test_client.py        # Core LsegClient tests
├── test_earnings_client.py  # Earnings data retrieval
├── test_financial_data.py   # Financial ratios, estimates
├── test_index_availability.py  # Index constituent tests
├── earnings/             # Earnings pipeline tests
│   ├── test_pipeline.py
│   └── test_pipeline_data_quality.py
├── equity_screener/      # Equity screener tests
│   ├── test_config.py
│   └── test_data_quality.py
└── timeseries/           # Timeseries module tests
    ├── test_cache.py
    ├── test_duckdb_storage.py
    ├── test_models.py
    ├── test_rolling.py
    └── test_storage.py
```

---

## Test Markers

We use pytest markers to categorize tests:

| Marker | Description | Requires |
|--------|-------------|----------|
| `@pytest.mark.integration` | Tests that call the real LSEG API | LSEG Workspace running |
| `@pytest.mark.slow` | Long-running tests | Nothing special |
| `@pytest.mark.unit` | Pure unit tests (no I/O) | Nothing special |

### Usage

```python
import pytest

@pytest.mark.integration
def test_fetch_real_data(lseg_client_class):
    """This test calls the real API."""
    ...

@pytest.mark.unit
def test_parse_date():
    """This test is pure Python logic."""
    ...
```

### CI Behavior

The CI pipeline (`.woodpecker/ci.yml`) runs:
```bash
pytest tests/ -m "not integration" --no-cov
```

This skips all integration tests since LSEG Workspace is not available in CI.

To mirror the full Woodpecker pipeline locally with the same frozen
test-only dependency group, run:

```bash
make ci-local
```

---

## Fixtures

All shared fixtures are defined in `tests/conftest.py`.

### LSEG Client Fixtures

| Fixture | Scope | Use Case |
|---------|-------|----------|
| `lseg_client_session` | session | Shared across all tests (read-only operations) |
| `lseg_client_class` | class | Shared across tests in a test class |
| `lseg_client` | function | Fresh client per test (when isolation needed) |

```python
class TestMyFeature:
    def test_something(self, lseg_client_class):
        """Uses class-scoped client (recommended for most tests)."""
        result = lseg_client_class.get_index_constituents("SPX")
        assert len(result) > 0
```

### Data Fixtures

| Fixture | Returns |
|---------|---------|
| `sample_tickers_us` | `["AAPL.O", "MSFT.O", "GOOGL.O"]` |
| `sample_tickers_global` | US, UK, Japan tickers |
| `sample_ticker_single` | `"AAPL.O"` |
| `major_indices` | `["SPX", "NDX", "DJI", "STOXX", "FTSE"]` |
| `small_index` | `"DJI"` (Dow 30, for faster tests) |

### Date Fixtures

| Fixture | Returns |
|---------|---------|
| `current_week_dates` | Dict with start_date, end_date, monday, sunday |
| `snapshot_date` | Sunday before current week (YYYY-MM-DD string) |
| `past_date_range` | Dict with historical start_date, end_date |

---

## Helper Functions

Common assertion patterns are in `tests/helpers.py`:

```python
from tests.helpers import (
    assert_dataframe_columns,
    assert_no_nulls,
    assert_date_range,
    assert_dataframe_not_empty,
    assert_column_numeric,
    assert_column_values_in,
    assert_unique_column,
)

def test_earnings_data(lseg_client_class):
    df = lseg_client_class.get_earnings_data(["AAPL.O"])

    # Check required columns exist
    assert_dataframe_columns(df, ["Instrument", "Event Start Date"])

    # Check no nulls in key columns
    assert_no_nulls(df, ["Instrument"])

    # Check dates are in expected range
    assert_date_range(df, "Event Start Date", start="2024-01-01")
```

---

## Test Patterns

### Integration Tests (Real API)

```python
pytestmark = pytest.mark.integration  # Mark entire file

class TestEarningsData:
    def test_get_earnings_basic(self, lseg_client_class):
        df = lseg_client_class.get_earnings_data(["AAPL.O"])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
```

### Unit Tests (Mocked)

```python
from unittest.mock import MagicMock, patch

@pytest.mark.unit
def test_parse_response():
    mock_response = pd.DataFrame({"A": [1, 2, 3]})

    with patch("lseg_toolkit.client.rd.get_data", return_value=mock_response):
        result = some_function()
        assert result == expected
```

### Parametrized Tests

```python
@pytest.mark.parametrize("index_code,min_size,max_size", [
    ("SPX", 400, 600),
    ("NDX", 80, 120),
    ("DJI", 25, 35),
], ids=["SPX", "NDX", "DJI"])
def test_index_size(self, lseg_client_class, index_code, min_size, max_size):
    rics = lseg_client_class.get_index_constituents(index_code)
    assert min_size <= len(rics) <= max_size
```

---

## Writing New Tests

### 1. Choose the Right Marker

- Uses LSEG API? → `@pytest.mark.integration`
- Pure logic? → `@pytest.mark.unit`
- Takes >5 seconds? → `@pytest.mark.slow`

### 2. Use Appropriate Fixtures

- Most integration tests: `lseg_client_class`
- Need isolation: `lseg_client`
- Session-wide caching: `lseg_client_session`

### 3. Use Helper Functions

Prefer `assert_dataframe_columns()` over manual column checks.

### 4. Keep Tests Focused

One logical assertion per test. Use descriptive names:
- `test_get_earnings_returns_dataframe` ✓
- `test_earnings` ✗

### 5. Add IDs to Parametrized Tests

```python
@pytest.mark.parametrize("value", [1, 2, 3], ids=["one", "two", "three"])
```

---

## Common Issues

### "No session" Errors

LSEG Workspace must be running at `localhost:9000`. See [WSL_SETUP.md](WSL_SETUP.md).

### Slow Tests

Use the `small_index` fixture (DJI with 30 stocks) instead of SPX (500+).

### Flaky Integration Tests

Network issues can cause intermittent failures. Consider:
- Adding retries for specific error types
- Using wider date ranges for time-sensitive data

### Prediction-market troubleshooting tests

When changing Polymarket schema/normalization/resolution behavior, rerun at
minimum:

- `tests/timeseries/test_pm_models.py`
- `tests/timeseries/test_pm_schema.py`
- `tests/timeseries/test_pm_storage.py`
- `tests/timeseries/test_polymarket_client.py`
- `tests/timeseries/test_polymarket_extractor.py`
- `tests/timeseries/test_polymarket_trades.py`
- `tests/timeseries/test_polymarket_resolution.py`
- `tests/timeseries/test_polymarket_candles_orchestration.py`
- `tests/timeseries/test_polymarket_workflow.py`

If Kalshi comparison behavior is involved, also rerun:

- `tests/timeseries/test_kalshi_client.py`
- `tests/timeseries/test_kalshi_extractor.py`

---

## Running in CI

CI automatically skips integration tests. To simulate CI locally:

```bash
uv run pytest tests/ -m "not integration" --no-cov
```

To verify integration tests work:

```bash
# Start LSEG Workspace, then:
uv run pytest tests/ -m "integration" -v
```
