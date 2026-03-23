# Backlog

Active TODOs and feature requests for jl-lseg-toolkit.

---

## Features & Research

### Prediction Markets / Polymarket
**Priority:** Medium
**Status:** Partial - core ingest landed, follow-up hardening remains

- fold explicit Polymarket candlestick derivation into the default
  `backfill()` / `daily_refresh()` path only if we want that behavior by default
- tighten Polymarket ↔ FOMC linkage rules before writing `fomc_meeting_id`
- add regression tests around any future FOMC-linkage write heuristics
- decide whether to persist raw Polymarket trades separately later
- evaluate whether active-market snapshot enrichment should populate
  Polymarket bid/ask close fields
- add durable troubleshooting examples for Polymarket vs Kalshi comparisons

### Credit Instruments (CDS)
**Priority:** Low
**Status:** Partial - daily only, intraday not available

CDS indices (IBOXIG05=MP, IBOXHY05=MP) work for daily data but not intraday. Documented in INSTRUMENTS.md.

### Options Research
**Priority:** Low
**Status:** Not started

Individual options RICs don't support time series (only snapshots). Need to research chain discovery and Greeks fields.

---

## Technical Debt

### Code Refactoring

| Item | Impact | Est. LOC Reduction |
|------|--------|-------------------|
| Audit remaining field-mapping edge cases | Keep normalized mappings canonical as new instruments are added | -400 |
| Extract `_bulk_insert` helper | DRY for all save functions | -150 |

See `dev_scripts/refactor_recommendations.md` for detailed analysis.

### Code Updates

| File | Change Needed |
|------|---------------|
| `fetch.py` | Keep shape-specific normalization aligned with storage mappings |
| `storage/field_mapping.py` | Extend mappings/tests as new fields or asset classes are added |

---

## Tests

- [x] Intraday data fetching tests in `tests/timeseries/test_integration.py`
- [x] Broader end-to-end intraday storage/pipeline integration coverage
- [x] Filter sparse intraday volume-only OHLCV bars in fetch, while keeping storage skip as a final safeguard
