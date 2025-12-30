# CLAUDE.md

Project context for Claude Code.

## Project

**Package**: `jl-lseg-toolkit` - Python toolkit for LSEG financial data API.

**CLI Tools**: `lseg-earnings`, `lseg-screener`

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
| Development setup & testing | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| System architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API patterns & fields | [docs/LSEG_API_REFERENCE.md](docs/LSEG_API_REFERENCE.md) |
| WSL2 networking | [docs/WSL_SETUP.md](docs/WSL_SETUP.md) |
| Contributing | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Examples | [examples/](examples/) |

## Rules

- Exploratory scripts → `dev_scripts/` (gitignored)
- LSEG Workspace must be running on `localhost:9000`
