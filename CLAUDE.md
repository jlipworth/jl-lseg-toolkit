# CLAUDE.md

Project context for Claude Code.

## Project

**Package**: `jl-lseg-toolkit` - Python toolkit for LSEG financial data API.

**CLI Tools**: `lseg-earnings`, `lseg-screener`, `lseg-extract`, `lseg-scheduler`

## Quick Commands

```bash
uv sync
uv run pytest tests/ --no-cov
uv run pre-commit run --all-files
```

## Key References

| Topic | File |
|-------|------|
| Quick start & CLI usage | [README.md](README.md) |
| Setup (all platforms) | [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) |
| Timeseries module | [docs/TIMESERIES.md](docs/TIMESERIES.md) |
| System architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API patterns & fields | [docs/LSEG_API_REFERENCE.md](docs/LSEG_API_REFERENCE.md) |
| Development & testing | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Examples | [examples/](examples/) |

## Rules

- Exploratory scripts → `dev_scripts/` (gitignored)
- LSEG Workspace must be running on `localhost:9000`
