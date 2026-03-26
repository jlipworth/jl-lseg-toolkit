# Bloomberg Live Validation Runbook

Use this runbook when you have Bloomberg Terminal/Desktop API access and want to:

1. validate the currently supported Bloomberg workflows, and
2. optionally probe the next most likely Bloomberg expansion targets.

Current supported Bloomberg surface:
- `bbg-extract jgb`
- `bbg-extract fx-atm-vol`

Related docs:
- `docs/instruments/BLOOMBERG.md`
- `docs/BLOOMBERG_SCRIPTS.md`
- `docs/BLOOMBERG_FINDINGS.md`

---

## Working directory

Run everything from:

```bash
cd /Users/jlipworth/jl-lseg-toolkit/.worktrees/bloomberg
```

---

## 1. Preflight

Install Bloomberg and test dependencies:

```bash
uv sync --group bloomberg --group test
```

Confirm the Desktop API port is reachable:

```bash
nc -z localhost 8194 && echo ok || echo fail
```

If needed, verify the supported CLI surface:

```bash
uv run bbg-extract --help
uv run bbg-extract jgb --help
uv run bbg-extract fx-atm-vol --help
```

Expected environment:
- Bloomberg Terminal is running and logged in
- Desktop API is available on `localhost:8194`
- `blpapi` is installed through `uv sync --group bloomberg`

---

## 2. Supported Bloomberg validation

These are the merge-relevant checks.

### 2.1 JGB snapshot

```bash
uv run bbg-extract jgb
```

Focused tenor check:

```bash
uv run bbg-extract jgb --tenors 2Y 5Y 10Y 20Y 30Y 40Y
```

What to confirm:
- returns non-empty output
- `tenor` and `ticker` populate
- yields look plausible
- no unexpected `_security_error`

### 2.2 JGB historical

```bash
uv run bbg-extract jgb --historical --start-date 2025-01-01 --tenors 2Y 5Y 10Y 20Y 30Y 40Y
```

What to confirm:
- historical rows return
- `date`, `tenor`, `yield`, `ticker` populate
- no obvious missing-tenor or shape issues

### 2.3 FX ATM vol snapshot

Full supported matrix:

```bash
uv run bbg-extract fx-atm-vol --pairs EURUSD USDJPY GBPUSD AUDUSD USDCHF USDCAD --tenors 1W 1M 2M 3M 6M 9M 1Y 2Y
```

Focused spot check:

```bash
uv run bbg-extract fx-atm-vol --pairs EURUSD USDJPY --tenors 1M 3M 1Y
```

What to confirm:
- returns non-empty output
- `pair`, `tenor`, `ticker` populate
- ATM vol values look plausible
- no unexpected `_security_error`

### 2.4 FX ATM vol historical

```bash
uv run bbg-extract fx-atm-vol --historical --start-date 2025-01-01 --pairs EURUSD USDJPY --tenors 1M 3M
```

What to confirm:
- historical rows return
- `date`, `pair`, `tenor`, `atm_vol`, `ticker` populate
- output shape is stable across requested pairs/tenors

### 2.5 Integration smoke tests

```bash
RUN_BLOOMBERG_INTEGRATION=1 uv run pytest tests/bloomberg/test_integration.py -m integration -v
```

Current smoke tests cover:
- `extract_jgb_snapshot(["10Y"])`
- `extract_fx_atm_vol_snapshot(pairs=["EURUSD"], tenors=["1M"])`

---

## 3. Opportunistic expansion probes

These are worth probing during the same session, but should not block validation of the supported surface.

Priority order:
1. SOFR term rates
2. JGB futures

---

## 4. Probe: SOFR term rates

This is the best candidate for a small Bloomberg expansion because it is additive rather than redundant.

Discovery commands:

```bash
uv run python bloomberg_scripts/search_securities.py "TSFR term sofr"
uv run python bloomberg_scripts/search_instruments.py "TSFR term sofr"
```

Candidate tickers from current docs:
- `TSFR1M Index`
- `TSFR3M Index`
- `TSFR6M Index`
- `TSFR12M Index`
- fallback candidate: `USOSFR1 Curncy`

Suggested fields to verify:
- `PX_LAST`
- `LAST_UPDATE`

Terminal checks if available:
- resolve the exact security in Terminal first
- inspect quote provenance
- verify the Desktop API object matches the terminal-visible object

Promotion bar:
- ticker resolves consistently
- fields populate cleanly
- shape is simple enough to normalize without guesswork

If validated, record findings in:
- `docs/BLOOMBERG_FINDINGS.md`

---

## 5. Probe: JGB futures

This is a plausible target structurally, but lower-value than SOFR term because LSEG already covers JGB futures.

Discovery commands:

```bash
uv run python bloomberg_scripts/search_securities.py "JGB futures OSE"
uv run python bloomberg_scripts/search_instruments.py "JGB futures OSE"
```

Candidate tickers from current docs:
- `JB1 Comdty`
- `JBM1 Comdty`
- `JF1 Comdty`
- specific contracts with `{ROOT}{MONTH}{YEAR} Comdty`

Suggested fields to verify:
- `PX_LAST`
- `PX_OPEN`
- `PX_HIGH`
- `PX_LOW`
- `VOLUME`
- `OPEN_INT`

Promotion bar:
- generic and/or specific-contract pattern is stable
- fields populate consistently
- there is a clear normalized output shape worth supporting

If validated, record findings in:
- `docs/BLOOMBERG_FINDINGS.md`

---

## 6. Do not spend much time here unless the session is going very well

These remain research-heavy and should not be treated as near-term support candidates:
- swaptions
- caps/floors
- FX risk reversals / butterflies

Optional research commands:

```bash
uv run python bloomberg_scripts/test_swaption_tickers.py
uv run python bloomberg_scripts/test_fx_tickers.py
```

These are for discovery only, not merge-readiness.

---

## 7. What to capture during the session

For each supported check or probe, capture:
- exact command run
- whether it returned data
- exact ticker(s) used
- fields that populated
- any `_security_error`
- whether the result looks promotable to supported CLI

Useful format:

```text
### YYYY-MM-DD — <dataset>
- Command:
- Tickers:
- Fields:
- Result:
- Errors:
- Interpretation:
- Next step:
```

Record durable probe findings in:
- `docs/BLOOMBERG_FINDINGS.md`

---

## 8. Success criteria

### Merge-ready minimum

The Bloomberg branch is in good shape for merge if:
- `uv run bbg-extract jgb` works
- `uv run bbg-extract fx-atm-vol` works
- historical variants return expected shapes
- Bloomberg integration smoke tests pass

### Nice-to-have

One of these also validates cleanly:
- SOFR term rates
- JGB futures

### Not required for this pass

These do not need to validate for the branch to be considered successful:
- swaptions
- caps/floors
- FX RR/BF

---

## 9. Troubleshooting

Typical failure classes:

### `blpapi` not installed

Symptom:
- CLI reports a Bloomberg configuration error

Fix:

```bash
uv sync --group bloomberg
```

### Desktop API session cannot start

Symptom:
- CLI reports a Bloomberg runtime error

Checks:

```bash
nc -z localhost 8194
```

Verify:
- Bloomberg Terminal is running
- Bloomberg Terminal is logged in
- Desktop API is reachable on `localhost:8194`

### Empty or partial data

Check:
- wrong ticker
- wrong yellow key/object
- entitlement restriction
- terminal-visible but Desktop API unavailable

For research targets, verify in Terminal first before concluding the API pattern is wrong.
