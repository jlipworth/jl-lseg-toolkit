# Bloomberg Data Integration / Implementation Plan

**Status:** Active / in progress
**Created:** 2026-03-24
**Branch:** `feature/bloomberg`

---

## Objective

Turn the current Bloomberg branch from a mixed set of exploratory scripts and partially productized modules into a coherent, documented, testable Bloomberg capability for the repo.

The immediate goal is **not** to force Bloomberg into the full timeseries stack prematurely. The immediate goal is to:

1. stabilize the current Bloomberg code,
2. expose only validated capabilities,
3. adopt the same discipline used by the merged timeseries work,
4. preserve a path to future source-level integration with `lseg_toolkit.timeseries`.

---

## Why this plan exists

The merged timeseries branch established a useful pattern for how substantial data-source work should land in this repo:

- one current user-facing contract (`README.md`, focused docs, CLI help)
- centralized normalization/mapping instead of scattered assumptions
- explicit handling of vendor quirks
- round-trip and integration coverage, not just raw fetch scripts
- docs/tests/CI alignment in the same development stream

The current Bloomberg branch does **not** yet meet that bar.

---

## Current branch assessment

## What is genuinely validated today

### 1. JGB yields
Status: **working**

Validated in `docs/instruments/BLOOMBERG.md` using Bloomberg tickers like:
- `GJGB2 Index`
- `GJGB5 Index`
- `GJGB10 Index`
- `GJGB20 Index`
- `GJGB30 Index`
- `GJGB40 Index`

Current working standalone script:
- `bloomberg_scripts/extract_jgb.py`

### 2. FX ATM implied vol
Status: **working**

Validated pattern:
- `{PAIR}V{TENOR} BGN Curncy`

Examples:
- `EURUSDV1M BGN Curncy`
- `USDJPYV1M BGN Curncy`

Current working standalone script:
- `bloomberg_scripts/extract_fx_vol.py`

### 3. Treasury futures / basis discovery
Status: **working enough for exploration**

The branch contains working exploration for Bloomberg Treasury futures / CTD / basis fields and corresponding test scripts.

Representative scripts:
- `bloomberg_scripts/test_bond_basis.py`
- `bloomberg_scripts/test_bond_futures_basis.py`

---

## What is not validated / not ready

### 1. FX risk reversals / butterflies
Status: **not working**

Current conclusion from the branch docs:
- tested RR/BF patterns either fail or appear to return ATM vol rather than true RR/BF values

### 2. Swaptions
Status: **API access not confirmed**

Current conclusion from the branch docs:
- visible on terminal screens
- Desktop API ticker path not confirmed
- may require different tickers, different permissions, or B-PIPE

### 3. Caps / floors
Status: **ticker format unknown**

Current conclusion from the branch docs:
- tested candidate patterns failed
- terminal-assisted discovery still required

### 4. JGB futures
Status: **to investigate**

### 5. SOFR term rates
Status: **to investigate**

---

## Current implementation problems

## 1. Two competing implementations exist

The branch currently contains both:

### A. standalone scripts that appear to match the validated findings
- `bloomberg_scripts/extract_jgb.py`
- `bloomberg_scripts/extract_fx_vol.py`
- `bloomberg_scripts/extract_swaptions.py`
- various `test_*.py` and search/probe scripts

### B. newer package-style modules plus unified CLI
- `bloomberg_scripts/common/`
- `bloomberg_scripts/jgb_yields/`
- `bloomberg_scripts/fx_options/`
- `bloomberg_scripts/swaptions/`
- `bloomberg_scripts/caps_floors/`
- `bloomberg_scripts/cli.py`

This duplication makes it unclear which path is authoritative.

## 2. The package-style path has structural bugs

`BloombergSession.get_reference_data()` returns a DataFrame indexed by security, but several extractors assume a `ticker` column exists.

This affects multiple package-style modules and likely means the unified CLI is not actually runnable end-to-end in its current form.

## 3. The unified CLI exposes unvalidated features first

Current package CLI exposes:
- `swaptions`
- `caps`
- `jgb`
- `fx-options`

But the validated FX capability is **ATM implied vol**, not RR/BF.

## 4. Packaging/runtime support is incomplete

Current repo state:
- no Bloomberg install story in the main project config
- no `blpapi` source/index configuration in this repo
- no dedicated Bloomberg CLI entrypoint
- no explicit optional-dependency grouping for Bloomberg workflows

By contrast, `~/random-fin-tests` already contains a clean `uv` + Bloomberg index pattern.

## 5. Test/CI parity is missing

Current Bloomberg scripts are mostly manual scripts under `bloomberg_scripts/test_*.py`, not normal pytest coverage under `tests/`.

## 6. No clean data-model decision exists yet

It is still unclear whether Bloomberg is intended to be:
- a standalone export/probe layer only, or
- a first-class source inside `lseg_toolkit.timeseries`

That decision needs to be explicit before deeper integration.

---

## Guiding decisions for this plan

## Decision 1: Start with a stable standalone Bloomberg subsystem

For now, Bloomberg should be treated as a **standalone adjunct data source** that can:
- fill permission gaps,
- support discovery/probe workflows,
- export normalized data,
- optionally evolve into a first-class source later.

This avoids forcing immature Bloomberg option-vol workflows into the current TimescaleDB/scheduler stack before the data contracts are stable.

## Decision 2: Design for later integration with timeseries

Even if Bloomberg remains standalone initially, it should adopt the same engineering patterns as timeseries:
- explicit normalization
- clear asset/data-shape boundaries
- documented support matrix
- testable interfaces
- stable CLI surface

## Decision 3: Only supported/validated features should be user-facing

Initially supported Bloomberg features should be limited to:
- JGB yields
- FX ATM implied vol

Everything else should be clearly marked:
- experimental
- research only
- terminal-discovery only

---

## Target operating model

## Phase-1 operating model (recommended)

Supported Bloomberg code should move into `src/lseg_toolkit/bloomberg/`, while remaining outside `src/lseg_toolkit/timeseries/` for now. Research/probe utilities can remain under `bloomberg_scripts/` temporarily.

This gives Bloomberg normal package/test/entrypoint discipline without prematurely forcing it into timeseries storage/scheduler semantics.

Phase 1 should therefore produce a coherent repo subsystem with:

- one supported CLI surface
- one normalization layer
- one current support matrix
- pytest unit tests
- optional live Bloomberg integration tests
- installation/runtime docs

## Phase-2 operating model (optional later)

If stable, selected Bloomberg datasets can later be integrated into the timeseries subsystem with:
- vendor/source tagging
- storage integration where the shape cleanly matches existing tables
- scheduler integration for supported Bloomberg-native workflows

---

## Support matrix to adopt

## Supported

Features that are:
- validated against live Bloomberg Desktop API,
- documented,
- covered by unit tests,
- exposed in the supported CLI.

Planned initial supported set:
- JGB yields
- FX ATM implied vol

## Experimental

Features with promising implementation paths but incomplete validation:
- JGB futures
- SOFR term rates
- Treasury futures / basis helpers

## Research only

Features under active discovery where no stable support claim should be made:
- swaptions
- caps/floors
- FX RR/BF
- terminal-only or entitlement-sensitive datasets

---

## Architecture plan

## 1. Choose a single authoritative implementation path

### Recommended direction

Use the **validated standalone extraction logic as source-of-truth**, then port that logic into cleaned-up supported modules.

Why:
- the standalone scripts are the ones that match the validated findings in the docs
- the package-style modules currently contain shape/assumption bugs
- this minimizes the risk of keeping a broken abstraction as the primary path
- the standalone scripts are not ready-made library modules, so this should be treated as a deliberate refactor/port rather than a thin wrapper exercise

### Concrete rule

For each supported feature, there should be exactly one authoritative implementation path:
- one extraction function,
- one normalization path,
- one export path,
- one supported CLI command.

## 2. Add a Bloomberg normalization layer

Create one shared normalization layer for Bloomberg responses, covering:
- snapshot vs historical responses
- security/ticker identity handling
- extraction timestamp
- field presence / null behavior
- Bloomberg error metadata and entitlement failures
- normalized output column names

This should play the same role for Bloomberg that centralized shape mappings play in the timeseries stack.

## 3. Separate supported extractors from research/probe tools

Recommended layout direction:

```text
src/lseg_toolkit/bloomberg/
├── __init__.py
├── cli.py
├── connection.py
├── normalize.py
├── export.py
├── jgb.py
└── fx_atm_vol.py

bloomberg_scripts/
├── search_instruments.py
├── search_securities.py
├── swaptions_probe.py
├── caps_floors_probe.py
├── fx_rr_bf_probe.py
└── treasury_basis_exploration.py
```

The exact filenames can differ, but the conceptual split should be explicit:
- supported/package code under `src/`
- exploratory/research scripts outside the package surface

## 4. Keep data-shape decisions explicit

Do **not** force Bloomberg data into existing timeseries storage until the data shape is well-defined.

Proposed normalized shapes for phase 1:
- `bond_yield` for JGB yields
- `fx_vol_surface` for FX ATM implied vol

If Treasury basis matures later, define a specific schema then; do not imply support before a normalized contract exists.

---

## Packaging / runtime plan

## Objective

Make Bloomberg functionality installable and runnable in a clean, documented way, similar to the working pattern in `random-fin-tests`.

## Tasks

### 1. Add Bloomberg dependency support

Introduce a clean dependency path for:
- `blpapi`
- `pandas`
- `pyarrow` if parquet export remains a supported output

### 2. Add Bloomberg package index/source configuration

Mirror the `random-fin-tests` pattern for the Bloomberg package index.

### 3. Add a supported entrypoint

Recommended choices:
- `bbg-extract`
- or later `lseg-extract --source bloomberg`

For phase 1, a dedicated `bbg-extract` entrypoint is simpler and clearer.

### 4. Add import guards / runtime diagnostics

Adopt the `random-fin-tests` pattern of:
- graceful `ImportError` handling for `blpapi`
- clear instructions when Bloomberg Terminal is not reachable
- actionable hints for WSL/networking/runtime issues

---

## CLI plan

## Supported phase-1 CLI

The supported Bloomberg CLI should expose only validated capabilities.

### Proposed commands

```bash
uv run bbg-extract jgb --historical --start-date 2020-01-01
uv run bbg-extract fx-atm-vol --pairs EURUSD USDJPY GBPUSD
```

### Commands that should *not* be in the supported CLI yet
- swaptions
- caps/floors
- fx RR/BF
- treasury basis

Those can remain under research commands or explicit probe scripts.

---

## Testing plan

Adopt the same philosophy as the merged timeseries work:
- unit-test logic in CI
- keep live external integration tests opt-in

## 1. Unit tests under `tests/`

Proposed test layout:

```text
tests/bloomberg/
├── test_connection.py
├── test_normalize.py
├── test_cli.py
├── test_jgb.py
├── test_fx_atm_vol.py
├── test_treasury_basis.py
└── test_search.py
```

### Unit-test scope
- request/response normalization
- ticker generation/parsing
- field/error handling
- CLI argument handling
- export schema and filename behavior

Supported Bloomberg code should follow the same repo conventions as other maintained subsystems:
- library code under `src/`
- pytest coverage under `tests/`
- CI-safe unit tests by default
- live Bloomberg integration tests opt-in only


## 2. Live integration tests

Mark Bloomberg live tests with an integration marker and keep them opt-in.

Examples:
- connection smoke test
- JGB snapshot fetch
- FX ATM vol snapshot fetch
- optional historical fetch smoke test

## 3. CI policy

CI should run:
- Bloomberg unit tests
- no Bloomberg live integration by default

---

## Documentation plan

Bloomberg should adopt the same doc discipline as timeseries.

## Documents to add/update

### 1. `README.md`
Only mention Bloomberg after the supported CLI/runtime is stable.

### 2. `docs/instruments/BLOOMBERG.md`
Convert this into the current source of truth for:
- support matrix
- validated tickers/patterns
- research findings
- entitlement caveats

### 3. `docs/TESTING.md`
Add Bloomberg-specific testing commands and integration guidance.

### 4. `docs/DEVELOPMENT.md`
Document that:
- supported Bloomberg code lives under `src/lseg_toolkit/bloomberg/`
- Bloomberg unit tests live under `tests/bloomberg/`
- research/probe scripts in `bloomberg_scripts/` are not automatically product support claims

### 5. `docs/OUTSTANDING.md`
Add a Bloomberg backlog section so remaining work is tracked in the same style as other subsystems.

---

## Research-track plan for hard datasets

These should proceed as explicit discovery work, not supported feature work.

## 1. Swaptions

Research questions:
- Is the issue ticker format, entitlement, or Desktop API limitations?
- Are terminal-visible swaptions unavailable via Desktop API?
- Is B-PIPE required?

## 2. Caps / floors

Research questions:
- Can the correct ticker format be discovered via `//blp/instruments`?
- Is the relevant data source ICAP/BGN/other?
- Are these terminal-only?

## 3. FX RR/BF

Research questions:
- Are the returned ATM-like values actually source-specific placeholders?
- Are different quote sources required?
- Is a different field set needed versus `PX_LAST`?

## Research tooling requirements

For these datasets, standardize a discovery workflow using:
- terminal-assisted search (`SECF`, help/help, screen click-through)
- `instrumentListRequest`
- search scripts
- explicit logging of ticker, source, error category, entitlement behavior

---

## Future timeseries integration plan (optional)

Only attempt this after the standalone Bloomberg subsystem is stable.

## Preconditions
- supported features have stable normalized schemas
- packaging/runtime path is solved
- unit tests exist
- docs reflect reality
- feature support levels are explicit

## Potential integration targets

### JGB yields
Likely candidate for eventual integration into the existing `bond` timeseries shape.

### Treasury futures / basis
May fit only partially. Basis/CTD data may need a separate derivative/basis representation rather than forcing it into current fact tables. Keep this experimental until there is:
- one normalized extractor entrypoint
- one documented schema
- one testable non-ad-hoc module

### FX ATM implied vol
Should not be forced into current quote/ohlcv tables. This likely needs either:
- a Bloomberg-only normalized export path, or
- future option/vol-specific modeling.

---

## Implementation milestones

## Milestone 1 — Bloomberg foundation / mergeability

Goal: make the Bloomberg branch internally coherent and runnable.

**Status update (2026-03-24):** materially in progress.

Completed so far:
- created `src/lseg_toolkit/bloomberg/`
- added supported package modules for JGB and FX ATM vol
- added a supported `bbg-extract` CLI surface
- added normalization / connection / export helpers
- added initial pytest scaffolding under `tests/bloomberg/`
- added Bloomberg runtime support in `pyproject.toml`
- added runtime diagnostics / import guards for supported Bloomberg entrypoints
- reclassified `bloomberg_scripts/` as legacy / research-oriented in docs
- updated `docs/OUTSTANDING.md` with a Bloomberg backlog section
- added runtime warnings on the legacy `bloomberg_scripts` CLI path
- quarantined the legacy modular Bloomberg extractor paths with explicit warnings
- updated `README.md` with Bloomberg install/runtime notes and examples
- verified wheel packaging includes `lseg_toolkit.bloomberg` modules and the `bbg-extract` entrypoint

Still remaining:
- decide whether the quarantined legacy modular Bloomberg extractors should be fully retired later
- keep reducing confusion around duplicate old codepaths in docs and examples
- run/expand test coverage once the Bloomberg-enabled environment is available

### Tasks
- [x] choose one authoritative implementation path
- [ ] fix current DataFrame/ticker-shape bugs
- [x] separate supported vs research codepaths
- [x] add a stable Bloomberg normalization layer
- [x] remove or de-emphasize duplicate broken paths
- [x] move supported Bloomberg code under `src/lseg_toolkit/bloomberg/`

### Exit criteria
- supported commands run from one coherent CLI path
- no known structural breakage in the primary implementation

### Concrete implementation checklist

#### 1. Establish package boundary
- [x] create `src/lseg_toolkit/bloomberg/`
- [x] add `__init__.py`
- [x] add a minimal `cli.py`
- [x] keep `bloomberg_scripts/` for research/probe scripts only

#### 2. Port the first two supported datasets
- [x] port `bloomberg_scripts/extract_jgb.py` into a supported `jgb.py` module
- [x] port `bloomberg_scripts/extract_fx_vol.py` into a supported `fx_atm_vol.py` module
- [x] preserve current validated ticker patterns and output semantics during the port
- [x] avoid depending on current broken package extractors while porting

#### 3. Build a minimal shared support layer
- [x] add a supported Bloomberg connection helper
- [x] add normalization helpers for:
  - [x] snapshot responses
  - [x] historical responses
  - [x] security/ticker identity
  - [x] extraction timestamps
  - [x] error/entitlement metadata
- [x] add shared export helpers only if still needed by the ported modules

#### 4. Shrink the supported CLI surface
- [x] expose only:
  - [x] `jgb`
  - [x] `fx-atm-vol`
- [x] do not expose:
  - [x] `swaptions`
  - [x] `caps`
  - [x] `fx-options`
  - [x] `treasury-basis`

#### 5. Reclassify current Bloomberg code
- [x] mark treasury basis work as experimental in docs
- [x] mark swaptions as research-only in docs
- [x] mark caps/floors as research-only in docs
- [x] mark FX RR/BF as research-only in docs
- [x] relabel or relocate existing probe/search scripts accordingly

#### 6. Add minimal test scaffolding
- [x] create `tests/bloomberg/`
- [x] add unit tests for:
  - [x] CLI argument parsing
  - [x] response normalization
  - [x] JGB ticker mapping
  - [x] FX ATM vol ticker generation/parsing
- [x] defer live Bloomberg integration tests until the supported CLI path exists

#### 7. Prepare packaging/runtime follow-through for Milestone 3
- [x] identify exact `pyproject.toml` changes needed for Bloomberg dependency support
- [x] identify exact entrypoint name and module path
- [x] identify which README/testing/development doc updates can wait until the supported CLI is real

## Milestone 2 — Supported Bloomberg v1

Goal: expose only validated functionality.

### Tasks
- [x] productize JGB yields
- [x] productize FX ATM vol
- [x] add pytest unit coverage for supported features
- [x] add optional live Bloomberg integration smoke tests
- [x] update docs to match actual support level

### Exit criteria
- repo has a supported Bloomberg CLI and current docs
- validated capabilities are unit-test-backed and documented
- final Bloomberg Terminal/Desktop API verification is deferred to the end-of-stream testing pass

## Milestone 3 — Packaging / developer parity

Goal: make Bloomberg tooling easy to install and use.

### Tasks
- [x] update `pyproject.toml` with a Bloomberg dependency path and index/source configuration
- [x] ensure supported Bloomberg package code is included in packaging
- [x] add dedicated CLI entrypoint
- [x] add runtime diagnostics / import guards
- [x] add Bloomberg section to testing/development docs
- [x] update `README.md` with Bloomberg install/runtime notes only once the supported CLI is stable

### Exit criteria
- a new machine can install and run supported Bloomberg commands from documented steps

## Milestone 4 — Research toolkit for hard gaps

Goal: formalize discovery work for unresolved Bloomberg datasets.

### Tasks
- [x] move swaptions/caps/floors/RR-BF into explicit research/probe workflows
- [x] standardize instrument-search and terminal-discovery playbooks
- [x] document findings with exact tested patterns and outcomes
- [ ] investigate JGB futures and SOFR term rates as likely next incremental wins

### Exit criteria
- unsupported areas are clearly tracked as research, not implied product support

## Milestone 5 — Source-integration decision

Goal: explicitly decide whether Bloomberg remains standalone or joins the timeseries stack.

### Tasks
- [x] review normalized schemas against existing `timeseries_*` storage shapes
- [x] decide whether vendor/source tagging is needed in core storage
- [x] decide whether any Bloomberg-supported datasets belong in scheduler jobs

### Decision
- Bloomberg remains a **standalone adjunct source for now**.
- Supported Bloomberg workflows stay under `src/lseg_toolkit/bloomberg/` and the `bbg-extract` CLI.
- Bloomberg data does **not** join `timeseries` storage or scheduler jobs yet.
- Any future integration should wait until after the deferred Bloomberg-enabled validation pass and should likely start with JGB yields only.
- Vendor/source tagging in core storage can be revisited later if Bloomberg support broadens beyond the current narrow supported surface.

### Exit criteria
- a conscious integration decision exists with clear constraints

---

## Recommended immediate sequence

1. Write and adopt the support matrix.
2. Choose the authoritative implementation path.
3. Port JGB yields and FX ATM vol into supported package modules.
4. Replace the supported CLI surface with JGB + FX ATM vol only.
5. Add pytest unit coverage for JGB, FX ATM vol, and normalization.
6. Add Bloomberg dependency/index/runtime support to the repo.
7. Move swaptions/caps/floors/RR-BF and Treasury basis into explicit research/experimental status.

---

## Open questions for implementation review

1. Should any specific research utilities be retained under `bloomberg_scripts/`, or should they move into a more explicit `scripts/` or `research/` area?
2. Should supported Bloomberg functionality be packaged as a dedicated CLI now (`bbg-extract`) or remain module-invoked initially?
3. Is Treasury basis best treated as a supported Bloomberg feature or left as a research helper until its output schema is normalized?
4. Should JGB yields be the first dataset promoted into the existing `timeseries_bond` model later, or should all Bloomberg datasets remain export-only until source-tagging exists?
5. Should `random-fin-tests` remain the place for fast Bloomberg experimentation, with this repo holding only supported Bloomberg workflows?

---

## Success criteria

This plan is successful when:
- Bloomberg support claims in the repo are narrow and true,
- the supported Bloomberg CLI actually runs,
- validated Bloomberg workflows are unit-tested and documented,
- research-grade Bloomberg work is clearly separated from supported functionality,
- the repo is positioned to integrate Bloomberg into the broader timeseries model later without a rewrite.


---

## Deferred end-of-stream Bloomberg testing plan

This branch is not being developed in a live Bloomberg-enabled environment right now.
So the remaining Bloomberg Desktop API / Terminal verification should happen in one final pass
after the implementation stream is otherwise complete.

### Supported-workflow validation to run later
- `bbg-extract jgb`
- `bbg-extract jgb --historical --start-date 2025-01-01`
- `bbg-extract fx-atm-vol --pairs EURUSD USDJPY --tenors 1M 3M`
- `RUN_BLOOMBERG_INTEGRATION=1 uv run pytest tests/bloomberg/test_integration.py -m integration -v`

### Research validation to run later
- terminal-assisted swaption discovery (`VCUB`, `SECF`, `ALLQ`)
- terminal-assisted caps/floors discovery (`SECF`, `ALLQ`)
- FX RR/BF quote-source validation (`ALLQ`, surface-cell help)
- JGB futures and SOFR term candidate validation

### Goal of the final Bloomberg pass
- confirm supported workflows return real data in the expected normalized schemas
- confirm runtime diagnostics are sufficient when Bloomberg is unavailable or not entitled
- capture fresh research findings for still-unsupported datasets
