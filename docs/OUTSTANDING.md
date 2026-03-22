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

## Technical Debt

### Code Refactoring

| Item | Impact | Est. LOC Reduction |
|------|--------|-------------------|
| Complete FieldMapper rollout + tests | Centralize LSEG field mappings consistently | -400 |
| Extract `_bulk_insert` helper | DRY for all save functions | -150 |

See `dev_scripts/refactor_recommendations.md` for detailed analysis.

### Code Updates

| File | Change Needed |
|------|---------------|
| `fetch.py` | Reduce remaining ad hoc field mappings where possible |
| `storage/field_mapping.py` | Expand test coverage and keep mappings canonical |

---

## Tests

- [x] Intraday data fetching tests in `tests/timeseries/test_integration.py`
- [ ] Broader end-to-end intraday storage/pipeline integration coverage
