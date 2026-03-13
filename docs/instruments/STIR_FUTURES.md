## STIR Futures (Short-Term Interest Rate)


### CME Symbol → LSEG RIC Mapping

| CME Symbol | LSEG RIC | Description |
|------------|----------|-------------|
| SR3 | SRA | 3-Month SOFR Futures |
| SR1 | SOFR | 1-Month SOFR Futures |
| ZQ | FF | 30-Day Fed Funds Futures |

### USD STIR

| Instrument | CME | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|-----|----------|--------|-------|----------|-------|
| 3M SOFR | SR3 | `SRAc1` | ✅ | ✅ | ❓ | CME SR3 → LSEG SRA |
| 3M SOFR Chain | - | `0#SRA:` | ✅ | - | - | All contracts |
| 1M SOFR | SR1 | `SOFRc1` | ⛔ | - | - | Access Denied (permissions) |
| 1M SOFR Chain | - | `0#SOFR:` | ✅ | ⛔ | - | Snapshot only, no history |
| Fed Funds | ZQ | `FFc1` | ✅ | ✅ | ❓ | CME ZQ → LSEG FF |
| Fed Funds Chain | - | `0#FF:` | ✅ | - | - | All contracts |

### Internal Stored Symbol Convention

The toolkit stores the Fed Funds continuous contract under the canonical internal
symbol:

- `FF_CONTINUOUS` → LSEG `FFc1`

Stored hourly and daily rows also include:

- `session_date`
- `source_contract`
- `implied_rate`

This is the symbol downstream consumers (for example `fin-kit`) should query.

### STIR Futures Fields

STIR futures use **settlement prices**, not OHLC:

```python
fields=['SETTLE', 'OPEN_INT', 'VOLUME']  # Not OPEN/HIGH/LOW/CLOSE
```

For the implemented Fed Funds storage path:

- **daily**
  - `close = settle`
  - `implied_rate = 100 - settle`
- **hourly**
  - `mid = (bid + ask) / 2`
  - `close = mid`
  - `implied_rate = 100 - mid`

### Continuous Contract Roll Dates

LSEG continuous contracts are **unadjusted** (raw price jumps at rolls):

| Contract | Roll Date | Pattern |
|----------|-----------|---------|
| `FFc1` (Fed Funds) | 1st business day of month | Monthly |
| `SRAc1` (3M SOFR) | 3rd Wednesday of month (IMM date) | Monthly |
| `FEIc1` (Euribor) | 3rd Wednesday of month (IMM date) | Monthly |
| `SONc1` (SONIA) | 3rd Wednesday of month (IMM date) | Monthly |

### Session-Date Rule for Fed Funds Hourly Data

For `FF_CONTINUOUS` hourly rows, contract labeling is based on `session_date`,
not plain UTC calendar date.

Observed LSEG/CME behavior:

- the new monthly contract is already active in the evening session
- practical stored rule:
  - `session_date = (timestamp_utc + 2 hours).date()`

Example:

- `2026-03-01 22:00 UTC` maps to `session_date = 2026-03-02`
- that row is labeled with the March front contract `FFJ26`

**Observed roll jumps (Oct-Dec 2024):**

| Date | FFc1 Change | SRAc1 Change | Event |
|------|-------------|--------------|-------|
| 2024-10-01 | +0.3075 | - | FF roll (1st bus day) |
| 2024-10-16 | - | +0.2225 | SRA roll (3rd Wed) |
| 2024-11-01 | +0.1875 | - | FF roll |
| 2024-11-20 | - | +0.2325 | SRA roll (3rd Wed) |
| 2024-12-02 | +0.1225 | - | FF roll (Dec 1 = Sunday) |
| 2024-12-18 | - | +0.1550 | SRA roll (3rd Wed) |

### Historical Data Availability

| Data Type | Availability | Notes |
|-----------|--------------|-------|
| Continuous (`FFc1`, `SRAc1`) | ✅ 2+ years | Full history, unadjusted |
| Discrete active (`FFH26`) | ✅ | Current/future contracts |
| Discrete expired (`FFH24`) | ⛔ | "Universe not found" error |

### Reconstructing Expired Discrete Contracts

Since LSEG doesn't provide history for expired discrete contracts, reconstruction options:

1. **From continuous + c2 spread**: Use `FFc1` and `FFc2` to back out discrete prices
   - At roll date: `c1` switches to new front, `c2` becomes what was `c1`
   - Track the spread `c2 - c1` to identify contract boundaries

2. **From roll jumps**: Work backwards from known prices
   - Roll jump ≈ price difference between expiring and new contract
   - Cumulative adjustment reconstructs historical discrete levels

3. **Third-party data**: CME, Quandl, or Bloomberg for expired contracts

### EUR STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| 3M Euribor | FEI | `FEIc1` | ✅ | ✅ | ❓ | ICE/Eurex |
| Euribor Chain | - | `0#FEI:` | ✅ | - | - | All contracts |

### GBP STIR

| Instrument | Symbol | LSEG RIC | Status | Daily | Intraday | Notes |
|------------|--------|----------|--------|-------|----------|-------|
| SONIA Future | - | `SONc1` | ✅ | ✅ | ❓ | ICE Europe |

---
