# Bond Futures

Current bond-futures mappings represented by `src/lseg_toolkit/timeseries/constants.py`.

## US Treasury futures

| CME Symbol | LSEG root | Front contract | Contract |
|------------|-----------|----------------|----------|
| `ZT` | `TU` | `TUc1` | 2-Year T-Note |
| `Z3N` | `Z3N` | `Z3Nc1` | 3-Year T-Note |
| `ZF` | `FV` | `FVc1` | 5-Year T-Note |
| `ZN` | `TY` | `TYc1` | 10-Year T-Note |
| `TN` | `TN` | `TNc1` | Ultra 10-Year |
| `TWE` | `TWE` | `TWEc1` | 20-Year T-Bond |
| `ZB` | `US` | `USc1` | 30-Year T-Bond |
| `UB` | `UB` | `UBc1` | Ultra 30-Year |

## European bond futures

| Symbol | LSEG root | Front contract | Contract |
|--------|-----------|----------------|----------|
| `FGBL` | `FGBL` | `FGBLc1` | Euro-Bund 10Y |
| `FGBM` | `FGBM` | `FGBMc1` | Euro-Bobl 5Y |
| `FGBS` | `FGBS` | `FGBSc1` | Euro-Schatz 2Y |
| `FGBX` | `FGBX` | `FGBXc1` | Euro-Buxl 30Y |
| `FLG` | `FLG` | `FLGc1` | UK Long Gilt |

## Asian bond futures

| Symbol | LSEG root | Front contract | Contract |
|--------|-----------|----------------|----------|
| `JGB` | `JGB` | `JGBc1` | 10Y JGB |

## Notes

- The code-level source of truth is `timeseries/constants.py`.
- Continuous contracts use `{root}c1`, `{root}c2`, etc.
- If you change any mapping in code, update this file and
  `docs/LSEG_API_REFERENCE.md` in the same PR.
