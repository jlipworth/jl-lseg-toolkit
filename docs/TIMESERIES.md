# Time Series Extraction

Current reference for the `lseg-extract` and related timeseries APIs.

## Scope

The timeseries subsystem currently covers:
- bond futures
- STIR futures (including Fed Funds continuous ranks)
- FX spot
- OIS curves
- FRAs
- government yields
- storage in TimescaleDB/PostgreSQL
- scheduler-driven extraction

For prediction-market workflows, see [PREDICTION_MARKETS.md](PREDICTION_MARKETS.md).

## Quick start

```bash
# Bond futures
uv run lseg-extract ZN ZB

# FX spot
uv run lseg-extract EURUSD USDJPY --asset-class fx

# Treasury yields (bare tenors default to US Treasuries)
uv run lseg-extract 2Y 5Y 10Y 30Y --asset-class govt-yield

# OIS curve
uv run lseg-extract 1M 3M 1Y 5Y 10Y --asset-class ois

# Fed Funds continuous
uv run lseg-extract FF_CONTINUOUS --asset-class stir --interval hourly --start 2026-03-01 --end 2026-03-03
```

## Supported CLI asset classes

`lseg-extract --asset-class` currently supports:
- `futures`
- `stir`
- `fx`
- `ois`
- `govt-yield`
- `fra`

> `fixing` exists in the broader storage/scheduler model, but is **not**
> currently exposed as a direct `lseg-extract --asset-class fixing` option.

## CLI reference

```text
lseg-extract SYMBOLS... [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--asset-class` | `futures`, `stir`, `fx`, `ois`, `govt-yield`, `fra` |
| `--start` / `--end` | Date range in `YYYY-MM-DD` |
| `--interval` | `tick`, `1min`, `5min`, `10min`, `30min`, `hourly`, `daily`, `weekly`, `monthly` |
| `--continuous` | Build a continuous futures series |
| `--adjust` | `none`, `ratio`, `difference` |
| `--roll-method` | `volume`, `first-notice`, `fixed-days`, `expiry` |
| `--roll-days` | Days-before-expiry when using `fixed-days` |
| `--parquet` | Parquet output directory |
| `--no-parquet` | Skip Parquet export |
| `--list` | Print supported instruments |
| `-q` / `--quiet` | Reduce progress output |

There is currently **no** `--ric` flag; if you want to use an explicit RIC,
pass the RIC itself.

## Python API

### Cache-first access

```python
from lseg_toolkit.timeseries import DataCache

cache = DataCache()
df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")
```

### Direct client access

```python
from lseg_toolkit.timeseries import get_client

client = get_client()
df = client.fetch_timeseries("EUR=", start="2026-03-01", end="2026-03-03", interval="hourly")
```

### Storage access

```python
from lseg_toolkit.timeseries.storage import get_connection, load_timeseries

with get_connection() as conn:
    df = load_timeseries(conn, "ZN")
```

## Storage model

The current timeseries fact tables are unified by data shape:

| Table | Stores |
|-------|--------|
| `timeseries_ohlcv` | futures / index-like OHLCV data |
| `timeseries_quote` | quote-style data such as FX spot |
| `timeseries_rate` | OIS / IRS / FRA / repo-style rate data |
| `timeseries_bond` | sovereign / bond-yield style data |
| `timeseries_fixing` | daily fixings |

Instrument metadata is stored separately in `instruments` plus typed detail
Tables such as `instrument_futures`, `instrument_fx`, `instrument_rate`, and
`instrument_bond`.

See [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md) for the current database summary.

## Continuous contracts

```bash
# Volume-based roll with ratio adjustment
uv run lseg-extract ZN --continuous --adjust ratio --roll-method volume

# Fixed-days roll
uv run lseg-extract ZN --continuous --roll-method fixed-days --roll-days 5
```

Supported adjustment modes:
- `ratio`
- `difference`
- `none`

Supported roll modes:
- `volume`
- `first-notice`
- `fixed-days`
- `expiry`

## Fed Funds notes

Fed Funds continuous ranks are exposed as:
- `FF_CONTINUOUS`
- `FF_CONTINUOUS_2` ... `FF_CONTINUOUS_12`

Related code lives in:
- `timeseries/fed_funds/`
- `timeseries/stir_futures/`
- `timeseries/rolling.py`

## Scheduler / downstream docs

- [SCHEDULER.md](SCHEDULER.md)
- [FF_CONTINUOUS_SMOKE_TEST.md](FF_CONTINUOUS_SMOKE_TEST.md)
- [INSTRUMENTS.md](INSTRUMENTS.md)
