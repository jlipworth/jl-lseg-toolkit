# jl-lseg-toolkit

A Python toolkit for extracting and analyzing financial data from the LSEG (London Stock Exchange Group) API. Provides CLI tools and a Python API for equity screening, earnings analysis, and financial data retrieval.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/jl-lseg-toolkit.svg)](https://pypi.org/project/jl-lseg-toolkit/)
[![CI](https://woodpecker01.crapmaster.org/api/badges/jlipworth/jl-lseg-toolkit/status.svg)](https://woodpecker01.crapmaster.org/jlipworth/jl-lseg-toolkit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> **Requires:** LSEG Workspace Desktop running with an active subscription.

## Features

- **Earnings Reports**: Screen 13 global indices by upcoming earnings dates with timezone conversion
- **Equity Screener**: Filter stocks by market cap, valuation metrics, and financial criteria
- **Time Series Extraction**: Bond futures, FX, OIS, Treasury yields with DuckDB storage and Parquet export
- **Continuous Contracts**: Build ratio/difference-adjusted continuous futures with configurable roll methods
- **Financial Ratios**: 20+ valuation, debt, and performance metrics
- **Consensus Estimates**: Analyst EPS/revenue estimates (NTM, FY1, FY2, FQ1, FQ2)
- **Historical Snapshots**: Point-in-time data for backtesting
- **Excel Export**: Formatted workbooks with sector breakdown and collapsible rows
- **Activism Tracking**: Campaign announcement dates

## Installation

### From PyPI

```bash
pip install jl-lseg-toolkit
```

### From Source

```bash
git clone https://github.com/jlipworth/jl-lseg-toolkit.git
cd jl-lseg-toolkit
uv sync
```

### Configure App Key (Optional)

```bash
lseg-setup  # Interactive setup
```

**WSL2 users:** See [WSL Setup Guide](docs/WSL_SETUP.md).

## Quick Start

### Prerequisites Checklist

Before running, verify your setup:

```bash
# 1. Is LSEG Workspace running? (should return HTTP 404, not "Connection refused")
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000
# Expected: 404

# 2. Can Python connect? (should print "Session opened")
python -c "import lseg.data as rd; rd.open_session(); print('Session opened'); rd.close_session()"
```

If Step 1 fails: Start LSEG Workspace Desktop and log in.
If Step 2 fails: Run `lseg-setup` to configure your app key.

### Run Your First Report

```bash
# Earnings report for S&P 500, current week
lseg-earnings

# Equity screener for Nasdaq 100
lseg-screener --index NDX

# Extract bond futures time series (last year, daily)
lseg-extract ZN ZB

# See all options
lseg-earnings --help
lseg-screener --help
lseg-extract --help
```

**Having connection issues?** See [Troubleshooting](docs/TROUBLESHOOTING.md).

## Available Indices

| Code | Name | Region | Companies |
|------|------|--------|-----------|
| SPX | S&P 500 | US | 500 |
| SPCY | S&P SmallCap 600 | US | 600 |
| NDX | Nasdaq 100 | US | 100 |
| DJI | Dow Jones | US | 30 |
| STOXX | STOXX Europe 600 | Europe | 600 |
| STOXX50E | EURO STOXX 50 | Europe | 50 |
| FTSE | FTSE 100 | UK | 100 |
| GDAXI | DAX | Germany | 40 |
| FCHI | CAC 40 | France | 40 |
| AEX | AEX | Netherlands | 25 |
| N225 | Nikkei 225 | Japan | 225 |
| HSI | Hang Seng | Hong Kong | ~88 |
| GSPTSE | S&P/TSX Composite | Canada | ~214 |

## CLI Reference

### lseg-earnings

Screen index constituents by upcoming earnings dates with Excel export.

```bash
lseg-earnings [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--index CODE` | Index to screen (default: SPX). Use `--list-indices` to see all. |
| `--timeframe` | today, tomorrow, week, next-week, month |
| `--start-date` | Start date (YYYY-MM-DD) |
| `--end-date` | End date (YYYY-MM-DD) |
| `--min-cap` | Minimum market cap in millions (e.g., 10000 = $10B) |
| `--max-cap` | Maximum market cap in millions |
| `--timezone` | Convert times to timezone (default: US/Eastern) |
| `--output-dir` | Output directory (default: exports/) |
| `--list-indices` | Show available indices |

### lseg-screener

Screen equities by valuation metrics with Excel export.

```bash
lseg-screener [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--index CODE` | Index to screen (default: SPX) |
| `--country CODE` | Filter by country (default: US) |
| `--no-index` | Screen all stocks (no index filter) |
| `--no-country` | Screen globally (no country filter) |
| `--min-cap` | Minimum market cap in millions |
| `--max-cap` | Maximum market cap in millions |
| `--date` | Screen date for historical snapshot (YYYY-MM-DD) |
| `--output-dir` | Output directory (default: exports/) |
| `--list-indices` | Show available indices |

### lseg-extract

Extract time series data for bond futures, FX, OIS, Treasury yields, and FRAs with DuckDB storage and Parquet export.

```bash
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

**Examples:**

```bash
# Extract 10Y and 30Y Treasury futures (last year, daily)
lseg-extract ZN ZB

# Build continuous contract with ratio adjustment
lseg-extract ZN --continuous --adjust ratio

# Extract FX spot data (5-minute bars, recent 30 days)
lseg-extract EURUSD USDJPY --asset-class fx --start 2025-12-01 --interval 5min

# Extract full USD OIS curve
lseg-extract 1M 3M 6M 1Y 2Y 5Y 10Y 30Y --asset-class ois

# Extract Treasury yield curve
lseg-extract 2Y 5Y 10Y 30Y --asset-class govt-yield

# List all 200+ supported instruments
lseg-extract --list
```

**Output:**
- **DuckDB database** (`data/timeseries.duckdb`): Analytics-optimized storage with shape-specific tables
- **Parquet files** (`data/parquet/`): Columnar format for C++/Rust consumption via Arrow
- **metadata.json**: Instrument registry, date ranges, roll history

For complete documentation, see [Time Series Guide](docs/TIMESERIES.md).

## Python API

```python
from lseg_toolkit import LsegClient

with LsegClient() as client:
    # Get S&P 500 large caps ($50B+)
    tickers = client.get_index_constituents('SPX', min_market_cap=50_000)

    # Get earnings dates for next month
    earnings = client.get_earnings_data(
        tickers,
        start_date='2025-01-01',
        end_date='2025-01-31'
    )

    # Get comprehensive financial ratios
    ratios = client.get_financial_ratios(tickers)

    # Get consensus estimates (NTM, FY1, FY2, FQ1, FQ2)
    estimates = client.get_consensus_estimates(tickers, periods=['NTM', 'FY1'])

    # Historical snapshot for backtesting
    historical = client.get_financial_ratios(
        tickers,
        as_of_date='2024-06-30'
    )
```

### Financial Ratios Available

**Valuation**: P/E LTM, P/E NTM, EV/EBITDA LTM & NTM, P/B, P/FCF

**Debt Metrics**: Net Debt, Net Debt/EBITDA, Net Debt % of EV

**Returns**: 1Mo, 3Mo, 6Mo, YTD, 1Y, 2Y, 3Y, 5Y, Since Last Earnings

**Analyst**: Price Targets (Mean/Median/High/Low), StarMine P/IV

### Historical Snapshots (`as_of_date`)

These methods support point-in-time historical data:

| Method | `as_of_date` Support | Notes |
|--------|---------------------|-------|
| `get_financial_ratios()` | Yes | Full valuation snapshot |
| `get_consensus_estimates()` | Yes | Historical analyst estimates |
| `get_since_last_earnings_return()` | Yes | Returns as of specific date |
| `get_index_constituents()` | No | Always returns current members |
| `get_earnings_data()` | No | Use `start_date`/`end_date` instead |

```python
# Get valuations as they were on June 30, 2024
historical = client.get_financial_ratios(tickers, as_of_date='2024-06-30')
```

### Performance Expectations

Typical execution times (depends on network and LSEG server load):

| Operation | Tickers | Time |
|-----------|---------|------|
| Index constituents | - | 2-5 sec |
| Earnings data | 500 | 5-10 sec |
| Financial ratios | 500 | 10-15 sec |
| Full earnings report | 500 | 30-45 sec |
| Full equity screener | 500 | 45-60 sec |

**Tip:** Use `--min-cap` to reduce universe size for faster results.

### Glossary

| Term | Meaning |
|------|---------|
| **RIC** | Reuters Instrument Code (e.g., `AAPL.O` for Apple on NASDAQ) |
| **LTM** | Last Twelve Months (trailing) |
| **NTM** | Next Twelve Months (forward consensus) |
| **FY1/FY2** | Fiscal Year 1/2 (current/next fiscal year estimates) |
| **FQ1/FQ2** | Fiscal Quarter 1/2 (current/next quarter estimates) |
| **EV** | Enterprise Value (Market Cap + Net Debt) |
| **EBITDA** | Earnings Before Interest, Taxes, Depreciation, Amortization |
| **P/E** | Price-to-Earnings ratio |
| **P/B** | Price-to-Book ratio |
| **P/FCF** | Price-to-Free-Cash-Flow ratio |

## Architecture

```
lseg_toolkit/
├── client/                 # LSEG API Client (modular)
│   ├── session.py          # Session lifecycle management
│   ├── constituents.py     # Index constituent retrieval
│   ├── earnings.py         # Earnings dates and returns
│   ├── financial.py        # Valuation ratios and metrics
│   ├── consensus.py        # Analyst estimates
│   └── company.py          # Company info and activism
│
├── earnings/               # Earnings Report Pipeline
│   ├── pipeline.py         # Data collection orchestration
│   ├── config.py           # Report configuration
│   └── cli.py              # Command-line interface
│
├── equity_screener/        # Screener Pipeline
│   ├── pipeline.py         # Screening and metrics calc
│   ├── config.py           # Screener configuration
│   └── cli.py              # Command-line interface
│
├── timeseries/             # Time Series Extraction Pipeline
│   ├── cache.py            # Async cache layer with gap detection
│   ├── client.py           # LSEG data client
│   ├── duckdb_storage.py   # DuckDB persistence (shape-specific tables)
│   ├── rolling.py          # Continuous contract construction
│   ├── constants.py        # Symbol mappings (CME↔LSEG, 200+ RICs)
│   ├── enums.py            # Asset classes, granularities, data shapes
│   ├── models/             # Instrument and timeseries dataclasses
│   └── cli.py              # lseg-extract CLI
│
├── excel.py                # Formatted Excel workbook export
├── data.py                 # DataFrame processing utilities
├── timezone_utils.py       # GMT to local time conversion
├── constants.py            # Centralized configuration
└── exceptions.py           # Custom exception hierarchy
```

### Exception Hierarchy

```
LsegError (base)
├── SessionError        # Connection/auth failures
├── DataRetrievalError  # API call failures
├── DataValidationError # Invalid data format
└── ConfigurationError  # Invalid configuration
```

## Documentation

| Document | Description |
|----------|-------------|
| [Time Series Guide](docs/TIMESERIES.md) | Extraction, storage, and Python API |
| [Instruments](docs/INSTRUMENTS.md) | 200+ validated RICs by asset class |
| [Storage Schema](docs/STORAGE_SCHEMA.md) | DuckDB tables and data shapes |
| [API Reference](docs/LSEG_API_REFERENCE.md) | LSEG fields and API patterns |
| [Architecture](docs/ARCHITECTURE.md) | System design and data flow |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Development](docs/DEVELOPMENT.md) | Testing, code quality, setup |
| [Contributing](docs/CONTRIBUTING.md) | How to contribute |
| [WSL Setup](docs/WSL_SETUP.md) | WSL2 networking configuration |
| [Changelog](docs/CHANGELOG.md) | Version history |

## Requirements

- Python 3.12+
- LSEG Workspace Desktop with active subscription
- `lseg-data` Python package (LSEG Data Library)

## License

<a href="https://opensource.org/licenses/MIT">
  <img src="https://opensource.org/wp-content/themes/flavor/library/images/logo-mark.png" alt="OSI Approved" width="100">
</a>

MIT License - Copyright (c) 2025 Jonathan Lipworth. See [LICENSE](LICENSE) for details.
