# Examples

Runnable examples for the **core LSEG client / earnings / screener** surface.

> These examples do **not** currently cover the newer timeseries, scheduler, or
> prediction-markets subsystems.

## Prerequisites

1. LSEG Workspace Desktop running and logged in
2. Project dependencies installed:
   ```bash
   uv sync
   ```
3. App key configured:
   ```bash
   uv run lseg-setup
   ```

## Available examples

| Script | Description | Output |
|--------|-------------|--------|
| `earnings_report.py` | Generate an earnings report for an index | Excel file in `exports/` |
| `equity_screener.py` | Screen stocks by valuation metrics | Excel file in `exports/` |
| `custom_queries.py` | Direct `LsegClient` usage for ad-hoc analysis | Console output |

## Running examples

```bash
uv run python examples/earnings_report.py
uv run python examples/equity_screener.py
uv run python examples/custom_queries.py
```
