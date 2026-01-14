# Contributing

Thank you for your interest in contributing to the LSEG Toolkit!

## Getting Started

For complete setup instructions, see **[GETTING_STARTED.md](GETTING_STARTED.md)**.

```bash
# Clone and install
git clone <repository-url>
cd jl-lseg-toolkit
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Verify setup
uv run pytest tests/ --no-cov
```

## Making Changes

### 1. Create a Branch

```bash
# For features
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b fix/issue-description

# For documentation
git checkout -b docs/what-youre-documenting
```

### 2. Make Your Changes

- Write clear, focused commits
- Add tests for new functionality
- Update documentation as needed
- Follow existing code style

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src/lseg_toolkit --cov-report=term-missing

# Type checking
uv run mypy src/

# Linting and formatting
uv run pre-commit run --all-files
```

### 4. Submit a Pull Request

1. Push your branch to GitHub
2. Open a Pull Request against `master` (the default branch)
3. Describe your changes clearly
4. Reference any related issues
5. Wait for CI checks and code review

## Code Style

### Python

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions (Google style)
- Maximum line length: 88 characters (Black default)

### Formatting

The project uses:
- **Ruff** for linting and formatting
- **mypy** for type checking
- **pre-commit** to run checks automatically

These run automatically on commit via pre-commit hooks.

### Example Function

```python
def get_earnings_data(
    tickers: list[str],
    start_date: str,
    end_date: str,
    convert_timezone: str | None = None,
) -> pd.DataFrame:
    """
    Retrieve earnings data for the specified tickers.

    Args:
        tickers: List of stock tickers (e.g., ["AAPL", "MSFT"])
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        convert_timezone: Target timezone (e.g., "US/Eastern")

    Returns:
        DataFrame with earnings dates, times, and confirmation status

    Raises:
        ValueError: If date format is invalid
    """
```

## Testing Guidelines

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_<module>.py     # Module-level tests
├── earnings/            # Pipeline-specific tests
└── equity_screener/     # Pipeline-specific tests
```

### Writing Tests

```python
def test_function_does_expected_thing():
    """Test that function produces expected output."""
    # Arrange
    input_data = create_test_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result.shape == (10, 5)
    assert "expected_column" in result.columns
```

### Test Markers

```python
@pytest.mark.integration  # Requires LSEG connection
def test_live_api_call():
    ...

@pytest.mark.slow  # Takes > 10 seconds
def test_large_dataset():
    ...
```

Run specific markers:
```bash
# Skip integration tests
uv run pytest tests/ -m "not integration"

# Run only unit tests
uv run pytest tests/ -m "unit"
```

## Documentation

### When to Update Docs

- Adding new features: Update README.md and relevant docs
- Changing APIs: Update LSEG_API_REFERENCE.md
- Changing configuration: Update DEVELOPMENT.md
- Fixing bugs: Update CHANGELOG.md

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Quick start, installation, examples |
| `docs/GETTING_STARTED.md` | Setup for all platforms |
| `docs/ARCHITECTURE.md` | System design, data flow |
| `docs/DEVELOPMENT.md` | Developer guide, testing |
| `docs/LSEG_API_REFERENCE.md` | API patterns, field reference |
| `docs/CHANGELOG.md` | Version history |

## Commit Messages

Use conventional commit format:

```
type: short description

Longer explanation if needed.

Fixes #123
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or fixes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

### Examples

```
feat: add support for FTSE 250 index

fix: correct timezone conversion for Asian markets

docs: update installation instructions for Windows

test: add coverage for earnings date edge cases
```

## Reporting Issues

### Bug Reports

Please include:
1. Python version and OS
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Error messages (if any)

### Feature Requests

Please include:
1. Use case description
2. Proposed solution
3. Alternatives considered

## Questions?

- Check [DEVELOPMENT.md](DEVELOPMENT.md) for development guidance
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Open an issue for questions or discussion
