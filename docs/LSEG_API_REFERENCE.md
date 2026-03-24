# LSEG API Reference

Repo-specific reference notes for working with the LSEG Workspace API.

## Scope

This document is for:
- batching / API-shape reminders
- field and query-pattern notes
- repo-specific symbol / RIC conventions used by current code

The source of truth for timeseries mappings is:
- `src/lseg_toolkit/timeseries/constants.py`
- the instrument docs under `docs/instruments/`

## General API guidance

### Batch requests whenever possible

```python
# Prefer one batched request
rd.get_data(["AAPL.O", "MSFT.O"], ["TR.CommonName", "TR.CompanyMarketCap"])
```

### Keep repo docs aligned with current code

If you update:
- supported symbols
- RIC roots
- instrument groups
- field assumptions

then update both the code and the relevant docs in the same PR.

## Time-series mapping notes

### US Treasury futures (current code)

| CME Symbol | LSEG root | Front contract |
|------------|-----------|----------------|
| `ZT` | `TU` | `TUc1` |
| `Z3N` | `Z3N` | `Z3Nc1` |
| `ZF` | `FV` | `FVc1` |
| `ZN` | `TY` | `TYc1` |
| `TN` | `TN` | `TNc1` |
| `TWE` | `TWE` | `TWEc1` |
| `ZB` | `US` | `USc1` |
| `UB` | `UB` | `UBc1` |

### European bond futures (current code)

| Symbol | LSEG root | Front contract |
|--------|-----------|----------------|
| `FGBL` | `FGBL` | `FGBLc1` |
| `FGBM` | `FGBM` | `FGBMc1` |
| `FGBS` | `FGBS` | `FGBSc1` |
| `FGBX` | `FGBX` | `FGBXc1` |
| `FLG` | `FLG` | `FLGc1` |

### FX spot mappings

| Pair symbol | LSEG RIC |
|-------------|----------|
| `EURUSD` | `EUR=` |
| `GBPUSD` | `GBP=` |
| `USDJPY` | `JPY=` |
| `USDCHF` | `CHF=` |
| `AUDUSD` | `AUD=` |
| `USDCAD` | `CAD=` |
| `NZDUSD` | `NZD=` |
| `EURGBP` | `EURGBP=` |
| `EURJPY` | `EURJPY=` |
| `EURCHF` | `EURCHF=` |
| `GBPJPY` | `GBPJPY=` |

### OIS pattern

Current code uses:

```text
{CCY}{tenor}OIS=
```

Examples:
- `USD1MOIS=`
- `USD10YOIS=`
- `EUR5YOIS=`

## Common repo assumptions

- Continuous futures use `{root}c1`, `{root}c2`, etc.
- Bare Treasury tenors in the CLI default to US Treasuries
- Explicit sovereign symbols use country-prefixed tenors such as `DE10Y` or `GB10Y`
- Explicit RIC usage is supported by passing the RIC directly; there is no special `--ric` CLI flag

## Related docs

- [INSTRUMENTS.md](INSTRUMENTS.md)
- [TIMESERIES.md](TIMESERIES.md)
- [SCHEDULER.md](SCHEDULER.md)
