# Time Series Extraction

Extract historical market data from LSEG for bond futures, FX, OIS curves, government yields, and more.

## Quick Start

```bash
# Extract Treasury futures (last year, daily)
lseg-extract ZN ZB

# FX spot rates
lseg-extract EURUSD USDJPY --asset-class fx

# Treasury yield curve
lseg-extract 2Y 5Y 10Y 30Y --asset-class govt-yield

# OIS curve
lseg-extract 1M 3M 1Y 5Y 10Y --asset-class ois

# List all supported instruments
lseg-extract --list
```

## Supported Asset Classes

| Asset Class | Examples | Description |
|-------------|----------|-------------|
| `futures` | ZN, ZB, FGBL, ES | Bond and index futures |
| `fx` | EURUSD, USDJPY | FX spot rates |
| `ois` | 1M, 1Y, 5Y | OIS swap rates (SOFR) |
| `govt-yield` | 2Y, 10Y, 30Y | US Treasury yields |
| `fra` | 1X4, 3X6 | Forward Rate Agreements |
| `fixing` | SOFR | Daily rate fixings |

For the complete instrument list with 200+ validated RICs, see [INSTRUMENTS.md](INSTRUMENTS.md).

## CLI Reference

```
lseg-extract SYMBOLS... [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--asset-class` | Asset class: futures, fx, ois, govt-yield, fra (auto-detected if omitted) |
| `--start DATE` | Start date (YYYY-MM-DD, default: 1 year ago) |
| `--end DATE` | End date (YYYY-MM-DD, default: today) |
| `--interval` | Granularity: tick, 1min, 5min, 10min, 30min, hourly, daily, weekly, monthly |
| `--continuous` | Build continuous contract (futures only) |
| `--adjust` | Price adjustment: none, ratio, difference (default: ratio) |
| `--roll-method` | Roll detection: volume, first-notice, fixed-days, expiry |
| `--db PATH` | DuckDB database path (default: data/timeseries.duckdb) |
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

# Full USD OIS curve
lseg-extract 1M 2M 3M 6M 9M 1Y 2Y 3Y 5Y 7Y 10Y 15Y 20Y 30Y --asset-class ois

# Custom output location
lseg-extract ZN --db data/custom.duckdb --parquet output/
```

## Python API

### Cache-First Approach (Recommended)

```python
from lseg_toolkit.timeseries import DataCache, CacheConfig

# Create cache with DuckDB backend
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

### DuckDB Storage

```python
from lseg_toolkit.timeseries import duckdb_storage

# Query stored data directly
with duckdb_storage.get_connection() as conn:
    # Load timeseries
    df = duckdb_storage.load_timeseries(conn, "ZN")

    # Get date range
    start, end = duckdb_storage.get_data_range(conn, "ZN")

    # List all instruments
    instruments = duckdb_storage.list_instruments(conn)
```

## Storage Architecture

Data is stored in DuckDB with tables optimized for different data shapes:

| Table | Data Shape | Asset Classes |
|-------|------------|---------------|
| `timeseries_ohlcv` | OHLCV bars | Futures, equities, commodities |
| `timeseries_quote` | Bid/ask quotes | FX, OIS, IRS, FRA |
| `timeseries_bond` | Yield + analytics | Government bonds |
| `timeseries_rate` | Rate quotes | Swaps, repos |
| `timeseries_fixing` | Daily fixings | SOFR, ESTR, SONIA |

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

- **Retention**: ~90 days for most instruments
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
| EURUSD | EUR= | EUR/USD spot |
| USDJPY | JPY= | USD/JPY spot |

For explicit RICs, use the `--ric` flag or pass the RIC directly.

## Output Formats

### DuckDB (Default)

- **Location**: `data/timeseries.duckdb`
- **Query**: Use DuckDB CLI or Python API
- **Advantages**: Fast analytics, SQL support, native Parquet export

### Parquet

- **Location**: `data/parquet/`
- **Format**: Apache Parquet (columnar)
- **Advantages**: Cross-language (C++, Rust, Python), compressed

### Metadata

Each extraction creates:
- `metadata.json`: Instrument registry, date ranges, roll events

## Related Documentation

- [INSTRUMENTS.md](INSTRUMENTS.md) - Complete instrument list (200+ RICs)
- [STORAGE_SCHEMA.md](STORAGE_SCHEMA.md) - DuckDB schema details
- [LSEG_API_REFERENCE.md](LSEG_API_REFERENCE.md) - LSEG field mappings
