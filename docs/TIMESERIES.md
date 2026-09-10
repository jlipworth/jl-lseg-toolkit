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
| `--roll-method` | `volume` for pipeline extraction; other parsed modes require verified expiry metadata and fail explicitly |
| `--roll-days` | Reserved for expiry-aware fixed-day rolling (not available in the extraction pipeline) |
| `--parquet` | Parquet output directory |
| `--no-parquet` | Skip Parquet export |
| `--list` | Print supported instruments |
| `-q` / `--quiet` | Reduce progress output |

There is currently **no** `--ric` flag; if you want to use an explicit RIC,
pass the RIC itself.

Parquet export is enabled by default and reads the full stored history for each
successfully extracted symbol at the selected granularity, so a short update does
not truncate an existing yearly partition. Export errors produce a failed result.
Use `--no-parquet` for database-only extraction.

## Python API

### Cache-first access

```python
from lseg_toolkit.timeseries import DataCache

cache = DataCache()
df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")
```

`DataCache` stores successful request coverage independently from data rows,
including successful empty intervals. Disjoint request ranges remain disjoint;
old rows without coverage metadata are revalidated once rather than treating
MIN/MAX timestamps as proof of completeness. Apply the schema update described in
[Getting Started](GETTING_STARTED.md#provision-storage-before-extraction-or-scheduling)
before using an existing database with this version.

Daily Treasury futures additionally check the CME session calendar for missing
sessions, excluding holidays. Other instruments can set
`CacheConfig(exchange_calendars={"RIC": "exchange_calendars_code"})`, or provide
`expected_timestamps(ric, start, end, granularity)` for exact intraday bar coverage.
Without a known schedule, coverage means **a successful provider request**, not
an independent guarantee that every market bar exists. `FetchResult.coverage_verified`
reports the stronger schedule check. Provider failures retain their errors and
single-instrument APIs raise instead of silently returning partial/empty data.
Current/future dates are not stored as completed coverage and are refreshed.

### Direct client access

```python
from lseg_toolkit.timeseries import get_client

client = get_client()
df = client.get_history("EUR=", start="2026-03-01", end="2026-03-03", interval="hourly")
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

```

Supported adjustment modes:
- `ratio`
- `difference`
- `none`

Library roll modes (only `volume` is supported by the extraction pipeline):
- `volume`
- `first-notice`
- `fixed-days`
- `expiry`

The pipeline enumerates quarterly bond contracts separately for each root,
uses expired RIC suffixes for historical deliveries, and rejects incomplete
required chains rather than storing a misleading partial continuous series.
Expiry, first-notice, and fixed-day pipeline modes are rejected because the end
of a requested history window is not a verified exchange expiry date. Use the
default volume mode; these date-based modes need exchange metadata before they
can be enabled safely in the pipeline.

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

## Parquet exports

The PostgreSQL-backed export supports every stored data shape and field. Daily
files use `daily/<asset_class>/year=YYYY/<escaped-symbol>.parquet`; other intervals
use `intraday/<asset_class>/<interval>/<escaped-symbol>.parquet` under the selected
output directory. The pipeline exports full stored history for each extracted
symbol, avoiding truncation of existing yearly partitions during incremental
runs. Each data-file replacement is atomic.

The export API accepts `config=DatabaseConfig(...)`; legacy `db_path` is ignored
because storage is PostgreSQL-backed. Use `--no-parquet` to skip export.
