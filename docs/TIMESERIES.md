# Time Series Extraction

Extract historical market data from LSEG for bond futures, FX, OIS curves, government yields, and more.

## Quick Start

```bash
# Extract Treasury futures (last year, daily)
lseg-extract ZN ZB

# FX spot rates
lseg-extract EURUSD USDJPY --asset-class fx

# Treasury yield curve (bare tenors default to US Treasuries)
lseg-extract 2Y 5Y 10Y 30Y --asset-class govt-yield

# Explicit non-US sovereign yields
lseg-extract DE10Y GB10Y --asset-class govt-yield

# OIS curve
lseg-extract 1M 3M 1Y 5Y 10Y --asset-class ois

# List all supported instruments
lseg-extract --list
```

For prediction-market specific reference notes, see
[PREDICTION_MARKETS.md](PREDICTION_MARKETS.md).

## Supported Asset Classes

| Asset Class | Examples | Description |
|-------------|----------|-------------|
| `futures` | ZN, ZB, FGBL, ES | Bond and index futures |
| `stir` | FF_CONTINUOUS | STIR futures (Fed Funds, SOFR family) |
| `fx` | EURUSD, USDJPY | FX spot rates |
| `ois` | 1M, 1Y, 5Y | OIS swap rates (SOFR) |
| `govt-yield` | 2Y, 10Y, 30Y, DE10Y, GB10Y | Bare tenors = US Treasuries; explicit country codes select other sovereigns |
| `fra` | 1X4, 3X6 | Forward Rate Agreements |
| `fixing` | SOFR | Daily rate fixings |

For the complete instrument list with 200+ validated RICs, see [INSTRUMENTS.md](INSTRUMENTS.md).

## CLI Reference

```
lseg-extract SYMBOLS... [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--asset-class` | Asset class: futures, stir, fx, ois, govt-yield, fra (auto-detected if omitted) |
| `--start DATE` | Start date (YYYY-MM-DD, default: 1 year ago) |
| `--end DATE` | End date (YYYY-MM-DD, default: today) |
| `--interval` | Granularity: tick, 1min, 5min, 10min, 30min, hourly, daily, weekly, monthly |
| `--continuous` | Build continuous contract (futures only) |
| `--adjust` | Price adjustment: none, ratio, difference (default: ratio) |
| `--roll-method` | Roll detection: volume, first-notice, fixed-days, expiry |
| `--parquet DIR` | Parquet output directory (default: data/parquet) |
| `--no-parquet` | Skip Parquet export |
| `--list` | Show supported instruments |
| `-q, --quiet` | Suppress progress output |

### Examples

```bash
# Build continuous 10Y future with ratio adjustment
lseg-extract ZN --continuous --adjust ratio

# Intraday FX (5-minute bars, last 30 days)
lseg-extract EURUSD --interval 5min --start 2025-12-01

# Fed Funds continuous (stored as FF_CONTINUOUS)
lseg-extract FF_CONTINUOUS --asset-class stir --interval hourly --start 2026-03-01 --end 2026-03-03

# Full USD OIS curve
lseg-extract 1M 2M 3M 6M 9M 1Y 2Y 3Y 5Y 7Y 10Y 15Y 20Y 30Y --asset-class ois

# Explicit sovereign yields
lseg-extract DE2Y DE5Y DE10Y DE30Y --asset-class govt-yield

# Custom parquet output location
lseg-extract ZN --parquet output/
```

## Python API

### Cache-First Approach (Recommended)

```python
from lseg_toolkit.timeseries import DataCache, CacheConfig

# Create cache with TimescaleDB backend
cache = DataCache()

# Fetch single instrument (uses cache if available)
df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")

# Fetch multiple instruments
results = cache.get_or_fetch_many(
    ["TYc1", "USc1", "FVc1"],
    start="2024-01-01",
    end="2024-12-31"
)

# Async batch fetching (for large portfolios)
import asyncio

async def fetch_portfolio():
    results = await cache.async_get_or_fetch_many(
        ["TYc1", "USc1", "FVc1", "EUR=", "GBP="],
        start="2024-01-01",
        end="2024-12-31"
    )
    return results

results = asyncio.run(fetch_portfolio())
```

### Direct Client Access

```python
from lseg_toolkit.timeseries import LSEGDataClient, get_client

# Get or create singleton client
client = get_client()

# Fetch OHLCV data
df = client.fetch_timeseries(
    ric="TYc1",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)
```

### TimescaleDB Storage

```python
from lseg_toolkit.timeseries.storage import (
    get_connection,
    load_timeseries,
    get_data_range,
    get_instruments,
)

# Query stored data directly
with get_connection() as conn:
    # Load timeseries
    df = load_timeseries(conn, "ZN")

    # Get date range
    start, end = get_data_range(conn, "ZN")

    # List all instruments
    instruments = get_instruments(conn)
```

Configure the database via environment variables:
```bash
export TSDB_HOST=localhost
export TSDB_PORT=5432
export TSDB_DATABASE=timeseries
export TSDB_USER=postgres
export TSDB_PASSWORD=yourpassword
```

These are example values only; you can point the toolkit at your own TimescaleDB/PostgreSQL
instance via `TSDB_*` or the compatible `POSTGRES_*` environment variables.

### Prediction Market Freshness Notes

For Kalshi rate markets (`KXFED`, `KXFEDDECISION`, `KXRATECUTCOUNT`), treat the
source `updated_time` field with caution. In practice, those products can show
stale `updated_time` values even when trades are still printing.

Use `pm_markets.last_trade_time` as the primary freshness signal for active
Kalshi markets. That field is populated from the most recent trade seen during
`daily_refresh()`.

## Storage Architecture

Data is stored in TimescaleDB (PostgreSQL with time-series extensions) using hypertables optimized for different data shapes:

| Hypertable | Data Shape | Asset Classes |
|------------|------------|---------------|
| `ohlcv_daily` | Daily OHLCV bars | Futures, equities, commodities |
| `ohlcv_intraday` | Intraday OHLCV | High-frequency data |
| `quote_daily` | Bid/ask quotes | FX, OIS, IRS, FRA |
| `bond_daily` | Yield + analytics | Government bonds |
| `rate_daily` | Rate quotes | Swaps, repos |
| `fixing_daily` | Daily fixings | SOFR, ESTR, SONIA |

For complete schema details, see [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md).

## Continuous Contracts

For futures, you can build continuous (rolled) contracts:

```bash
# Volume-based roll with ratio adjustment
lseg-extract ZN --continuous --adjust ratio --roll-method volume

# Fixed-days roll (5 days before expiry)
lseg-extract ZN --continuous --roll-method fixed-days --roll-days 5
```

### Adjustment Methods

| Method | Formula | Best For |
|--------|---------|----------|
| `ratio` | `price * (new/old)` | Backtesting (preserves returns) |
| `difference` | `price + (new - old)` | Spread analysis |
| `none` | Raw stitch | Level analysis |

### Roll Methods

| Method | Trigger | Use Case |
|--------|---------|----------|
| `volume` | Back month volume > front | Most liquid transition |
| `first-notice` | Before first notice date | Physical delivery |
| `fixed-days` | N days before expiry | Predictable schedule |
| `expiry` | On expiration | Matches LSEG default |

## Intraday Data

LSEG provides intraday data with these constraints:

- **Retention**: ~365 days for 5min/hourly (verified 2026-01-13)
- **Request limit**: 50,000 bars per request
- **Granularities**: tick, 1min, 5min, 10min, 30min, hourly

```bash
# Last 30 days of 5-minute bars
lseg-extract EURUSD --interval 5min --start $(date -d '-30 days' +%Y-%m-%d)
```

Not all instruments support intraday. See [INSTRUMENTS.md](INSTRUMENTS.md) for the full support matrix.

## Symbol Mapping

Common CME symbols are automatically mapped to LSEG RICs:

| You Type | LSEG RIC | Description |
|----------|----------|-------------|
| ZN | TYc1 | 10-Year Treasury |
| ZB | USc1 | 30-Year Treasury |
| ZF | FVc1 | 5-Year Treasury |
| FF_CONTINUOUS | FFc1 | 30-Day Fed Funds continuous |
| EURUSD | EUR= | EUR/USD spot |
| USDJPY | JPY= | USD/JPY spot |

For explicit RICs, use the `--ric` flag or pass the RIC directly.

## Output Formats

### TimescaleDB (Default)

- **Database**: PostgreSQL with TimescaleDB extension
- **Query**: Use psql CLI, Python API, or any PostgreSQL client
- **Advantages**: Time-series optimized hypertables, continuous aggregates, SQL support

### Parquet

- **Location**: `data/parquet/`
- **Format**: Apache Parquet (columnar)
- **Advantages**: Cross-language (C++, Rust, Python), compressed

## Module Architecture

The timeseries module is located at `src/lseg_toolkit/timeseries/` with this structure:

```
timeseries/
├── __init__.py          # Public API exports
├── cache.py             # DataCache - cache-first data access
├── cli.py               # lseg-extract CLI entry point
├── client.py            # LSEGDataClient - LSEG API wrapper
├── config.py            # TimeSeriesConfig, CacheConfig
├── constants.py         # ⭐ RIC mappings, field lists, month codes
├── enums.py             # Granularity, AssetClass, DataShape enums
├── fetch.py             # Raw data fetching from LSEG
├── pipeline.py          # Extraction orchestration
├── rolling.py           # Continuous contract construction
│
├── storage/             # TimescaleDB/PostgreSQL persistence
│   ├── connection.py    # Database connection pooling
│   ├── instruments.py   # Instrument registry CRUD
│   ├── reader.py        # load_timeseries, get_data_range
│   ├── writer.py        # save_timeseries, bulk inserts
│   └── ...
│
├── scheduler/           # Automated extraction jobs
│   ├── cli.py           # lseg-scheduler CLI
│   ├── daemon.py        # APScheduler daemon
│   ├── jobs.py          # Job execution logic
│   └── universes.py     # Pre-defined instrument universes
│
├── bond_basis/          # Treasury futures basis analysis
│   ├── conversion_factor.py  # CME conversion factor calc
│   └── extractor.py     # Deliverable basket extraction
│
└── stir_futures/        # Short-Term Interest Rate futures
    └── contracts.py     # Contract RIC generation (FF, SRA, FEI, SON)
```

### Key Files

| File | Purpose | When to Read |
|------|---------|--------------|
| `constants.py` | **All RIC mappings** - CME→LSEG, field lists, month codes | Before adding new instruments |
| `enums.py` | Asset classes, granularities, data shapes | Understanding data types |
| `config.py` | Configuration dataclasses | Customizing behavior |
| `storage/instruments.py` | Instrument registry | Adding new asset types |

### Submodule Dependencies

```
constants.py
    ↓
stir_futures/contracts.py  (imports FUTURES_MONTH_CODES, STIR_FUTURES_RICS)
bond_basis/extractor.py    (imports CME_TO_LSEG)
scheduler/universes.py     (imports instrument lists)
```

## Related Documentation

- [INSTRUMENTS.md](INSTRUMENTS.md) - Complete instrument list (200+ RICs)
- [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md) - Database schema details
- [SCHEDULER.md](SCHEDULER.md) - Automated extraction setup
- [LSEG_API_REFERENCE.md](LSEG_API_REFERENCE.md) - LSEG field mappings
