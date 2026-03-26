# Bloomberg Research / Probe Plan

## Objective

Use Bloomberg for two distinct workflows:

1. **Supported Bloomberg extraction** lives in `src/lseg_toolkit/bloomberg/` and is exposed through `bbg-extract`.
2. **Research / probe scripts** live in `bloomberg_scripts/` and are used to discover ticker formats, validate entitlements, and investigate unsupported datasets.

This document is specifically for the **research/probe** side of that split.

---

## Scope

- **Supported CLI**: `bbg-extract`
- **Research / probe location**: `bloomberg_scripts/`
- **Output**: CSV or Parquet files only
- **API**: Bloomberg Desktop API via local Terminal
- **Not in scope**: making `python -m bloomberg_scripts` the supported interface

> Note: some Bloomberg workflows have already been promoted to `bbg-extract`.
> This document tracks the remaining discovery work and legacy probe scripts.

---

## What is already supported elsewhere

These workflows are being productized through the supported package/CLI surface:

- JGB yields
- FX ATM implied volatility

If you want those workflows, use `bbg-extract`, not the research scripts.

---

## Research priorities

### 1. Swaptions
LSEG status: access denied / permission-restricted
Bloomberg status: terminal-visible, API access not confirmed

Goals:
- confirm whether Bloomberg Desktop API exposes the data
- discover the correct ticker format if it does
- determine whether B-PIPE or special entitlements are required

### 2. Interest rate caps/floors
LSEG status: access denied / premium data
Bloomberg status: ticker format still unknown

Goals:
- discover the correct Bloomberg ticker pattern
- verify whether the data is available through the Desktop API
- determine whether the useful source is ICAP, BGN, or another venue

### 3. FX risk reversals / butterflies
LSEG status: access denied / premium data
Bloomberg status: current patterns appear to resolve incorrectly or behave like ATM vol

Goals:
- determine whether the issue is ticker format or entitlement
- verify whether a different field set is required
- confirm whether the data is genuinely available via Desktop API

### 4. JGB futures / basis exploration
LSEG status: unknown
Bloomberg status: needs validation

Goals:
- validate front-month tickers
- determine whether historical data is usable
- decide whether this belongs in a supported workflow later

### 5. SOFR term rates
LSEG status: unknown
Bloomberg status: needs validation

Goals:
- validate candidate `TSFR*` tickers
- compare against alternative patterns if needed

---

## Research script layout

```
bloomberg_scripts/
├── __init__.py              # legacy/research package marker
├── __main__.py              # legacy/research module entry point
├── cli.py                   # legacy/research CLI only
├── search_instruments.py    # instrument discovery
├── search_securities.py     # security discovery
├── extract_swaptions.py     # swaption exploration
├── test_swaption_*.py       # swaption probe scripts
├── test_fx_*.py             # FX vol / RR-BF probes
├── test_bond_basis.py       # Treasury basis exploration
└── test_bond_futures_basis.py
```

Supported Bloomberg code lives separately in:

```
src/lseg_toolkit/bloomberg/
```

---

## Dataset-to-script map

| Dataset | Primary probe scripts | Terminal functions to use later | Current status |
|---------|------------------------|----------------------------------|----------------|
| Swaptions | `extract_swaptions.py`, `test_swaption_tickers.py`, `test_swaption_nvol.py`, `test_swaption_eusn.py` | `VCUB`, `SECF`, `ALLQ`, `<HELP><HELP>` on target cells | Research-only |
| Caps/floors | `search_instruments.py`, `search_securities.py`, `bloomberg_scripts/caps_floors/` | `SECF`, `ALLQ`, `<HELP><HELP>` on terminal quotes | Research-only |
| FX RR/BF | `test_fx_tickers.py`, `bloomberg_scripts/fx_options/` | `OVDV`, `ALLQ`, `<HELP><HELP>` on vol surface cells | Research-only |
| Treasury basis / CTD | `test_bond_basis.py`, `test_bond_futures_basis.py` | `DLV`, contract pages, `<HELP><HELP>` on CTD fields | Experimental |
| JGB futures | `search_instruments.py`, `search_securities.py` | `SECF`, contract pages, futures chain screens | Research-only |
| SOFR term | `search_instruments.py`, `search_securities.py` | `SECF`, index pages, rate monitor screens | Research-only |

---

## Next incremental validation targets

### JGB futures
Start with these candidates later in Terminal/Desktop API:
- `JB1 Comdty`
- `JBM1 Comdty`
- `JF1 Comdty`
- specific-contract pattern: `{ROOT}{MONTH}{YEAR} Comdty`

Suggested later checks:
- `python bloomberg_scripts/search_securities.py "JGB futures OSE"`
- verify `PX_LAST`, `PX_OPEN`, `PX_HIGH`, `PX_LOW`, `VOLUME`, `OPEN_INT`
- test whether historical data is available with the same fields

### SOFR term rates
Start with these candidates later in Terminal/Desktop API:
- `TSFR1M Index`
- `TSFR3M Index`
- `TSFR6M Index`
- `TSFR12M Index`
- fallback candidates: `USOSFR1 Curncy`, related `SOFR*` / `TSFR*` search hits

Suggested later checks:
- `python bloomberg_scripts/search_securities.py "TSFR term sofr"`
- verify `PX_LAST` and `LAST_UPDATE`
- compare terminal-visible naming against Desktop API search results

---

## Terminal-assisted discovery playbook

When you have Bloomberg Terminal access later, use this sequence:

1. **Find the security on terminal first**
   - `SECF` for candidate discovery
   - terminal search results for yellow-key and source confirmation
2. **Open the exact object you think should work**
   - use the terminal-resolved security rather than guessing spacing/source
3. **Inspect provenance from the terminal**
   - `<HELP><HELP>` on the quote or surface cell
   - `ALLQ` to inspect available contributors / quote sources
   - `DLV` for Treasury futures deliverable-basket context
4. **Only then retry Desktop API**
   - test the exact terminal-resolved ticker
   - test both reference and historical requests if relevant
5. **Classify the failure mode**
   - invalid security format
   - valid security but not entitled
   - terminal-visible but Desktop API unavailable
   - field not applicable

---

The current accumulated findings log lives in `docs/BLOOMBERG_FINDINGS.md`.

## Findings log format

For each new probe session, capture:

- date
- dataset
- terminal function used (`SECF`, `VCUB`, `ALLQ`, `DLV`, etc.)
- exact ticker(s) tried
- exact field(s) tried
- Desktop API result
- terminal result
- inferred failure type
- next candidate to test

Suggested markdown template:

```text
### YYYY-MM-DD — <dataset>
- Terminal path:
- Candidate ticker(s):
- Fields:
- Desktop API result:
- Terminal result:
- Interpretation:
- Next step:
```

---

## Research workflow

### Step 1: Discover ticker candidates
Use `search_instruments.py` and `search_securities.py` to identify plausible
security names, yellow-key types, and field combinations.

### Step 2: Probe one dataset at a time
Use the focused scripts to test a single hypothesis:
- ticker format
- yellow key
- field selection
- entitlement behavior
- historical availability

### Step 3: Record what failed
For every negative result, capture:
- exact ticker tried
- field set
- security error / message
- whether the issue looks like format, entitlement, or unsupported API access

### Step 4: Promote only validated workflows
If a dataset becomes stable and repeatable, it should move into the supported
package/CLI surface rather than staying in `bloomberg_scripts/`.

---

## Usage examples

### Supported workflows
Use the supported CLI:

```bash
bbg-extract jgb --historical --start-date 2020-01-01
bbg-extract fx-atm-vol --pairs EURUSD USDJPY GBPUSD
```

### Research / probe workflows
Run the probe scripts directly:

```bash
python bloomberg_scripts/search_instruments.py "swaption USD"
python bloomberg_scripts/search_securities.py "cap floor USD"
python bloomberg_scripts/test_swaption_tickers.py
python bloomberg_scripts/test_fx_tickers.py
```

Avoid treating `python -m bloomberg_scripts` as the supported interface; it is legacy/research only.

---

## Output format

Research scripts may write:
- CSV files for quick inspection
- Parquet files for offline analysis
- stdout tables or logs during discovery

Suggested output paths:

```text
data/bloomberg/research/swaptions/
data/bloomberg/research/caps_floors/
data/bloomberg/research/fx_options/
```

---

## Verification

1. **Supported Bloomberg check**: run `bbg-extract jgb` or `bbg-extract fx-atm-vol`
2. **Discovery check**: run the specific research script for the dataset you are probing
3. **Validation check**: verify ticker, field, and security error behavior against the Bloomberg Terminal
4. **Promotion check**: only move a workflow into the supported package after it has a stable, repeatable contract

---

## Dependencies

Research scripts still require the Bloomberg Desktop API environment:

```text
blpapi
pandas
pyarrow (if writing Parquet)
```

Bloomberg Terminal must be running locally for live requests.

---

## Deferred Bloomberg Terminal validation

Because this branch is being developed outside a live Bloomberg Desktop API environment,
final live validation should happen at the end of the implementation stream.

When Terminal access is available, run in order:

```bash
# Supported workflows first
bbg-extract jgb
bbg-extract jgb --historical --start-date 2025-01-01
bbg-extract fx-atm-vol --pairs EURUSD USDJPY --tenors 1M 3M
RUN_BLOOMBERG_INTEGRATION=1 uv run pytest tests/bloomberg/test_integration.py -m integration -v

# Then research probes
python bloomberg_scripts/search_instruments.py "swaption USD"
python bloomberg_scripts/search_securities.py "cap floor USD"
python bloomberg_scripts/test_swaption_tickers.py
python bloomberg_scripts/test_fx_tickers.py
```

Do the supported CLI/live smoke checks first; only then spend time on research probes.
