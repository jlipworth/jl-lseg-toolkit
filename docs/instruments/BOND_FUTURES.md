## Bond Futures


### US Treasury Futures (Complete Curve) - Validated 2026-01-06

**All 8 US Treasury futures validated: 8/8 working**

| Instrument | CME Symbol | LSEG RIC | Status | Daily | Notes |
|------------|------------|----------|--------|-------|-------|
| 2Y T-Note  | ZT | `TUc1` | ✅ | ✅ | 252 rows |
| 3Y T-Note  | Z3N | `YRc1` | ✅ | ✅ | 252 rows |
| 5Y T-Note  | ZF | `FVc1` | ✅ | ✅ | 252 rows |
| 10Y T-Note | ZN | `TYc1` | ✅ | ✅ | 252 rows |
| Ultra 10Y  | TN | `TNc1` | ✅ | ✅ | 252 rows |
| 20Y T-Bond | TWE | `ZPc1` | ✅ | ✅ | 252 rows |
| 30Y T-Bond | ZB | `USc1` | ✅ | ✅ | 252 rows |
| Ultra 30Y  | UB | `AULc1` | ✅ | ✅ | 252 rows |

**Key CME → LSEG Mapping Corrections:**
- 3Y T-Note: CME `Z3N` → LSEG `YRc1` (not `Z3Nc1`)
- 20Y T-Bond: CME `TWE` → LSEG `ZPc1` (not `TWEc1`)
- Ultra 30Y: CME `UB` → LSEG `AULc1` (not `UBc1`)

### European Bond Futures (Validated 2026-01-06)

**11/12 European bond futures validated**

| Instrument     | Symbol | LSEG RIC | Status | Daily | Notes |
|----------------|--------|----------|--------|-------|-------|
| **German (Eurex)** | | | | | |
| Euro-Schatz 2Y | FGBS   | `FGBSc1` | ✅ | ✅ | 254 rows |
| Euro-Bobl 5Y   | FGBM   | `FGBMc1` | ✅ | ✅ | 254 rows |
| Euro-Bund 10Y  | FGBL   | `FGBLc1` | ✅ | ✅ | 254 rows |
| Euro-Buxl 30Y  | FGBX   | `FGBXc1` | ✅ | ✅ | 254 rows |
| **French** | | | | | |
| Euro-OAT 10Y   | FOAT   | `FOATc1` | ✅ | ✅ | 254 rows |
| **Italian** | | | | | |
| Euro-BTP 10Y   | FBTP   | `FBTPc1` | ✅ | ✅ | 254 rows |
| Euro-BTP Short | FBTS   | `FBTSc1` | ✅ | ✅ | 254 rows |
| **Spanish** | | | | | |
| Euro-BONO 10Y  | FBON   | `FBONc1` | ✅ | ✅ | 254 rows |
| **Swiss** | | | | | |
| Swiss Conf     | CONF   | `CONFc1` | ✅ | ✅ | 254 rows |
| **UK (ICE)** | | | | | |
| UK Long Gilt   | FLG    | `FLGc1`  | ✅ | ✅ | 258 rows |
| UK Short Gilt  | FSG    | `FSGc1`  | ❌ | ❌ | Not found |
| UK Medium Gilt | FMG    | `FMGc1`  | ❌ | ❌ | Not found |

### Asian Bond Futures (Validated 2026-01-06)

| Instrument    | Symbol | LSEG RIC | Status | Daily | Intraday | Notes                    |
|---------------|--------|----------|--------|-------|----------|--------------------------|
| JGB 10Y       | JGB    | `JGBc1`  | ✅     | ✅    | ✅       | Osaka Exchange, 246 rows |

### Australian Bond Futures (Validated 2026-01-06)

**Pattern**: `YT{T/C}c1` (not `YTc1` or `XTc1` as documented elsewhere)

| Instrument    | Symbol | LSEG RIC | Status | Daily | Intraday | Notes                    |
|---------------|--------|----------|--------|-------|----------|--------------------------|
| Australia 3Y  | YTT    | `YTTc1`  | ✅     | ✅    | ✅       | ASX, 257 rows           |
| Australia 10Y | YTC    | `YTCc1`  | ✅     | ✅    | ✅       | ASX, 257 rows           |
| Chain 3Y      | -      | `0#YTT:` | ✅     | -     | -        | All contracts           |
| Chain 10Y     | -      | `0#YTC:` | ✅     | -     | -        | All contracts           |

### Canadian Bond Futures (Validated 2026-01-06)

**All 3 Canadian bond futures validated: 3/3 working**

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes            |
|------------|--------|----------|--------|-------|----------|------------------|
| Canada 10Y | CGB    | `CGBc1`  | ✅     | ✅    | ✅       | Montreal Exchange |
| Canada 5Y  | CGF    | `CGFc1`  | ✅     | ✅    | ✅       | Montreal Exchange |
| Canada 2Y  | CGZ    | `CGZc1`  | ✅     | ✅    | ✅       | Montreal Exchange |

---
