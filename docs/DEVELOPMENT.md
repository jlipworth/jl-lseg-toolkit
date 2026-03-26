# Development Guide

Use this document **after your local environment already works**.

- For first-time setup, LSEG connectivity, and WSL details, use
  [GETTING_STARTED.md](GETTING_STARTED.md).
- Use this guide for the **developer workflow**: repo structure, validation,
  documentation expectations, and release hygiene.

## What `DEVELOPMENT.md` is for

`DEVELOPMENT.md` is the maintainer/contributor playbook for working on the repo
once you can already run it locally.

It should answer questions like:
- how do I validate changes before pushing?
- what does `make ci-local` mirror?
- where should new code live?
- when should I update docs/tests/changelog?

It is **not** the end-user onboarding doc; that is `GETTING_STARTED.md`.

## Daily workflow

```bash
uv sync                      # Install dependencies
uv sync --group bloomberg    # Optional: install supported Bloomberg runtime deps
make install-hooks           # Install git pre-commit hooks
make ci-local                # Full local CI mirror
```

Useful commands:

```bash
# Fast unit-only test loop
uv run pytest tests/ -m "not integration" --no-cov -q

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Full local mirror of Woodpecker CI
make ci-local
```

## Validation policy

`make ci-local` is the repo's ground-truth local validation command.

It mirrors the Woodpecker pipeline by running:
1. frozen test-only dependency sync
2. `ruff check`
3. `ruff format --check`
4. `mypy`
5. unit-test CI slice (`pytest -m "not integration"`)

Use raw `uv run mypy src/` only for quick iteration; CI correctness is defined
by `make ci-local`.

## Project structure

```text
src/lseg_toolkit/
├── client/                 # Core LSEG client modules
├── earnings/               # Earnings-report CLI + pipeline
├── equity_screener/        # Screener CLI + pipeline
├── timeseries/             # Extraction, storage, scheduler, FOMC, prediction markets
│   ├── storage/            # PostgreSQL / TimescaleDB persistence
│   ├── scheduler/          # APScheduler-backed job orchestration
│   ├── fed_funds/          # Fed Funds extraction and roll logic
│   ├── fomc/               # FOMC meeting and decision sync
│   ├── prediction_markets/ # Kalshi / Polymarket / FedWatch workflows
│   ├── bond_basis/         # Treasury conversion-factor / basis helpers
│   └── stir_futures/       # STIR contract helpers
├── bloomberg/              # Supported Bloomberg extraction/normalization CLI surface
├── bonds/                  # Treasury API integrations
├── shared/                 # Shared utilities
└── exceptions.py           # Shared exception hierarchy
```

### Bloomberg code placement

- Supported Bloomberg code belongs under `src/lseg_toolkit/bloomberg/`
- Supported Bloomberg tests belong under `tests/bloomberg/`
- Exploratory or ticker-discovery scripts can remain under `bloomberg_scripts/`
- Files in `bloomberg_scripts/` should not be treated as automatic product-support claims

## Documentation expectations

Update docs when you change:
- CLI behavior or examples
- schema or storage behavior
- instrument mappings or support claims
- scheduler groups/commands
- prediction-market workflows

In practice, the most commonly touched docs are:
- `README.md`
- `docs/TIMESERIES.md`
- `docs/SCHEDULER.md`
- `docs/STORAGE_SCHEMA.md`
- `docs/PREDICTION_MARKETS.md`
- `docs/LSEG_API_REFERENCE.md`
- `docs/CHANGELOG.md`

## Code style

- Ruff for linting and formatting
- mypy for type checking
- pre-commit for local hooks
- Google-style docstrings for public functions
- Prefer small focused PRs

## Git / PR guidance

- Branch naming: `feature/...`, `fix/...`, `docs/...`, `refactor/...`
- Keep PRs focused and reviewable
- Update docs/changelog in the same PR when behavior changes
- Re-run `make ci-local` before pushing rebases or force-pushes

## Release / merge checklist

- [ ] `make ci-local` passes
- [ ] affected docs updated
- [ ] changelog updated if behavior materially changed
- [ ] examples/CLI help still reflect reality
- [ ] no maintainer-specific paths, secrets, or private infra details in docs
