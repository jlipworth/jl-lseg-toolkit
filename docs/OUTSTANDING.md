# Backlog

Active TODOs and feature requests for jl-lseg-toolkit.

---

## Features & Research

### Credit Instruments (CDS)
**Priority:** Low
**Status:** Partial - daily only, intraday not available

CDS indices (IBOXIG05=MP, IBOXHY05=MP) work for daily data but not intraday. Documented in INSTRUMENTS.md.

### Options Research
**Priority:** Low
**Status:** Not started

Individual options RICs don't support time series (only snapshots). Need to research chain discovery and Greeks fields.

---

## Schema

Missing instrument detail tables:

| Table | Asset Classes |
|-------|---------------|
| `instrument_commodity` | Commodity spot (not futures) |
| `instrument_cds` | CDS indices, sovereign CDS |
| `instrument_option` | Options chains metadata |

---

## Technical Debt

### Code Refactoring

| Item | Impact | Est. LOC Reduction |
|------|--------|-------------------|
| Extract FieldMapper class | Centralize LSEG field mappings | -400 |
| Extract `_bulk_insert` helper | DRY for all save functions | -150 |
| Unify instrument detail saves | Replace 7 functions with 1 | -310 |

See `dev_scripts/refactor_recommendations.md` for detailed analysis.

### Code Updates

| File | Change Needed |
|------|---------------|
| `fetch.py` | Add field mappings for different data shapes |
| `constants.py` | Add LSEG -> storage field mappings |

---

## Tests

- [ ] Intraday data fetching tests
- [ ] Integration tests with LSEG API
