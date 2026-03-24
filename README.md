# jl-lseg-toolkit

A Python toolkit for working with LSEG Workspace data, with first-class support for
**timeseries extraction/storage**, **scheduler-driven collection**, **Fed Funds/FOMC**
workflows, **prediction markets**, plus the original **earnings** and **equity
screening** tools.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/jl-lseg-toolkit.svg)](https://pypi.org/project/jl-lseg-toolkit/)
[![CI](https://woodpecker01.crapmaster.org/api/badges/jlipworth/jl-lseg-toolkit/status.svg)](https://woodpecker01.crapmaster.org/jlipworth/jl-lseg-toolkit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> **Requires:** LSEG Workspace Desktop running locally with an active subscription.

## What this repo does

- **Timeseries extraction** for futures, FX, OIS, FRAs, sovereign yields, and STIR products
- **TimescaleDB/PostgreSQL storage** with typed instrument metadata and unified `timeseries_*` tables
- **Scheduler support** for recurring extraction jobs and gap-filling workflows
- **Fed Funds / FOMC tooling** for continuous contracts, meeting history, and rate-decision data
- **Prediction markets** for Kalshi, Polymarket, and FedWatch comparison workflows
- **Equity tools** for earnings reports, screening, financial ratios, consensus, and historical snapshots

## Installation

### From source

```bash
git clone git@github.com:jlipworth/jl-lseg-toolkit.git
cd jl-lseg-toolkit
uv sync
```

### Configure your LSEG app key

```bash
uv run lseg-setup
```

For platform-specific setup details, including WSL2 mirrored networking, see
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Quick start

### Verify connectivity

```bash
# LSEG Workspace should respond on localhost:9000
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000
# Expected: 404 or 403, not "Connection refused"

# Test Python session from the project environment
uv run python -c "import lseg.data as rd; rd.open_session(); print('Session opened'); rd.close_session()"
```

### Try the CLI tools

```bash
# Earnings report for this week's S&P 500 earnings
uv run lseg-earnings

# Equity screener for Nasdaq 100
uv run lseg-screener --index NDX

# Bond futures extraction
uv run lseg-extract ZN ZB

# Scheduler command set
uv run lseg-scheduler groups
```

## CLI tools

| Command | Purpose |
|---------|---------|
| `lseg-earnings` | Earnings report generation with Excel export |
| `lseg-screener` | Equity screening and valuation snapshot export |
| `lseg-setup` | Interactive LSEG app-key configuration |
| `lseg-extract` | Timeseries extraction and optional continuous-contract building |
| `lseg-scheduler` | Scheduler job management and daemon control |

### `lseg-extract` highlights

```bash
# Extract Treasury futures
uv run lseg-extract ZN ZB

# Continuous contract with ratio adjustment
uv run lseg-extract ZN --continuous --adjust ratio

# FX intraday data
uv run lseg-extract EURUSD USDJPY --asset-class fx --start 2026-03-01 --interval 5min

# Fed Funds continuous hourly
uv run lseg-extract FF_CONTINUOUS --asset-class stir --interval hourly --start 2026-03-01 --end 2026-03-03

# Full USD OIS curve
uv run lseg-extract 1M 3M 6M 1Y 2Y 5Y 10Y 30Y --asset-class ois
```

### `lseg-scheduler` highlights

```bash
# List available instrument groups
uv run lseg-scheduler groups

# Seed default Fed Funds strip jobs
uv run lseg-scheduler seed-ff-strip

# Add a recurring job
uv run lseg-scheduler add-job \
  --name benchmark_daily \
  --group benchmark_fixings \
  --granularity daily \
  --cron "0 18 * * 1-5"
```

## Python API

### Core LSEG client

```python
from lseg_toolkit import LsegClient

with LsegClient() as client:
    tickers = client.get_index_constituents("SPX", min_market_cap=50_000)
    earnings = client.get_earnings_data(tickers, start_date="2025-01-01", end_date="2025-01-31")
    ratios = client.get_financial_ratios(tickers, as_of_date="2024-06-30")
```

### Timeseries API

```python
from lseg_toolkit.timeseries import DataCache, get_client

cache = DataCache()
df = cache.get_or_fetch("TYc1", start="2024-01-01", end="2024-12-31")

client = get_client()
df = client.fetch_timeseries("EUR=", start="2026-03-01", end="2026-03-03", interval="hourly")
```

### Prediction-market helpers

```python
from lseg_toolkit.timeseries.prediction_markets import (
    compare_markets_to_fedwatch,
    init_pm_schema,
    load_fedwatch_probabilities,
)
```

## Repo layout

```text
src/lseg_toolkit/
├── client/                 # Core LSEG client modules
├── earnings/               # Earnings-report pipeline + CLI
├── equity_screener/        # Screener pipeline + CLI
├── timeseries/             # Extraction, storage, scheduler, FOMC, prediction markets
│   ├── storage/
│   ├── scheduler/
│   ├── fed_funds/
│   ├── fomc/
│   ├── prediction_markets/
│   ├── bond_basis/
│   └── stir_futures/
├── bonds/                  # Treasury helper integrations
└── shared/                 # Shared utilities
```

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/GETTING_STARTED.md) | Environment setup and connectivity checks |
| [Timeseries Guide](docs/TIMESERIES.md) | Extraction workflow, asset classes, storage, rolling |
| [Scheduler Guide](docs/SCHEDULER.md) | Scheduler commands, groups, schema, operating model |
| [Prediction Markets](docs/PREDICTION_MARKETS.md) | Kalshi, Polymarket, FOMC, and FedWatch workflow |
| [Polymarket Resolution](docs/POLYMARKET_RESOLUTION.md) | Canonical normalization and resolution rules |
| [Storage Schema](docs/STORAGE_SCHEMA.md) | Current database model summary and source-of-truth pointers |
| [Instruments](docs/INSTRUMENTS.md) | LSEG instrument reference by asset class |
| [API Reference](docs/LSEG_API_REFERENCE.md) | LSEG patterns, field quirks, and mapping notes |
| [Architecture](docs/ARCHITECTURE.md) | Repo subsystem map and data flow |
| [Development](docs/DEVELOPMENT.md) | Contributor workflow after initial setup |
| [Testing](docs/TESTING.md) | Local test strategy and CI mirror |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common LSEG, database, scheduler, and ingestion issues |
| [Changelog](docs/CHANGELOG.md) | Version history and current unreleased work |

## Development quickstart

```bash
# install hooks for this clone
make install-hooks

# run the same checks CI runs
make ci-local
```

## Requirements

- Python 3.12+
- LSEG Workspace Desktop with active subscription
- For storage workflows: your own TimescaleDB/PostgreSQL instance configured via `TSDB_*` or `POSTGRES_*`

## License

MIT License. See [LICENSE](LICENSE) for details.
