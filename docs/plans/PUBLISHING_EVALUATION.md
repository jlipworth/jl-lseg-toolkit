# Publishing Evaluation

**Date:** 2026-03-24
**Branch:** `feat/python-publishing`
**Current version:** 0.1.0 (never published to PyPI)

---

## Purpose

Evaluate `jl-lseg-toolkit` for publishing to PyPI. The package has grown beyond LSEG into a broader financial data toolkit. This document captures findings and outlines the work needed to freeze the interface and publish.

---

## 1. Naming

### Problem

The package is named `jl-lseg-toolkit` (import: `lseg_toolkit`) but now includes significant non-LSEG functionality:
- Prediction markets (Kalshi, Polymarket)
- FOMC calendar/rate data (Federal Reserve)
- FedWatch probabilities (CME)
- Treasury bonds (Treasury Fiscal Data API)
- Bloomberg data (feature branch)

The `jl-` prefix is personal branding; `lseg` understates the scope.

### Candidate Names (all confirmed available on PyPI)

| Rank | PyPI Name | Import Name | Notes |
|------|-----------|-------------|-------|
| 1 | `findata-toolkit` | `findata_toolkit` | Descriptive, professional, broad scope |
| 2 | `finextract` | `finextract` | Short, action-oriented |
| 3 | `marketkit` | `marketkit` | Concise, modern |
| 4 | `jl-findata` | `jl_findata` | Keeps personal branding |
| 5 | `findata-kit` | `findata_kit` | Variant of #1 |

**Taken names:** `fintoolkit`, `finkit`, `mktdata`, `findata`

### Rename Blast Radius

| Category | Files | Occurrences |
|----------|-------|-------------|
| Python imports (`lseg_toolkit`) | ~101 | ~322 |
| All references to `lseg_toolkit` | ~117 | ~438 |
| Hyphenated refs (`lseg-toolkit`, `jl-lseg-toolkit`) | ~16 | |
| CLI names (`lseg-*`) | ~17 | |
| Markdown docs | ~13 | |

The rename is 100% mechanical (no dynamic imports, no plugin registries). Estimated effort: 1-2 hours with `sd`/find-and-replace.

### Recommendation

- **Rename before publishing.** No external consumers exist. Once published, renaming requires a deprecation migration.
- **Drop `jl-` prefix** for PyPI name.
- **Keep LSEG-branded class names** (`LsegEquityClient`, `LsegError`) since they accurately describe the LSEG wrapper module. The package name is the broader umbrella.
- **CLI tools** should get a matching prefix (e.g., `fin-earnings` instead of `lseg-earnings`).

### Decision

**TODO:** Pick a name.

---

## 2. Project Evolution Summary

The project is 3 months old (134 commits, single contributor) with rapid, deep development:

| Phase | Period | What Happened |
|-------|--------|---------------|
| Foundation | Dec 29, 2025 - Jan 6, 2026 | Initial LSEG client, earnings, screener, timeseries extraction |
| Storage & Instruments | Jan 6-14 | DuckDB -> PostgreSQL/TimescaleDB migration, scheduler daemon |
| Fixed Income | Jan 14 - Mar 2026 | Bond basis, STIR futures, Fed Funds continuous contracts |
| Prediction Markets | Mar 15-24 | Kalshi, Polymarket, FedWatch, FOMC calendar (~15 commits) |
| Bloomberg | Mar 12-24 | Feature branch (`feature/bloomberg`), not yet merged |

### Module Status

| Status | Modules |
|--------|---------|
| **Active** (recent commits) | prediction_markets, fomc, bloomberg (feature branch) |
| **Stable** (working, occasional maintenance) | storage, fed_funds, stir_futures, scheduler |
| **Stale** (untouched since initial release) | earnings, equity_screener, client |

---

## 3. API Audit Findings

### Breaking Issues (must fix before freezing)

1. **`LsegClient` deprecated alias** - exists but emits no deprecation warning. Either remove or add `warnings.warn()`.

2. **Storage module over-exports** - ~50 items in `__all__`. Should be ~10 core items (`save_instrument`, `save_timeseries`, `load_timeseries`, `get_connection`, etc.). The rest are implementation details.

3. **Polymarket exports asymmetry** - exports 25 functions vs Kalshi's 3. Many are implementation details (`parse_trade`, `aggregate_daily_candles`, `normalize_status`). Should tier into public vs internal.

4. **FedWatch functions misplaced** - `build_distribution()`, `load_fedwatch_probabilities()`, `normalize_fedwatch_frame()` exported from prediction_markets but belong in fomc module.

### Cleanup Issues

5. **CLI argument naming inconsistent** - `--start-date` vs `--start` vs `--date` across different CLIs. Need to standardize.

6. **Client class capitalization** - `LSEGDataClient` vs `LsegEquityClient`. Pick one convention.

7. **Private method leaking** - `_calculate_fiscal_period_label_simple` in client `__all__`.

8. **Config classes missing `.from_env()`** - `DatabaseConfig` and `SchedulerConfig` have it, others don't.

9. **Naming inconsistency** - `save_*()` vs `upsert_*()` used without clear distinction.

10. **`prepare_for_storage()`** - vague name, should be `prepare_fed_funds_for_storage()`.

### Missing

11. **No version tuple** - only `__version__` string, no `__version_info__`.

12. **Storage/roll exceptions not exported** from timeseries module.

---

## 4. Dependency Restructuring

### Unused Dependencies (remove)

- `xlrd>=2.0.2` - not imported anywhere
- `pytreasurydirect>=0.1.1` - not imported anywhere

### Recommended Optional Groups

```toml
[project.optional-dependencies]
timeseries = [
    "httpx>=0.26.0",
    "exchange-calendars>=4.13.2",
    "pydantic>=2.0",
]
storage = [
    "psycopg[binary,pool]>=3.2.0",
]
scheduler = [
    "apscheduler>=3.10,<4.0",
    "psycopg[binary,pool]>=3.2.0",
]
prediction-markets = [
    "httpx>=0.26.0",
    "pydantic>=2.0",
    "psycopg[binary,pool]>=3.2.0",
]
fomc = [
    "httpx>=0.26.0",
    "pydantic>=2.0",
    "psycopg[binary,pool]>=3.2.0",
    "fedtools>=0.0.7",
]
export = [
    "pyarrow>=14.0.0",
]
all = [
    # everything above combined
]
```

### Core Dependencies (always installed)

```
lseg-data, pandas>=2.0.0, numpy>=1.24.0, openpyxl>=3.1.0,
xlsxwriter>=3.1.0, python-dateutil>=2.8.0, pytz>=2024.1
```

This reduces default install footprint by ~60%.

### Version Constraints to Review

- `httpx<0.27` - very tight, investigate if 0.27+ actually breaks anything
- `lseg-data` - no version constraint at all, should add minimum
- `apscheduler>=3.10` - should add `<4.0` ceiling

---

## 5. Corrected Assumptions

Initial analysis flagged two "blockers" that turned out to be non-issues:

- **`.env` credentials** - .env was never committed to git history. It's in .gitignore and clean.
- **`lseg-data` proprietary** - `lseg-data` IS on public PyPI (versions 2.0.0-2.1.1). Fully installable.

---

## 6. Codebase Stats

- **94 Python files**, 86 classes, 323 functions
- **~23.5k lines** of source code
- **31 test modules**, ~9.9k lines of test code
- **5 CLI entry points**: lseg-earnings, lseg-screener, lseg-extract, lseg-scheduler, lseg-setup
- Modern tooling: hatchling build, ruff, mypy, pre-commit, Woodpecker CI

---

## 7. Work Plan

### Phase 1: Name Decision & Rename
- [ ] Pick package name
- [ ] Mechanical rename (src dir, imports, pyproject.toml, CLI entry points, docs)
- [ ] Verify tests pass

### Phase 2: Dependency Cleanup
- [ ] Remove unused deps (xlrd, pytreasurydirect)
- [ ] Create optional dependency groups
- [ ] Add lazy imports where needed
- [ ] Review version constraints

### Phase 3: API Cleanup
- [ ] Tier storage exports (core vs internal)
- [ ] Tier polymarket exports
- [ ] Move FedWatch functions to fomc module
- [ ] Remove or deprecate `LsegClient` alias
- [ ] Standardize CLI argument naming
- [ ] Fix private method leaks
- [ ] Standardize client class capitalization

### Phase 4: Freeze & Publish
- [ ] Define `__all__` as the frozen public API for each module
- [ ] Add version tags and version management
- [ ] Set up PyPI publish workflow
- [ ] Test install from test PyPI
- [ ] Publish v0.1.0 (or v1.0.0)
