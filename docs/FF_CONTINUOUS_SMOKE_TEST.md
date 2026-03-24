# FF_CONTINUOUS Smoke Test for `fin-kit`

> This is a **downstream integration note**, not the main user guide for the repo.

This document describes a minimal end-to-end smoke test for the stored
Fed Funds continuous contract.

Use this when validating the consumer-side integration in `~/fin-kit`.

---

## Goal

Confirm that downstream code reads `FF_CONTINUOUS` correctly from TimescaleDB and
uses:

- `ts` for ordering
- `session_date` for trading-day logic
- `source_contract` for contract labeling

The key failure mode to guard against is an **off-by-one day** error around the
monthly roll boundary.

---

## Instrument

- Stored symbol: `FF_CONTINUOUS`
- LSEG source: `FFc1`
- Table: `timeseries_ohlcv`

Important columns:

- `ts`
- `session_date`
- `granularity`
- `close`
- `settle`
- `mid`
- `implied_rate`
- `source_contract`

---

## Recommended Smoke-Test Window

Use the observed March 2026 boundary:

- start: `2026-03-01 20:00:00+00`
- end: `2026-03-02 03:00:00+00`

This is a good test because the evening session already reflects the new trading
day / new front contract.

---

## SQL: Boundary Check

```sql
SELECT
    ts,
    session_date,
    granularity,
    close,
    mid,
    implied_rate,
    source_contract
FROM timeseries_ohlcv t
JOIN instruments i ON t.instrument_id = i.id
WHERE i.symbol = 'FF_CONTINUOUS'
  AND t.ts >= TIMESTAMPTZ '2026-03-01 20:00:00+00'
  AND t.ts <= TIMESTAMPTZ '2026-03-02 03:00:00+00'
ORDER BY t.ts, t.granularity;
```

### Expected behavior

For the **hourly** rows:

- rows at `2026-03-01 22:00 UTC` and later should have:
  - `session_date = 2026-03-02`
  - `source_contract = FFH26`

This proves the consumer is not grouping hourly rows by raw UTC date.
It also reflects the corrected Fed Funds front-month convention:
the front contract is the **same settlement month**, not M+1.

---

## SQL: Daily Roll Check

```sql
SELECT
    ts::date AS day,
    session_date,
    source_contract,
    settle,
    implied_rate
FROM timeseries_ohlcv t
JOIN instruments i ON t.instrument_id = i.id
WHERE i.symbol = 'FF_CONTINUOUS'
  AND t.granularity = 'daily'
  AND t.ts::date BETWEEN DATE '2026-02-25' AND DATE '2026-03-05'
ORDER BY t.ts;
```

### Expected behavior

- `2026-02-25` to `2026-02-27` should label to `FFG26`
- `2026-03-02` onward should label to `FFH26`

---

## Consumer Rules for `fin-kit`

Use these conventions in C++:

1. sort by `ts`
2. treat `session_date` as the trading-day key
3. do **not** derive trading day from `ts` in UTC
4. if contract-sensitive logic is needed, use stored `source_contract`

Recommended mapping:

- daily bars:
  - use `close` or `settle`
- hourly bars:
  - use `close` or `mid`
- implied rate:
  - use stored `implied_rate`
  - do not recompute unless you are explicitly checking data integrity

---

## Suggested Assertions in `fin-kit`

At minimum:

1. query returns non-empty rows for the boundary window
2. hourly rows after `2026-03-01 22:00 UTC` have `session_date = 2026-03-02`
3. those same rows have `source_contract = FFH26`
4. daily rows switch from `FFG26` to `FFH26` on `2026-03-02`
5. `implied_rate` is approximately `100 - close`

Example tolerance:

- `abs(implied_rate - (100.0 - close)) < 1e-9`

---

## Nice-to-Have Follow-Up Test

Repeat the same test around another observed hard boundary:

- `2025-09-30 23:00 UTC` → expect `session_date = 2025-10-01`, `source_contract = FFV25`
- `2025-11-02 22:00 UTC` → expect `session_date = 2025-11-03`, `source_contract = FFX25`
- `2026-01-01 22:00 UTC` → expect `session_date = 2026-01-02`, `source_contract = FFF26`

If all of these pass, the consumer-side date handling is very likely correct.
