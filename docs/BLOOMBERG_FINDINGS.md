# Bloomberg Research Findings Log

This file records concrete Bloomberg probe findings for datasets that are still
experimental or research-only.

For the current supported Bloomberg surface, see:
- `bbg-extract`
- `docs/instruments/BLOOMBERG.md`

For the research workflow/playbook, see:
- `docs/BLOOMBERG_SCRIPTS.md`

---

## 2026-01-16 — FX RR/BF

### Dataset
FX risk reversals and butterflies

### Scripts / probes
- `bloomberg_scripts/test_fx_tickers.py`
- `bloomberg_scripts/fx_options/`

### Patterns tried

| Pattern | Example | Outcome |
|---------|---------|---------|
| `{PAIR}{TENOR}{DELTA}RR BGN Curncy` | `EURUSD1M25RR BGN Curncy` | Resolves but appears to return ATM-like value |
| `{PAIR}{TENOR}{DELTA}BF BGN Curncy` | `EURUSD1M25BF BGN Curncy` | Resolves but appears to return ATM-like value |
| `{PAIR}RR{TENOR} BGN Curncy` | `EURUSDRR1M BGN Curncy` | Invalid |
| `{PAIR}25RR{TENOR} BGN Curncy` | `EURUSD25RR1M BGN Curncy` | Invalid |
| inverted/alternative pair order | `JPYUSD1M25RR BGN Curncy` | No validated success |

### Current interpretation
- Bloomberg Desktop API access to true RR/BF remains unconfirmed.
- Existing RR/BF-like tickers may be aliases, placeholders, or simply the wrong
  quote source.
- This remains **research-only**.

### Next terminal checks
- `ALLQ` on candidate RR/BF securities
- surface-cell `<HELP><HELP>` on Bloomberg FX vol screens
- confirm quote source and field applicability versus ATM vol

---

## 2026-01-16 — Swaptions

### Dataset
Swaption volatility / normal-vol surfaces

### Scripts / probes
- `bloomberg_scripts/extract_swaptions.py`
- `bloomberg_scripts/test_swaption_tickers.py`
- `bloomberg_scripts/test_swaption_nvol.py`
- `bloomberg_scripts/test_swaption_eusn.py`

### Terminal observation
- terminal screen label observed: `EUR SWPT NVOL 1Y10Y`
- candidate ticker from terminal context: `EUSN0110 BVOL Curncy`

### Patterns tried

| Pattern | Example | Outcome |
|---------|---------|---------|
| `EUSN{exp}{tenor} BVOL Curncy` | `EUSN0110 BVOL Curncy` | No data via Desktop API |
| `EUSN{exp}{tenor} NVOL Curncy` | `EUSN0110 NVOL Curncy` | No data via Desktop API |
| `USSN{exp}{tenor} BVOL Curncy` | `USSN0110 BVOL Curncy` | No data via Desktop API |
| `USSV{exp}{tenor} BGN Curncy` | `USSV1Y10Y BGN Curncy` | Unknown security |
| `USSW{exp}{tenor} BGN Curncy` | `USSW1Y10Y BGN Curncy` | Unknown security |
| `{CCY}SWPTNVOL{exp}{tenor}` | `EURSWPTNVOL1Y10Y Curncy` | Unknown security |
| `{CCY} SWPT NVOL {exp}{tenor} Index` | `EUR SWPT NVOL 1Y10Y Index` | Wrong object / FX spot-like result |

### Broader search space already attempted
- V-pattern variants like `USDSWV1Y10Y`
- normal-vol / black-vol prefixes like `USSN`, `USSB`, `USSL`
- SOFR-based prefixes
- multiple quote sources: `ICAP`, `GFI`, `BGN`
- index vs currency yellow keys
- spacing and formatting variations

### Current interpretation
- terminal visibility does **not** yet imply Desktop API accessibility.
- likely failure modes are one of:
  - still-wrong ticker format,
  - entitlement restriction,
  - terminal-only visibility,
  - B-PIPE-only access.
- This remains **research-only**.

### Next terminal checks
- `VCUB`
- `SECF`
- `ALLQ`
- `<HELP><HELP>` on exact terminal cells

---

## 2026-01-16 — Caps / Floors

### Dataset
Interest-rate caps and floors

### Scripts / probes
- `bloomberg_scripts/caps_floors/`
- `bloomberg_scripts/search_instruments.py`
- `bloomberg_scripts/search_securities.py`

### Patterns tried

| Pattern | Example | Outcome |
|---------|---------|---------|
| `USCP{tenor}A ICAP Curncy` | `USCP5YA ICAP Curncy` | Unknown security |
| `USCP{tenor}+{strike} ICAP Curncy` | `USCP5Y+150 ICAP Curncy` | Unknown security |
| `EUCP{tenor}A ICAP Curncy` | `EUCP5YA ICAP Curncy` | Unknown security |
| `USDSRCAP{tenor} ICAP Curncy` | `USDSRCAP5Y ICAP Curncy` | Unknown security |
| `USCPVOL{tenor} BGN Curncy` | `USCPVOL5Y BGN Curncy` | Unknown security |

### Current interpretation
- no validated Bloomberg Desktop API ticker pattern yet.
- terminal-assisted discovery is still required.
- This remains **research-only**.

### Next terminal checks
- `SECF`
- `ALLQ`
- `<HELP><HELP>` on any terminal-resolved cap/floor quote

---

## 2026-01-16 — Treasury futures / CTD / basis

### Dataset
Treasury futures plus CTD/basis fields

### Scripts / probes
- `bloomberg_scripts/test_bond_basis.py`
- `bloomberg_scripts/test_bond_futures_basis.py`

### Validated futures tickers
- `TU1 Comdty`
- `FV1 Comdty`
- `TY1 Comdty`
- `UXY1 Comdty`
- `US1 Comdty`
- `WN1 Comdty`

### Validated current/snapshot field behavior

| Field | Outcome |
|-------|---------|
| `FUT_CTD_TICKER` | Working on specific contracts |
| `FUT_CTD_CUSIP` | Working on specific contracts |
| `FUT_CTD_ISIN` | Working on specific contracts |
| `FUT_CTD_NET_BASIS` | Working |
| `FUT_CTD_GROSS_BASIS` | Working |
| `FUT_CTD_IMPLIED_REPO` | Not available |
| `FUT_CTD_CONV_FACTOR` | Not available |
| `FUT_DLVRBL_BNDS_*` | Not available via API |

### Historical behavior

| Field | Outcome |
|-------|---------|
| `PX_LAST` | Historical available |
| `FUT_CTD_NET_BASIS` | Historical available |
| `FUT_CTD_GROSS_BASIS` | Historical available |
| `FUT_CTD_IMPLIED_REPO` | Not historically available |

### Current interpretation
- useful enough for **experimental** research helpers.
- not yet normalized enough for the supported CLI surface.

### Next terminal checks
- `DLV`
- contract pages
- `<HELP><HELP>` on CTD-related fields

---

## Deferred later validation targets

These have candidate starting points but have **not** yet been live-validated in
this implementation pass.

### JGB futures
Candidate starting points:
- `JB1 Comdty`
- `JBM1 Comdty`
- `JF1 Comdty`
- `{ROOT}{MONTH}{YEAR} Comdty`

### SOFR term rates
Candidate starting points:
- `TSFR1M Index`
- `TSFR3M Index`
- `TSFR6M Index`
- `TSFR12M Index`

### Planned later checks
- verify terminal resolution first
- verify `PX_LAST` / `LAST_UPDATE`
- check historical availability
- record findings here after the Bloomberg-enabled pass

---

## 2026-03-25 — Supported Bloomberg surface validation attempt

### Dataset
Supported Bloomberg workflows:
- JGB yields
- FX ATM implied volatility

### Environment / preflight
- `uv sync --group bloomberg --group test` completed successfully
- `blpapi==3.26.2.1` installed
- Desktop API port reachable on `localhost:8194`
- supported CLI surface present:
  - `bbg-extract jgb`
  - `bbg-extract fx-atm-vol`

### Commands run
- `uv run bbg-extract jgb`
- `uv run bbg-extract jgb --historical --start-date 2025-01-01 --tenors 2Y 5Y 10Y 20Y 30Y 40Y`
- `uv run bbg-extract fx-atm-vol --pairs EURUSD USDJPY GBPUSD AUDUSD USDCHF USDCAD --tenors 1W 1M 2M 3M 6M 9M 1Y 2Y`
- `uv run bbg-extract fx-atm-vol --historical --start-date 2025-01-01 --pairs EURUSD USDJPY --tenors 1M 3M`
- `RUN_BLOOMBERG_INTEGRATION=1 uv run pytest tests/bloomberg/test_integration.py -m integration -v`

### Tickers / fields checked
- JGB spot probe:
  - ticker: `GJGB10 Index`
  - fields: `PX_LAST`, `NAME`, `LAST_UPDATE`
- FX ATM vol spot probe:
  - ticker: `EURUSDV1M BGN Curncy`
  - fields: `PX_LAST`, `NAME`, `LAST_UPDATE`

### Result
- all supported CLI commands returned `No data returned`
- raw `BloombergSession.get_reference_data(...)` calls returned empty DataFrames
- integration smoke tests failed because both extractors returned empty DataFrames

### Bloomberg response summary
- low-level `blpapi` probing indicated a Bloomberg-side access / workflow
  restriction rather than a simple connectivity failure.

### Current interpretation
- this is not a simple connectivity failure: the Desktop API session starts and
  `//blp/refdata` opens successfully.
- the current host/account is blocked at request time by a Bloomberg workflow /
  entitlement review gate.
- the branch's supported Bloomberg surface therefore remains **not yet
  validated live** on this machine.

### Next step
- resolve Bloomberg-side workflow review / entitlement access first
- rerun the supported CLI checks and integration smoke tests after access is
  restored
