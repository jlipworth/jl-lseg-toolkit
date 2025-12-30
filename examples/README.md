# Examples

Runnable examples demonstrating LSEG Toolkit usage.

## Prerequisites

1. LSEG Workspace Desktop running and logged in
2. Python environment with package installed:
   ```bash
   uv sync
   ```

## Available Examples

| Script | Description |
|--------|-------------|
| `earnings_report.py` | Generate earnings report for an index |
| `equity_screener.py` | Screen stocks by valuation metrics |
| `custom_queries.py` | Direct client usage for custom analysis |

## Running Examples

```bash
# From project root
uv run python examples/earnings_report.py
uv run python examples/equity_screener.py
uv run python examples/custom_queries.py
```

## Output

Examples write output to the `exports/` directory (gitignored).
