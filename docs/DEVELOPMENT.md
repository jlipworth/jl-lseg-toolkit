# Development Guide

Developer documentation for contributing to and maintaining the LSEG Toolkit.

## Setup

For environment setup and LSEG connection, see **[GETTING_STARTED.md](GETTING_STARTED.md)**.

Quick reference:
```bash
uv sync                      # Install dependencies
uv run lseg-earnings --help  # Verify installation
```

---

## Code Quality

### Testing

```bash
# Run all tests
uv run pytest tests/

# Fast mode (skip coverage)
uv run pytest tests/ --no-cov

# Run specific test file
uv run pytest tests/test_excel.py -v

# Run with coverage report
uv run pytest tests/ --cov=src/lseg_toolkit --cov-report=html
```

### Linting & Formatting

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Type checking
uv run mypy src/

# Format only (ruff)
uv run ruff format src/ tests/

# Lint only (ruff)
uv run ruff check src/ tests/ --fix
```

### Validation Checklist

Run before every commit:
```bash
uv run pytest tests/ --no-cov && \
uv run mypy src/ && \
uv run pre-commit run --all-files
```

---

## Project Structure

```
src/lseg_toolkit/
├── client/                 # LSEG API client (modular)
│   ├── session.py          # Session management
│   ├── constituents.py     # Index constituents
│   ├── company.py          # Company data
│   ├── earnings.py         # Earnings dates/times
│   ├── financial.py        # Financial ratios
│   └── consensus.py        # Analyst estimates
├── earnings/               # Earnings report pipeline
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration dataclass
│   └── pipeline.py         # Processing pipeline
├── equity_screener/        # Equity screener pipeline
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration dataclass
│   └── pipeline.py         # Processing pipeline
├── data.py                 # Data processing utilities
├── excel.py                # Excel export
└── timezone_utils.py       # GMT to local conversion
```

---

## Git Workflow

### Branch Naming
- Features: `feature/short-description`
- Bug fixes: `fix/short-description`
- Refactoring: `refactor/short-description`

### Commit Messages
Use conventional commit format:
```
type: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### Pull Requests
1. Create a focused PR (one feature/fix per PR)
2. Ensure all tests pass
3. Update documentation if needed
4. Reference related issues

---

## Docstring Standard

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int = 10) -> pd.DataFrame:
    """
    One-line summary of what this does.

    Longer description if needed, explaining behavior,
    edge cases, or important notes.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is invalid

    Example:
        >>> result = function_name("test", param2=20)
        >>> print(result.shape)
        (100, 5)
    """
```

---

## Development Scripts

Exploratory scripts go in `dev_scripts/` (gitignored):

```
dev_scripts/
├── active/           # Current investigations
├── archive/          # Completed work (by project)
└── README.md         # Structure documentation
```

**Guidelines:**
- Keep active work in `active/`
- Archive completed investigations to `archive/<project-name>/`
- Use descriptive names: `test_<feature>.py`, `diagnose_<issue>.py`

---

## Architecture Notes

### Data Flow

```
CLI → Config → Pipeline → Client → LSEG API
                  ↓
              DataFrame
                  ↓
              Processing
                  ↓
              Excel Export
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `client/` | LSEG API abstraction, session management |
| `earnings/` | Earnings report generation pipeline |
| `equity_screener/` | Equity screening pipeline |
| `data.py` | DataFrame transformations |
| `excel.py` | Excel export with formatting |
| `timezone_utils.py` | GMT to local timezone conversion |

### Key Design Decisions

1. **Modular client:** Each data type (earnings, financial, consensus) has its own module for easier testing and maintenance.

2. **Pipeline pattern:** CLI tools use a pipeline class that orchestrates data fetching, processing, and export.

3. **Config dataclasses:** All configuration is captured in typed dataclasses for validation and IDE support.

4. **Context manager for sessions:** LsegClient uses `__enter__`/`__exit__` for automatic session cleanup.

---

## Troubleshooting

### Common Issues

**"Failed to open LSEG session"**
1. Ensure LSEG Workspace Desktop is running
2. Check you're logged in to LSEG
3. Run `uv run lseg-setup` to configure app key

**"No constituents found"**
- Verify the index code is valid (`--list-indices`)
- Check market cap filters aren't too restrictive

**Tests failing with connection errors**
- LSEG Workspace must be running for integration tests
- Run unit tests only: `uv run pytest tests/ -m "not integration"`

### Getting Help

- Check [LSEG_API_REFERENCE.md](LSEG_API_REFERENCE.md) for API patterns
- Review [CHANGELOG.md](CHANGELOG.md) for recent changes
- Open an issue on GitHub for bugs

---

## Release Checklist

Before releasing a new version:

- [ ] All tests pass: `uv run pytest tests/`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Linting passes: `uv run pre-commit run --all-files`
- [ ] CLI help is accurate: `uv run lseg-earnings --help`
- [ ] Update version in `pyproject.toml`
- [ ] Update `docs/CHANGELOG.md`
- [ ] Create git tag: `git tag v0.x.x`
