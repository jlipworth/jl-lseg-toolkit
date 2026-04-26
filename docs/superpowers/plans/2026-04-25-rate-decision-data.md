# Rate-Decision Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up TimescaleDB-resident interest-rate data (overnight benchmarks + OIS curves + central-bank meeting calendars) for US/EU/UK/CA so a separate repo can run rate-decision probability modeling.

**Architecture:** Five phases in order — (1) probe `EUREST{tenor}=` to learn whether ESTR-OIS is accessible, (2) conditional EUR OIS RIC pattern fix in `constants.py` + `scheduler/universes.py`, (3) three new `<cb>_meetings` tables + per-CB seeder packages mirroring `timeseries/fomc/`, (4) `seed-rate-decision-modeling` CLI subcommand mirroring `seed-ff-strip`, (5) backfill execution + doc updates.

**Tech Stack:** Python 3.x, psycopg (PostgreSQL/TimescaleDB), Pydantic, httpx, pytest, FRED API, BoC Valet API, public CB calendar HTML.

**Spec:** [`docs/superpowers/specs/2026-04-25-rate-decision-data-design.md`](../specs/2026-04-25-rate-decision-data-design.md)

---

## File map

**New files:**
- `dev_scripts/validate_eurest_ois.py` — probe-only script (gitignored)
- `src/lseg_toolkit/timeseries/ecb/{__init__,calendar_scraper,fetcher,models,storage}.py`
- `src/lseg_toolkit/timeseries/boe/{__init__,calendar_scraper,fetcher,models,storage}.py`
- `src/lseg_toolkit/timeseries/boc/{__init__,calendar_scraper,fetcher,models,storage}.py`
- `tests/timeseries/test_ecb.py`, `test_boe.py`, `test_boc.py`, `test_seed_rate_decision_modeling.py`

**Edited files:**
- `src/lseg_toolkit/timeseries/constants.py` — add `EUR_OIS_TENORS`, `get_eur_ois_ric` (conditional)
- `src/lseg_toolkit/timeseries/scheduler/universes.py` — fix `_build_ois_eur` (conditional)
- `src/lseg_toolkit/timeseries/scheduler/default_jobs.py` — add `RATE_DECISION_JOB_SPECS` + `ensure_rate_decision_jobs`
- `src/lseg_toolkit/timeseries/scheduler/cli.py` — add `cmd_seed_rate_decision_modeling`
- `src/lseg_toolkit/timeseries/storage/pg_schema.py` — append three `<cb>_meetings` tables
- `docs/instruments/RATES.md`, `docs/instruments/OVERVIEW.md`, `docs/STORAGE_SCHEMA.md`, `docs/SCHEDULER.md`

---

## Task 1: EUREST validation probe script

**Goal:** Determine whether `EUREST{tenor}=` returns price data, decide which tenors are usable. No DB writes.

**Files:**
- Create: `dev_scripts/validate_eurest_ois.py`

- [ ] **Step 1: Confirm dev_scripts/ is gitignored**

```bash
cd "/home/jlipworth/Refinitiv Projects"
grep -E '^dev_scripts/?$' .gitignore
```

Expected: matches `dev_scripts/`. If not, add it before continuing.

- [ ] **Step 2: Write the probe script**

```python
# dev_scripts/validate_eurest_ois.py
"""
Probe whether EUREST{tenor}= returns daily ESTR-OIS data.

Run:
    uv run python dev_scripts/validate_eurest_ois.py

Prints a one-line summary per tenor and exits 0 regardless. The output
informs whether EUR OIS RIC pattern in constants.py / scheduler/universes.py
should be wired to EUREST{tenor}=.
"""

from __future__ import annotations

from datetime import date, timedelta

import lseg.data as rd

from lseg_toolkit.timeseries.client import LSEGDataClient

TENORS = ["1W", "1M", "2M", "3M", "6M", "9M", "12M", "18M", "2Y"]
SUB_1Y_CORE = {"1W", "1M", "3M", "6M", "12M"}


def main() -> int:
    end = date.today()
    start = end - timedelta(days=30)

    rd.open_session()
    try:
        client = LSEGDataClient()
        results: list[tuple[str, str, int, str]] = []  # (tenor, ric, rows, last_date)

        for tenor in TENORS:
            ric = f"EUREST{tenor}="
            try:
                df = client.get_history(
                    rics=ric,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    interval="daily",
                )
                if df is None or df.empty:
                    results.append((tenor, ric, 0, "-"))
                else:
                    last = df.index.max() if hasattr(df.index, "max") else "?"
                    results.append((tenor, ric, len(df), str(last)[:10]))
            except Exception as e:  # noqa: BLE001
                results.append((tenor, ric, 0, f"ERR: {type(e).__name__}"))
    finally:
        rd.close_session()

    print(f"\n{'tenor':<6} {'ric':<14} {'rows':>5}  last_date")
    print("-" * 45)
    for tenor, ric, rows, last in results:
        print(f"{tenor:<6} {ric:<14} {rows:>5}  {last}")

    sub_1y_hits = {t for t, _, rows, _ in results if t in SUB_1Y_CORE and rows > 0}
    print(f"\nSub-1Y core hits ({len(sub_1y_hits)}/{len(SUB_1Y_CORE)}): {sorted(sub_1y_hits)}")

    if len(sub_1y_hits) >= 4:
        print("Decision: FULL SUCCESS — wire EUREST{tenor}= for EUR OIS.")
    elif len(sub_1y_hits) >= 1:
        print("Decision: PARTIAL — wire only validated tenors; document gaps.")
    else:
        print("Decision: FAIL — leave _build_ois_eur unwired; rely on EURIBOR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the script**

```bash
cd "/home/jlipworth/Refinitiv Projects"
uv run python dev_scripts/validate_eurest_ois.py | tee dev_scripts/eurest_validation_$(date +%F).log
```

Expected: prints a results table + a `Decision:` line. Save the log path — Task 2 reads it.

- [ ] **Step 4: Record outcome in plan tracker**

Edit this file (`docs/superpowers/plans/2026-04-25-rate-decision-data.md`) and append below this checkbox the actual `Decision:` line and the validated tenor list. This drives whether Task 2 runs.

```markdown
**Validation outcome (filled in by Task 1):**
- Decision: <FULL SUCCESS | PARTIAL | FAIL>
- Validated tenors: <e.g., ["1W", "1M", "3M", "6M", "12M"]>
- Log: `dev_scripts/eurest_validation_YYYY-MM-DD.log`
```

- [ ] **Step 5: Commit (skip the script — it's gitignored)**

Only the plan-tracker edit gets committed. The script and log stay local.

```bash
git add docs/superpowers/plans/2026-04-25-rate-decision-data.md
git commit -m "chore(plan): record EUREST validation outcome"
```

---

## Task 2: EUR OIS RIC pattern fix (CONDITIONAL on Task 1 ≠ FAIL)

**Goal:** When EUREST validation succeeded, wire the validated tenors into the EUR OIS scheduler universe.

**Skip this task entirely if Task 1 returned FAIL.**

**Files:**
- Modify: `src/lseg_toolkit/timeseries/constants.py:563-602` (EUR Interest Rate Swaps section — add EUR OIS section after it)
- Modify: `src/lseg_toolkit/timeseries/scheduler/universes.py:306-317`

- [ ] **Step 1: Write the failing test for `get_eur_ois_ric`**

Add to `tests/timeseries/test_constants.py` (create if it doesn't exist):

```python
# tests/timeseries/test_constants.py
def test_get_eur_ois_ric_returns_eurest_pattern():
    from lseg_toolkit.timeseries.constants import get_eur_ois_ric
    assert get_eur_ois_ric("3M") == "EUREST3M="
    assert get_eur_ois_ric("12M") == "EUREST12M="


def test_eur_ois_tenors_includes_validated_set():
    from lseg_toolkit.timeseries.constants import EUR_OIS_TENORS
    # At least one sub-1Y tenor must be validated to justify wiring at all
    assert any(t in EUR_OIS_TENORS for t in ("1W", "1M", "3M", "6M", "12M"))
```

- [ ] **Step 2: Run the test, expect failure**

```bash
uv run pytest tests/timeseries/test_constants.py -v --no-cov
```

Expected: `ImportError: cannot import name 'get_eur_ois_ric'` or `EUR_OIS_TENORS`.

- [ ] **Step 3: Add `EUR_OIS_TENORS` and `get_eur_ois_ric` to constants.py**

Append after the EUR IRS section (after line 602):

```python
# =============================================================================
# EUR OIS — ESTR-Linked (Validated <YYYY-MM-DD from Task 1>)
# =============================================================================

# Pattern: EUREST{tenor}=
# Tenor list comes from Task 1 validation results.
EUR_OIS_TENORS: list[str] = [<paste validated tenors from Task 1>]


def get_eur_ois_ric(tenor: str) -> str:
    """Get EUR OIS (ESTR-linked) RIC for tenor."""
    return f"EUREST{tenor}="
```

If Task 1 returned PARTIAL with only e.g. `{"1M", "3M", "6M"}`, use exactly that list — do not pad it.

- [ ] **Step 4: Remove the obsolete short-end comment**

Edit `src/lseg_toolkit/timeseries/constants.py:569`:

```python
# Pattern: EURIRS{tenor}=
# Note: Short-end (< 1Y) not available - use EURIBOR for short rates
```

becomes:

```python
# Pattern: EURIRS{tenor}=
# Short-end (< 1Y): use EUR_OIS_TENORS / get_eur_ois_ric (ESTR-linked).
```

- [ ] **Step 5: Run the constants tests, expect pass**

```bash
uv run pytest tests/timeseries/test_constants.py -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 6: Update `_build_ois_eur` in universes.py**

Edit `src/lseg_toolkit/timeseries/scheduler/universes.py:306-317`. Find the import block at the top (around line 30-40) and add `EUR_OIS_TENORS` and `get_eur_ois_ric` to the existing import from `lseg_toolkit.timeseries.constants`. Then replace the function body:

```python
def _build_ois_eur() -> list[InstrumentSpec]:
    """Build EUR OIS universe (ESTR-linked, EUREST{tenor}=)."""
    return [
        InstrumentSpec(
            symbol=f"EUR{tenor}OIS",
            ric=get_eur_ois_ric(tenor),
            asset_class=AssetClass.OIS,
            data_shape=DataShape.RATE,
            name=f"EUR OIS {tenor}",
        )
        for tenor in EUR_OIS_TENORS
    ]
```

- [ ] **Step 7: Add a regression test for the universe**

Append to `tests/timeseries/test_scheduler.py`:

```python
def test_build_ois_eur_uses_eurest_pattern():
    from lseg_toolkit.timeseries.scheduler.universes import build_universe
    specs = build_universe("ois_eur")
    assert specs, "ois_eur universe must not be empty"
    for spec in specs:
        assert spec.ric.startswith("EUREST"), f"unexpected RIC: {spec.ric}"
        assert spec.ric.endswith("=")
```

- [ ] **Step 8: Run the universe test**

```bash
uv run pytest tests/timeseries/test_scheduler.py::test_build_ois_eur_uses_eurest_pattern -v --no-cov
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/lseg_toolkit/timeseries/constants.py \
        src/lseg_toolkit/timeseries/scheduler/universes.py \
        tests/timeseries/test_constants.py \
        tests/timeseries/test_scheduler.py
git commit -m "fix(rates): wire EUR OIS to EUREST{tenor}= pattern"
```

---

## Task 3: Schema migration — three CB meeting tables

**Goal:** Add `ecb_meetings`, `boe_meetings`, `boc_meetings` with the same shape as `fomc_meetings`.

**Files:**
- Modify: `src/lseg_toolkit/timeseries/storage/pg_schema.py:471-493` (after `fomc_meetings` block)

- [ ] **Step 1: Write the failing test**

Add to `tests/timeseries/test_storage.py` (or create `test_pg_schema.py` if you prefer; place alongside whatever test asserts `fomc_meetings` exists, or follow nearby pattern):

```python
def test_cb_meeting_tables_in_schema():
    from lseg_toolkit.timeseries.storage import pg_schema
    sql = pg_schema.SCHEMA_SQL  # or whatever the module exports — adjust import
    for table in ("ecb_meetings", "boe_meetings", "boc_meetings"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert f"idx_{table}_date" in sql
        assert f"idx_{table}_decision" in sql
```

If `pg_schema` doesn't expose a single SQL string, adapt the assertion to whatever string-constant it does export (e.g., grep for the existing `fomc_meetings` assertion's pattern).

- [ ] **Step 2: Run the test, expect failure**

```bash
uv run pytest tests/timeseries/test_storage.py::test_cb_meeting_tables_in_schema -v --no-cov
```

Expected: FAIL because tables don't exist in the SQL string.

- [ ] **Step 3: Add the three tables to pg_schema.py**

Insert immediately after the `fomc_meetings` `CREATE TABLE` and its two indexes (currently around line 491-492). Use the exact same column shape; only the table/index names change:

```sql
CREATE TABLE IF NOT EXISTS ecb_meetings (
    id SERIAL PRIMARY KEY,
    meeting_date DATE NOT NULL UNIQUE,
    meeting_start_date DATE,
    rate_upper DOUBLE PRECISION,
    rate_lower DOUBLE PRECISION,
    rate_change_bps INTEGER,
    decision TEXT,
    dissent_count INTEGER DEFAULT 0,
    vote_for INTEGER,
    vote_against INTEGER,
    statement_url TEXT,
    minutes_url TEXT,
    is_scheduled BOOLEAN DEFAULT TRUE,
    has_sep BOOLEAN DEFAULT FALSE,
    has_presser BOOLEAN DEFAULT FALSE,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ecb_meetings_date ON ecb_meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_ecb_meetings_decision ON ecb_meetings(decision);

CREATE TABLE IF NOT EXISTS boe_meetings (
    id SERIAL PRIMARY KEY,
    meeting_date DATE NOT NULL UNIQUE,
    meeting_start_date DATE,
    rate_upper DOUBLE PRECISION,
    rate_lower DOUBLE PRECISION,
    rate_change_bps INTEGER,
    decision TEXT,
    dissent_count INTEGER DEFAULT 0,
    vote_for INTEGER,
    vote_against INTEGER,
    statement_url TEXT,
    minutes_url TEXT,
    is_scheduled BOOLEAN DEFAULT TRUE,
    has_sep BOOLEAN DEFAULT FALSE,
    has_presser BOOLEAN DEFAULT FALSE,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_boe_meetings_date ON boe_meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_boe_meetings_decision ON boe_meetings(decision);

CREATE TABLE IF NOT EXISTS boc_meetings (
    id SERIAL PRIMARY KEY,
    meeting_date DATE NOT NULL UNIQUE,
    meeting_start_date DATE,
    rate_upper DOUBLE PRECISION,
    rate_lower DOUBLE PRECISION,
    rate_change_bps INTEGER,
    decision TEXT,
    dissent_count INTEGER DEFAULT 0,
    vote_for INTEGER,
    vote_against INTEGER,
    statement_url TEXT,
    minutes_url TEXT,
    is_scheduled BOOLEAN DEFAULT TRUE,
    has_sep BOOLEAN DEFAULT FALSE,
    has_presser BOOLEAN DEFAULT FALSE,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_boc_meetings_date ON boc_meetings(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_boc_meetings_decision ON boc_meetings(decision);
```

- [ ] **Step 4: Re-run the test, expect pass**

```bash
uv run pytest tests/timeseries/test_storage.py::test_cb_meeting_tables_in_schema -v --no-cov
```

Expected: PASS.

- [ ] **Step 5: Apply schema to live DB**

Use the timescaledb-access skill workflow first (env normalization, read-only ping). Then:

```bash
uv run python -c "
from lseg_toolkit.timeseries.storage import init_db
init_db()
"
```

Then verify:

```bash
psql -c "\\dt ecb_meetings" -c "\\dt boe_meetings" -c "\\dt boc_meetings"
```

Expected: each command lists the table.

- [ ] **Step 6: Commit**

```bash
git add src/lseg_toolkit/timeseries/storage/pg_schema.py tests/timeseries/test_storage.py
git commit -m "feat(storage): add ecb/boe/boc meeting tables mirroring fomc_meetings"
```

---

## Task 4: ECB module (models, scraper, fetcher, storage, init, tests)

**Goal:** Mirror `timeseries/fomc/` structure for the ECB. Source meetings from the ECB calendar page; rates from FRED `ECBDFR` (Deposit Facility Rate).

**Files:**
- Create: `src/lseg_toolkit/timeseries/ecb/__init__.py`
- Create: `src/lseg_toolkit/timeseries/ecb/models.py`
- Create: `src/lseg_toolkit/timeseries/ecb/calendar_scraper.py`
- Create: `src/lseg_toolkit/timeseries/ecb/fetcher.py`
- Create: `src/lseg_toolkit/timeseries/ecb/storage.py`
- Create: `tests/timeseries/test_ecb.py`

- [ ] **Step 1: Write `models.py`**

```python
# src/lseg_toolkit/timeseries/ecb/models.py
"""Pydantic models for ECB Governing Council monetary-policy meetings."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class ECBMeeting(BaseModel):
    """ECB Governing Council monetary-policy meeting record.

    Both rate_upper and rate_lower store the Deposit Facility Rate (DFR);
    DFR is what ESTR tracks, so it is the relevant policy rate for OIS
    decomposition. MRO and marginal-lending rates are intentionally omitted.
    """

    meeting_date: date = Field(..., description="Decision/announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Deposit Facility Rate (DFR)")
    rate_lower: float | None = Field(None, description="Deposit Facility Rate (DFR)")
    rate_change_bps: int | None = None
    decision: RateDecision | None = None
    dissent_count: int = 0
    vote_for: int | None = None
    vote_against: int | None = None
    statement_url: str | None = None
    minutes_url: str | None = None
    is_scheduled: bool = True
    has_sep: bool = False  # ECB SPF — we leave False unless seeder learns otherwise
    has_presser: bool = True  # ECB has post-meeting press conference by default
    source: str = "ecb_calendar"
```

- [ ] **Step 2: Write `calendar_scraper.py`**

Approach: ECB publishes monetary-policy meeting dates at `https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html`. This page lists Governing Council monetary-policy meetings — strict subset of all GC meetings.

```python
# src/lseg_toolkit/timeseries/ecb/calendar_scraper.py
"""Scraper for ECB Governing Council monetary-policy meeting calendar."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.ecb.models import ECBMeeting

ECB_CALENDAR_URL = (
    "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"
)

# The page lists rows like "Wednesday, 11 March 2026". We parse all such rows
# and keep those on/after `today`.
_ROW_RE = re.compile(
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s*,?\s*"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_ecb_calendar_html(url: str = ECB_CALENDAR_URL) -> str:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_future_ecb_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[ECBMeeting]:
    """Parse the ECB monetary-policy calendar page into ECBMeeting objects."""
    if today is None:
        today = date.today()

    meetings: list[ECBMeeting] = []
    seen: set[date] = set()
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(
            ECBMeeting(
                meeting_date=d,
                source="ecb_calendar",
            )
        )
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_ecb_meetings(
    *,
    today: date | None = None,
    url: str = ECB_CALENDAR_URL,
) -> list[ECBMeeting]:
    return parse_future_ecb_meetings(fetch_ecb_calendar_html(url), today=today)
```

> **Verify at implementation time:** the actual HTML structure of the ECB page may differ from the regex above. If the regex returns 0 matches against the live page, inspect the rendered HTML and tighten the regex to whatever structural pattern the page uses (likely a `<dt>`/`<dd>` or `<time datetime="...">` block). Adjust and re-run the scraper test.

- [ ] **Step 3: Write `fetcher.py`**

```python
# src/lseg_toolkit/timeseries/ecb/fetcher.py
"""ECB meeting/rate fetcher — combines calendar dates and FRED ECBDFR."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

import httpx

from lseg_toolkit.timeseries.ecb.calendar_scraper import fetch_future_ecb_meetings
from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_DFR_SERIES = "ECBDFR"  # ECB Deposit Facility Rate

logger = logging.getLogger(__name__)


def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError(
            "FRED_API_KEY environment variable not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


def fetch_dfr_history(
    api_key: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    """Fetch Deposit Facility Rate history from FRED (series ECBDFR)."""
    if api_key is None:
        api_key = get_fred_api_key()

    params: dict = {
        "series_id": FRED_DFR_SERIES,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "asc",
    }
    if start_date:
        params["observation_start"] = start_date.isoformat()
    if end_date:
        params["observation_end"] = end_date.isoformat()

    resp = httpx.get(
        f"{FRED_BASE_URL}/series/observations", params=params, timeout=30.0
    )
    resp.raise_for_status()
    data = resp.json()

    return {
        datetime.strptime(obs["date"], "%Y-%m-%d").date(): float(obs["value"])
        for obs in data.get("observations", [])
        if obs.get("value") and obs["value"] != "."
    }


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    """Return the first rate on or after `target` (inclusive)."""
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_ecb_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[ECBMeeting]:
    """Build ECBMeeting records from announcement dates + DFR history."""
    meetings: list[ECBMeeting] = []
    prev_rate: float | None = None

    for meeting_date in sorted(dates):
        rate: float | None = None
        if rate_history:
            rate = _rate_on_or_after(rate_history, meeting_date)

        change_bps: int | None = None
        decision: RateDecision | None = None
        if rate is not None and prev_rate is not None:
            diff = rate - prev_rate
            change_bps = int(round(diff * 100))
            if change_bps > 0:
                decision = RateDecision.HIKE
            elif change_bps < 0:
                decision = RateDecision.CUT
            else:
                decision = RateDecision.HOLD

        meetings.append(
            ECBMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="fred+ecb_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate

    return meetings


def fetch_ecb_meetings(
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> list[ECBMeeting]:
    """Fetch ECB monetary-policy meetings: future from calendar, history from DFR."""
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_dfr_history(api_key)
    except ValueError:
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "FRED API key unavailable; syncing ECB meetings without rate history"
        )

    historical_dates: list[date] = (
        sorted(rate_history.keys()) if rate_history else []
    )
    # Treat each FRED-observed rate-change date as a meeting date.
    # ECB rates only change on Governing Council monetary-policy days, so this
    # is a reasonable historical proxy when no calendar archive is available.
    change_dates: list[date] = []
    if rate_history:
        prev: float | None = None
        for d in historical_dates:
            if prev is None or rate_history[d] != prev:
                change_dates.append(d)
                prev = rate_history[d]

    historical = build_ecb_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_ecb_meetings()
    except Exception:
        logger.warning(
            "Failed to fetch future scheduled ECB meetings", exc_info=True
        )
        future = []

    combined: dict[date, ECBMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)

    return [combined[d] for d in sorted(combined)]
```

- [ ] **Step 4: Write `storage.py`**

```python
# src/lseg_toolkit/timeseries/ecb/storage.py
"""ECB data storage operations for PostgreSQL/TimescaleDB."""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.ecb.models import ECBMeeting

logger = logging.getLogger(__name__)


def upsert_ecb_meeting(conn: psycopg.Connection, meeting: ECBMeeting) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ecb_meetings (
                meeting_date, meeting_start_date, rate_upper, rate_lower,
                rate_change_bps, decision, dissent_count, vote_for, vote_against,
                statement_url, minutes_url, is_scheduled, has_sep, has_presser, source,
                updated_at
            ) VALUES (
                %(meeting_date)s, %(meeting_start_date)s, %(rate_upper)s, %(rate_lower)s,
                %(rate_change_bps)s, %(decision)s, %(dissent_count)s, %(vote_for)s, %(vote_against)s,
                %(statement_url)s, %(minutes_url)s, %(is_scheduled)s, %(has_sep)s, %(has_presser)s,
                %(source)s, NOW()
            )
            ON CONFLICT (meeting_date) DO UPDATE SET
                meeting_start_date = EXCLUDED.meeting_start_date,
                rate_upper = EXCLUDED.rate_upper,
                rate_lower = EXCLUDED.rate_lower,
                rate_change_bps = EXCLUDED.rate_change_bps,
                decision = EXCLUDED.decision,
                dissent_count = EXCLUDED.dissent_count,
                vote_for = EXCLUDED.vote_for,
                vote_against = EXCLUDED.vote_against,
                statement_url = EXCLUDED.statement_url,
                minutes_url = EXCLUDED.minutes_url,
                is_scheduled = EXCLUDED.is_scheduled,
                has_sep = EXCLUDED.has_sep,
                has_presser = EXCLUDED.has_presser,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id
            """,
            {
                "meeting_date": meeting.meeting_date,
                "meeting_start_date": meeting.meeting_start_date,
                "rate_upper": meeting.rate_upper,
                "rate_lower": meeting.rate_lower,
                "rate_change_bps": meeting.rate_change_bps,
                "decision": meeting.decision.value if meeting.decision else None,
                "dissent_count": meeting.dissent_count,
                "vote_for": meeting.vote_for,
                "vote_against": meeting.vote_against,
                "statement_url": meeting.statement_url,
                "minutes_url": meeting.minutes_url,
                "is_scheduled": meeting.is_scheduled,
                "has_sep": meeting.has_sep,
                "has_presser": meeting.has_presser,
                "source": meeting.source,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_ecb_meetings(
    conn: psycopg.Connection, meetings: list[ECBMeeting]
) -> int:
    count = 0
    for m in meetings:
        upsert_ecb_meeting(conn, m)
        count += 1
    conn.commit()
    return count


def sync_ecb_meetings(
    conn: psycopg.Connection,
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> int:
    """Fetch ECB meetings and upsert them into PostgreSQL."""
    from lseg_toolkit.timeseries.ecb.fetcher import fetch_ecb_meetings

    meetings = fetch_ecb_meetings(
        api_key=api_key,
        allow_missing_rate_history=allow_missing_rate_history,
    )
    count = upsert_ecb_meetings(conn, meetings)
    logger.info("Upserted %d ECB meetings", count)
    return count


def get_ecb_meetings(
    conn: psycopg.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    conditions = []
    params: dict = {}
    if start_date:
        conditions.append("meeting_date >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("meeting_date <= %(end_date)s")
        params["end_date"] = end_date
    where = " AND ".join(conditions) if conditions else "TRUE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM ecb_meetings WHERE {where} ORDER BY meeting_date DESC",
            params,
        )
        return list(cur.fetchall())


def get_meeting_count(conn: psycopg.Connection) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM ecb_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0
```

- [ ] **Step 5: Write `__init__.py`**

```python
# src/lseg_toolkit/timeseries/ecb/__init__.py
"""ECB (European Central Bank) monetary-policy meeting data module."""

from lseg_toolkit.timeseries.ecb.calendar_scraper import (
    ECB_CALENDAR_URL,
    fetch_future_ecb_meetings,
    parse_future_ecb_meetings,
)
from lseg_toolkit.timeseries.ecb.fetcher import (
    fetch_dfr_history,
    fetch_ecb_meetings,
)
from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision
from lseg_toolkit.timeseries.ecb.storage import (
    get_ecb_meetings,
    get_meeting_count,
    sync_ecb_meetings,
    upsert_ecb_meeting,
    upsert_ecb_meetings,
)

__all__ = [
    "ECB_CALENDAR_URL",
    "ECBMeeting",
    "RateDecision",
    "fetch_dfr_history",
    "fetch_ecb_meetings",
    "fetch_future_ecb_meetings",
    "get_ecb_meetings",
    "get_meeting_count",
    "parse_future_ecb_meetings",
    "sync_ecb_meetings",
    "upsert_ecb_meeting",
    "upsert_ecb_meetings",
]
```

- [ ] **Step 6: Write tests in `tests/timeseries/test_ecb.py`**

```python
"""Tests for the ECB module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision

# Synthetic snippet matching the regex shape, not the live page exactly.
ECB_HTML = """
<html><body>
<dt><time datetime="2026-03-11">Wednesday, 11 March 2026</time></dt>
<dt><time datetime="2026-04-29">Wednesday, 29 April 2026</time></dt>
<dt><time datetime="2026-06-10">Wednesday, 10 June 2026</time></dt>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.ecb.calendar_scraper import (
            parse_future_ecb_meetings,
        )

        meetings = parse_future_ecb_meetings(ECB_HTML, today=date(2026, 4, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 4, 29),
            date(2026, 6, 10),
        ]

    def test_parse_dedupes_repeats(self):
        from lseg_toolkit.timeseries.ecb.calendar_scraper import (
            parse_future_ecb_meetings,
        )

        repeated = ECB_HTML + ECB_HTML
        meetings = parse_future_ecb_meetings(repeated, today=date(2026, 1, 1))
        dates = [m.meeting_date for m in meetings]
        assert len(dates) == len(set(dates))


class TestFetcherBuilders:
    def test_build_assigns_decision_from_rate_change(self):
        from lseg_toolkit.timeseries.ecb.fetcher import (
            build_ecb_meetings_from_dates,
        )

        dates = [date(2026, 1, 30), date(2026, 3, 13), date(2026, 4, 24)]
        rate_history = {
            date(2026, 1, 30): 4.0,
            date(2026, 3, 13): 3.75,
            date(2026, 4, 24): 3.75,
        }
        meetings = build_ecb_meetings_from_dates(dates, rate_history)

        assert meetings[0].decision is None  # no prev_rate
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25
        assert meetings[2].decision == RateDecision.HOLD


class TestFetchECBMeetings:
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_future_ecb_meetings")
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_dfr_history")
    def test_merges_future_with_historical(self, mock_dfr, mock_future):
        from lseg_toolkit.timeseries.ecb.fetcher import fetch_ecb_meetings

        mock_dfr.return_value = {date(2025, 12, 1): 3.25}
        mock_future.return_value = [
            ECBMeeting(meeting_date=date(2026, 3, 11), source="ecb_calendar")
        ]

        meetings = fetch_ecb_meetings()
        dates = [m.meeting_date for m in meetings]
        assert date(2025, 12, 1) in dates
        assert date(2026, 3, 11) in dates

    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_future_ecb_meetings")
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_dfr_history")
    def test_falls_back_when_fred_missing(self, mock_dfr, mock_future):
        from lseg_toolkit.timeseries.ecb.fetcher import fetch_ecb_meetings

        mock_dfr.side_effect = ValueError("FRED_API_KEY environment variable not set")
        mock_future.return_value = [
            ECBMeeting(meeting_date=date(2026, 3, 11), source="ecb_calendar")
        ]

        meetings = fetch_ecb_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
```

- [ ] **Step 7: Run the ECB tests, expect pass**

```bash
uv run pytest tests/timeseries/test_ecb.py -v --no-cov
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add src/lseg_toolkit/timeseries/ecb/ tests/timeseries/test_ecb.py
git commit -m "feat(ecb): add ECB Governing Council meeting data module"
```

---

## Task 5: BoE module

**Goal:** Mirror Task 4 structure for the Bank of England MPC. Source from BoE MPC calendar page; rates from FRED `IUDSOIA` (Bank Rate per FRED) — verify the series ID at runtime; if it turns out `IUDSOIA` represents SONIA rather than Bank Rate, fall back to `BOEBSI`/`BOERUKA` (whichever exists) or scrape `bankofengland.co.uk`'s rate-history page.

**Files:**
- Create: `src/lseg_toolkit/timeseries/boe/{__init__,models,calendar_scraper,fetcher,storage}.py`
- Create: `tests/timeseries/test_boe.py`

- [ ] **Step 1: Verify FRED Bank Rate series ID**

```bash
curl -sS "https://api.stlouisfed.org/fred/series?series_id=IUDSOIA&api_key=${FRED_API_KEY}&file_type=json" | head -50
```

Read the `title` field. If it says "SONIA" or anything other than "Bank Rate", search FRED for "Bank of England Bank Rate" and pick the official series. Record the chosen series ID — it will go into `BOE_BANK_RATE_SERIES` in `fetcher.py`.

- [ ] **Step 2: Write `models.py`**

Same shape as ECB but rename `ECBMeeting` → `BoEMeeting`, default `source="boe_calendar"`, `has_presser=False` (BoE has Monetary Policy Reports four times/year — not every meeting has a press conference; default False, the seeder can flip it for QMR-coincident meetings).

```python
# src/lseg_toolkit/timeseries/boe/models.py
"""Pydantic models for Bank of England MPC meetings."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class BoEMeeting(BaseModel):
    """Bank of England MPC monetary-policy meeting record.

    rate_upper == rate_lower == Bank Rate (single policy rate).
    """

    meeting_date: date = Field(..., description="MPC announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Bank Rate")
    rate_lower: float | None = Field(None, description="Bank Rate")
    rate_change_bps: int | None = None
    decision: RateDecision | None = None
    dissent_count: int = 0
    vote_for: int | None = None
    vote_against: int | None = None
    statement_url: str | None = None
    minutes_url: str | None = None
    is_scheduled: bool = True
    has_sep: bool = False  # BoE has MPR (Monetary Policy Report) — flip True per QMR
    has_presser: bool = False
    source: str = "boe_calendar"
```

- [ ] **Step 3: Write `calendar_scraper.py`**

```python
# src/lseg_toolkit/timeseries/boe/calendar_scraper.py
"""Scraper for the Bank of England MPC meeting calendar."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boe.models import BoEMeeting

BOE_CALENDAR_URL = (
    "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"
)

_ROW_RE = re.compile(
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_boe_calendar_html(url: str = BOE_CALENDAR_URL) -> str:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_future_boe_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[BoEMeeting]:
    if today is None:
        today = date.today()
    seen: set[date] = set()
    meetings: list[BoEMeeting] = []
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(BoEMeeting(meeting_date=d, source="boe_calendar"))
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_boe_meetings(
    *, today: date | None = None, url: str = BOE_CALENDAR_URL
) -> list[BoEMeeting]:
    return parse_future_boe_meetings(fetch_boe_calendar_html(url), today=today)
```

> **Verify at implementation time:** the BoE upcoming-MPC-dates URL above is best-current-knowledge. If 404 or returns no matching dates, search bankofengland.co.uk for the live URL of the published MPC schedule and update `BOE_CALENDAR_URL`.

- [ ] **Step 4: Write `fetcher.py`**

Identical structure to ECB fetcher, with:
- `FRED_BANK_RATE_SERIES = "<verified series ID from Step 1>"`
- `fetch_bank_rate_history` instead of `fetch_dfr_history`
- `build_boe_meetings_from_dates` instead of `build_ecb_meetings_from_dates`
- `fetch_boe_meetings` orchestrator

Copy the ECB pattern verbatim, swap names, swap series ID. Reproduced here in full to spare the engineer cross-referencing:

```python
# src/lseg_toolkit/timeseries/boe/fetcher.py
"""BoE meeting/rate fetcher — combines calendar dates and FRED Bank Rate."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

import httpx

from lseg_toolkit.timeseries.boe.calendar_scraper import fetch_future_boe_meetings
from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_BANK_RATE_SERIES = "<paste verified series ID from Task 5 Step 1>"

logger = logging.getLogger(__name__)


def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError(
            "FRED_API_KEY environment variable not set."
        )
    return key


def fetch_bank_rate_history(
    api_key: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    if api_key is None:
        api_key = get_fred_api_key()
    params: dict = {
        "series_id": FRED_BANK_RATE_SERIES,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "asc",
    }
    if start_date:
        params["observation_start"] = start_date.isoformat()
    if end_date:
        params["observation_end"] = end_date.isoformat()
    resp = httpx.get(
        f"{FRED_BASE_URL}/series/observations", params=params, timeout=30.0
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        datetime.strptime(obs["date"], "%Y-%m-%d").date(): float(obs["value"])
        for obs in data.get("observations", [])
        if obs.get("value") and obs["value"] != "."
    }


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_boe_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[BoEMeeting]:
    meetings: list[BoEMeeting] = []
    prev_rate: float | None = None
    for meeting_date in sorted(dates):
        rate: float | None = None
        if rate_history:
            rate = _rate_on_or_after(rate_history, meeting_date)
        change_bps: int | None = None
        decision: RateDecision | None = None
        if rate is not None and prev_rate is not None:
            diff = rate - prev_rate
            change_bps = int(round(diff * 100))
            if change_bps > 0:
                decision = RateDecision.HIKE
            elif change_bps < 0:
                decision = RateDecision.CUT
            else:
                decision = RateDecision.HOLD
        meetings.append(
            BoEMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="fred+boe_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate
    return meetings


def fetch_boe_meetings(
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> list[BoEMeeting]:
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_bank_rate_history(api_key)
    except ValueError:
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "FRED API key unavailable; syncing BoE meetings without rate history"
        )

    change_dates: list[date] = []
    if rate_history:
        prev: float | None = None
        for d in sorted(rate_history):
            if prev is None or rate_history[d] != prev:
                change_dates.append(d)
                prev = rate_history[d]

    historical = build_boe_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_boe_meetings()
    except Exception:
        logger.warning("Failed to fetch future scheduled BoE meetings", exc_info=True)
        future = []

    combined: dict[date, BoEMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)
    return [combined[d] for d in sorted(combined)]
```

- [ ] **Step 5: Write `storage.py`**

Identical to ECB `storage.py`, but every `ecb_meetings` → `boe_meetings`, every `ECBMeeting` → `BoEMeeting`, every `ecb` import → `boe`. Reproduced in full:

```python
# src/lseg_toolkit/timeseries/boe/storage.py
"""BoE data storage operations for PostgreSQL/TimescaleDB."""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.boe.models import BoEMeeting

logger = logging.getLogger(__name__)


def upsert_boe_meeting(conn: psycopg.Connection, meeting: BoEMeeting) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO boe_meetings (
                meeting_date, meeting_start_date, rate_upper, rate_lower,
                rate_change_bps, decision, dissent_count, vote_for, vote_against,
                statement_url, minutes_url, is_scheduled, has_sep, has_presser, source,
                updated_at
            ) VALUES (
                %(meeting_date)s, %(meeting_start_date)s, %(rate_upper)s, %(rate_lower)s,
                %(rate_change_bps)s, %(decision)s, %(dissent_count)s, %(vote_for)s, %(vote_against)s,
                %(statement_url)s, %(minutes_url)s, %(is_scheduled)s, %(has_sep)s, %(has_presser)s,
                %(source)s, NOW()
            )
            ON CONFLICT (meeting_date) DO UPDATE SET
                meeting_start_date = EXCLUDED.meeting_start_date,
                rate_upper = EXCLUDED.rate_upper,
                rate_lower = EXCLUDED.rate_lower,
                rate_change_bps = EXCLUDED.rate_change_bps,
                decision = EXCLUDED.decision,
                dissent_count = EXCLUDED.dissent_count,
                vote_for = EXCLUDED.vote_for,
                vote_against = EXCLUDED.vote_against,
                statement_url = EXCLUDED.statement_url,
                minutes_url = EXCLUDED.minutes_url,
                is_scheduled = EXCLUDED.is_scheduled,
                has_sep = EXCLUDED.has_sep,
                has_presser = EXCLUDED.has_presser,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id
            """,
            {
                "meeting_date": meeting.meeting_date,
                "meeting_start_date": meeting.meeting_start_date,
                "rate_upper": meeting.rate_upper,
                "rate_lower": meeting.rate_lower,
                "rate_change_bps": meeting.rate_change_bps,
                "decision": meeting.decision.value if meeting.decision else None,
                "dissent_count": meeting.dissent_count,
                "vote_for": meeting.vote_for,
                "vote_against": meeting.vote_against,
                "statement_url": meeting.statement_url,
                "minutes_url": meeting.minutes_url,
                "is_scheduled": meeting.is_scheduled,
                "has_sep": meeting.has_sep,
                "has_presser": meeting.has_presser,
                "source": meeting.source,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_boe_meetings(
    conn: psycopg.Connection, meetings: list[BoEMeeting]
) -> int:
    count = 0
    for m in meetings:
        upsert_boe_meeting(conn, m)
        count += 1
    conn.commit()
    return count


def sync_boe_meetings(
    conn: psycopg.Connection,
    api_key: str | None = None,
    allow_missing_rate_history: bool = True,
) -> int:
    from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings
    meetings = fetch_boe_meetings(
        api_key=api_key, allow_missing_rate_history=allow_missing_rate_history
    )
    count = upsert_boe_meetings(conn, meetings)
    logger.info("Upserted %d BoE meetings", count)
    return count


def get_boe_meetings(
    conn: psycopg.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    conditions = []
    params: dict = {}
    if start_date:
        conditions.append("meeting_date >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("meeting_date <= %(end_date)s")
        params["end_date"] = end_date
    where = " AND ".join(conditions) if conditions else "TRUE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM boe_meetings WHERE {where} ORDER BY meeting_date DESC",
            params,
        )
        return list(cur.fetchall())


def get_meeting_count(conn: psycopg.Connection) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM boe_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0
```

- [ ] **Step 6: Write `__init__.py`**

```python
# src/lseg_toolkit/timeseries/boe/__init__.py
"""BoE (Bank of England) MPC meeting data module."""

from lseg_toolkit.timeseries.boe.calendar_scraper import (
    BOE_CALENDAR_URL,
    fetch_future_boe_meetings,
    parse_future_boe_meetings,
)
from lseg_toolkit.timeseries.boe.fetcher import (
    fetch_bank_rate_history,
    fetch_boe_meetings,
)
from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision
from lseg_toolkit.timeseries.boe.storage import (
    get_boe_meetings,
    get_meeting_count,
    sync_boe_meetings,
    upsert_boe_meeting,
    upsert_boe_meetings,
)

__all__ = [
    "BOE_CALENDAR_URL",
    "BoEMeeting",
    "RateDecision",
    "fetch_bank_rate_history",
    "fetch_boe_meetings",
    "fetch_future_boe_meetings",
    "get_boe_meetings",
    "get_meeting_count",
    "parse_future_boe_meetings",
    "sync_boe_meetings",
    "upsert_boe_meeting",
    "upsert_boe_meetings",
]
```

- [ ] **Step 7: Write tests in `tests/timeseries/test_boe.py`**

Pattern matches ECB tests but with synthetic BoE HTML and BoE-specific assertions. Engineer should clone the ECB test file structure, swap names, and adjust the synthetic HTML to look like a BoE MPC schedule snippet.

```python
"""Tests for the BoE module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision

BOE_HTML = """
<html><body>
<ul>
  <li>6 February 2026</li>
  <li>20 March 2026</li>
  <li>8 May 2026</li>
</ul>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.boe.calendar_scraper import (
            parse_future_boe_meetings,
        )
        meetings = parse_future_boe_meetings(BOE_HTML, today=date(2026, 3, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 3, 20),
            date(2026, 5, 8),
        ]


class TestFetcherBuilders:
    def test_build_assigns_decision_from_rate_change(self):
        from lseg_toolkit.timeseries.boe.fetcher import build_boe_meetings_from_dates
        dates = [date(2026, 2, 6), date(2026, 3, 20)]
        rate_history = {date(2026, 2, 6): 4.5, date(2026, 3, 20): 4.25}
        meetings = build_boe_meetings_from_dates(dates, rate_history)
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25


class TestFetchBoEMeetings:
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_future_boe_meetings")
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_bank_rate_history")
    def test_falls_back_when_fred_missing(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings
        mock_rate.side_effect = ValueError("FRED_API_KEY environment variable not set")
        mock_future.return_value = [
            BoEMeeting(meeting_date=date(2026, 3, 20), source="boe_calendar")
        ]
        meetings = fetch_boe_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
```

- [ ] **Step 8: Run BoE tests**

```bash
uv run pytest tests/timeseries/test_boe.py -v --no-cov
```

Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/lseg_toolkit/timeseries/boe/ tests/timeseries/test_boe.py
git commit -m "feat(boe): add Bank of England MPC meeting data module"
```

---

## Task 6: BoC module

**Goal:** Same shape as Tasks 4 and 5 for the Bank of Canada. Calendar from BoC FAD page; rates from BoC Valet API series `V39079` (Target Overnight Rate). Verify the series ID at runtime — Valet's catalog is at `https://www.bankofcanada.ca/valet/lists/series/json`; if `V39079` doesn't exist, search for "Target overnight rate" in the catalog and use whatever ID is current.

**Files:**
- Create: `src/lseg_toolkit/timeseries/boc/{__init__,models,calendar_scraper,fetcher,storage}.py`
- Create: `tests/timeseries/test_boc.py`

- [ ] **Step 1: Verify BoC Valet series ID for Target Overnight Rate**

```bash
curl -sS "https://www.bankofcanada.ca/valet/observations/V39079/json?recent=1" | head -50
```

If 404 or wrong series, query the catalog:

```bash
curl -sS "https://www.bankofcanada.ca/valet/lists/series/json" | jq '.series | to_entries[] | select(.value.label | test("(?i)target.*overnight"))'
```

Record the chosen series ID — it will go into `BOC_TARGET_RATE_SERIES` in `fetcher.py`.

- [ ] **Step 2: Write `models.py`**

```python
# src/lseg_toolkit/timeseries/boc/models.py
"""Pydantic models for Bank of Canada rate-decision meetings (FAD)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RateDecision(StrEnum):
    CUT = "cut"
    HIKE = "hike"
    HOLD = "hold"


class BoCMeeting(BaseModel):
    """Bank of Canada Fixed Announcement Date (FAD) record.

    rate_upper == rate_lower == Target Overnight Rate (single policy rate).
    """

    meeting_date: date = Field(..., description="FAD announcement date")
    meeting_start_date: date | None = None
    rate_upper: float | None = Field(None, description="Target Overnight Rate")
    rate_lower: float | None = Field(None, description="Target Overnight Rate")
    rate_change_bps: int | None = None
    decision: RateDecision | None = None
    dissent_count: int = 0  # BoC does not publish individual votes
    vote_for: int | None = None
    vote_against: int | None = None
    statement_url: str | None = None
    minutes_url: str | None = None
    is_scheduled: bool = True  # set False for inter-meeting cuts (e.g. Mar 2020)
    has_sep: bool = False  # BoC publishes Monetary Policy Report 4x/year — flip True for MPR-coincident
    has_presser: bool = False  # MPR-coincident FADs have a press conference
    source: str = "boc_calendar"
```

- [ ] **Step 3: Write `calendar_scraper.py`**

```python
# src/lseg_toolkit/timeseries/boc/calendar_scraper.py
"""Scraper for Bank of Canada Fixed Announcement Date schedule."""

from __future__ import annotations

import re
from datetime import date

import httpx

from lseg_toolkit.timeseries.boc.models import BoCMeeting

BOC_CALENDAR_URL = (
    "https://www.bankofcanada.ca/core-functions/monetary-policy/"
    "key-interest-rate/"
)

_ROW_RE = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),?\s+"
    r"(?P<year>\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_boc_calendar_html(url: str = BOC_CALENDAR_URL) -> str:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def parse_future_boc_meetings(
    html: str,
    *,
    today: date | None = None,
) -> list[BoCMeeting]:
    if today is None:
        today = date.today()
    seen: set[date] = set()
    meetings: list[BoCMeeting] = []
    for match in _ROW_RE.finditer(html):
        d = date(
            int(match.group("year")),
            _MONTHS[match.group("month").lower()],
            int(match.group("day")),
        )
        if d < today or d in seen:
            continue
        seen.add(d)
        meetings.append(BoCMeeting(meeting_date=d, source="boc_calendar"))
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def fetch_future_boc_meetings(
    *, today: date | None = None, url: str = BOC_CALENDAR_URL
) -> list[BoCMeeting]:
    return parse_future_boc_meetings(fetch_boc_calendar_html(url), today=today)
```

> **Verify at implementation time:** the BoC calendar URL above is best-current-knowledge. The actual page used historically is `https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/` but the exact path can change. If the URL 404s or returns no matching dates, search bankofcanada.ca for "Schedule for FAD" and update `BOC_CALENDAR_URL`.

- [ ] **Step 4: Write `fetcher.py`** — uses BoC Valet API instead of FRED

```python
# src/lseg_toolkit/timeseries/boc/fetcher.py
"""BoC meeting/rate fetcher — calendar dates + Valet API Target Overnight Rate."""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx

from lseg_toolkit.timeseries.boc.calendar_scraper import fetch_future_boc_meetings
from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision

VALET_BASE_URL = "https://www.bankofcanada.ca/valet"
BOC_TARGET_RATE_SERIES = "<paste verified series ID from Task 6 Step 1>"

logger = logging.getLogger(__name__)


def fetch_target_rate_history(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[date, float]:
    """Fetch Target Overnight Rate history from BoC Valet API.

    Valet endpoint:
        /valet/observations/{series}/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Returns object with `observations` array; each entry has a `d` (date) and
    a series-keyed value object like `{"v": "4.50"}`.
    """
    params = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    resp = httpx.get(
        f"{VALET_BASE_URL}/observations/{BOC_TARGET_RATE_SERIES}/json",
        params=params,
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    history: dict[date, float] = {}
    for obs in data.get("observations", []):
        d_str = obs.get("d")
        if not d_str:
            continue
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        value_obj = obs.get(BOC_TARGET_RATE_SERIES)
        if not isinstance(value_obj, dict):
            continue
        v_str = value_obj.get("v")
        if v_str in (None, "", "."):
            continue
        history[d] = float(v_str)
    return history


def _rate_on_or_after(rate_history: dict[date, float], target: date) -> float | None:
    candidates = sorted(d for d in rate_history if d >= target)
    return rate_history[candidates[0]] if candidates else None


def build_boc_meetings_from_dates(
    dates: list[date],
    rate_history: dict[date, float] | None = None,
) -> list[BoCMeeting]:
    meetings: list[BoCMeeting] = []
    prev_rate: float | None = None
    for meeting_date in sorted(dates):
        rate: float | None = None
        if rate_history:
            rate = _rate_on_or_after(rate_history, meeting_date)
        change_bps: int | None = None
        decision: RateDecision | None = None
        if rate is not None and prev_rate is not None:
            diff = rate - prev_rate
            change_bps = int(round(diff * 100))
            if change_bps > 0:
                decision = RateDecision.HIKE
            elif change_bps < 0:
                decision = RateDecision.CUT
            else:
                decision = RateDecision.HOLD
        meetings.append(
            BoCMeeting(
                meeting_date=meeting_date,
                rate_upper=rate,
                rate_lower=rate,
                rate_change_bps=change_bps,
                decision=decision,
                source="valet+boc_calendar",
            )
        )
        if rate is not None:
            prev_rate = rate
    return meetings


def fetch_boc_meetings(
    allow_missing_rate_history: bool = True,
) -> list[BoCMeeting]:
    rate_history: dict[date, float] | None = None
    try:
        rate_history = fetch_target_rate_history()
    except Exception:  # noqa: BLE001
        if not allow_missing_rate_history:
            raise
        logger.warning(
            "BoC Valet unavailable; syncing BoC meetings without rate history",
            exc_info=True,
        )

    change_dates: list[date] = []
    if rate_history:
        prev: float | None = None
        for d in sorted(rate_history):
            if prev is None or rate_history[d] != prev:
                change_dates.append(d)
                prev = rate_history[d]

    historical = build_boc_meetings_from_dates(change_dates, rate_history)

    try:
        future = fetch_future_boc_meetings()
    except Exception:
        logger.warning("Failed to fetch future scheduled BoC meetings", exc_info=True)
        future = []

    combined: dict[date, BoCMeeting] = {m.meeting_date: m for m in historical}
    for m in future:
        combined.setdefault(m.meeting_date, m)
    return [combined[d] for d in sorted(combined)]
```

- [ ] **Step 5: Write `storage.py`**

Identical to BoE storage, with every `boe_meetings` → `boc_meetings`, every `BoEMeeting` → `BoCMeeting`, every `boe` → `boc`. Reproduce in full (engineer should not skip — it's faster to copy-edit than cross-reference):

```python
# src/lseg_toolkit/timeseries/boc/storage.py
"""BoC data storage operations for PostgreSQL/TimescaleDB."""

from __future__ import annotations

import logging
from datetime import date

import psycopg
from psycopg.rows import dict_row

from lseg_toolkit.timeseries.boc.models import BoCMeeting

logger = logging.getLogger(__name__)


def upsert_boc_meeting(conn: psycopg.Connection, meeting: BoCMeeting) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO boc_meetings (
                meeting_date, meeting_start_date, rate_upper, rate_lower,
                rate_change_bps, decision, dissent_count, vote_for, vote_against,
                statement_url, minutes_url, is_scheduled, has_sep, has_presser, source,
                updated_at
            ) VALUES (
                %(meeting_date)s, %(meeting_start_date)s, %(rate_upper)s, %(rate_lower)s,
                %(rate_change_bps)s, %(decision)s, %(dissent_count)s, %(vote_for)s, %(vote_against)s,
                %(statement_url)s, %(minutes_url)s, %(is_scheduled)s, %(has_sep)s, %(has_presser)s,
                %(source)s, NOW()
            )
            ON CONFLICT (meeting_date) DO UPDATE SET
                meeting_start_date = EXCLUDED.meeting_start_date,
                rate_upper = EXCLUDED.rate_upper,
                rate_lower = EXCLUDED.rate_lower,
                rate_change_bps = EXCLUDED.rate_change_bps,
                decision = EXCLUDED.decision,
                dissent_count = EXCLUDED.dissent_count,
                vote_for = EXCLUDED.vote_for,
                vote_against = EXCLUDED.vote_against,
                statement_url = EXCLUDED.statement_url,
                minutes_url = EXCLUDED.minutes_url,
                is_scheduled = EXCLUDED.is_scheduled,
                has_sep = EXCLUDED.has_sep,
                has_presser = EXCLUDED.has_presser,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id
            """,
            {
                "meeting_date": meeting.meeting_date,
                "meeting_start_date": meeting.meeting_start_date,
                "rate_upper": meeting.rate_upper,
                "rate_lower": meeting.rate_lower,
                "rate_change_bps": meeting.rate_change_bps,
                "decision": meeting.decision.value if meeting.decision else None,
                "dissent_count": meeting.dissent_count,
                "vote_for": meeting.vote_for,
                "vote_against": meeting.vote_against,
                "statement_url": meeting.statement_url,
                "minutes_url": meeting.minutes_url,
                "is_scheduled": meeting.is_scheduled,
                "has_sep": meeting.has_sep,
                "has_presser": meeting.has_presser,
                "source": meeting.source,
            },
        )
        result = cur.fetchone()
        return result["id"] if result else 0


def upsert_boc_meetings(
    conn: psycopg.Connection, meetings: list[BoCMeeting]
) -> int:
    count = 0
    for m in meetings:
        upsert_boc_meeting(conn, m)
        count += 1
    conn.commit()
    return count


def sync_boc_meetings(
    conn: psycopg.Connection,
    allow_missing_rate_history: bool = True,
) -> int:
    from lseg_toolkit.timeseries.boc.fetcher import fetch_boc_meetings
    meetings = fetch_boc_meetings(allow_missing_rate_history=allow_missing_rate_history)
    count = upsert_boc_meetings(conn, meetings)
    logger.info("Upserted %d BoC meetings", count)
    return count


def get_boc_meetings(
    conn: psycopg.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    conditions = []
    params: dict = {}
    if start_date:
        conditions.append("meeting_date >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        conditions.append("meeting_date <= %(end_date)s")
        params["end_date"] = end_date
    where = " AND ".join(conditions) if conditions else "TRUE"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM boc_meetings WHERE {where} ORDER BY meeting_date DESC",
            params,
        )
        return list(cur.fetchall())


def get_meeting_count(conn: psycopg.Connection) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS meeting_count FROM boc_meetings")
        result = cur.fetchone()
        return int(result["meeting_count"]) if result else 0
```

- [ ] **Step 6: Write `__init__.py`**

```python
# src/lseg_toolkit/timeseries/boc/__init__.py
"""BoC (Bank of Canada) FAD meeting data module."""

from lseg_toolkit.timeseries.boc.calendar_scraper import (
    BOC_CALENDAR_URL,
    fetch_future_boc_meetings,
    parse_future_boc_meetings,
)
from lseg_toolkit.timeseries.boc.fetcher import (
    fetch_boc_meetings,
    fetch_target_rate_history,
)
from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision
from lseg_toolkit.timeseries.boc.storage import (
    get_boc_meetings,
    get_meeting_count,
    sync_boc_meetings,
    upsert_boc_meeting,
    upsert_boc_meetings,
)

__all__ = [
    "BOC_CALENDAR_URL",
    "BoCMeeting",
    "RateDecision",
    "fetch_boc_meetings",
    "fetch_future_boc_meetings",
    "fetch_target_rate_history",
    "get_boc_meetings",
    "get_meeting_count",
    "parse_future_boc_meetings",
    "sync_boc_meetings",
    "upsert_boc_meeting",
    "upsert_boc_meetings",
]
```

- [ ] **Step 7: Write tests in `tests/timeseries/test_boc.py`**

```python
"""Tests for the BoC module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision

BOC_HTML = """
<html><body>
<p>March 12, 2026</p>
<p>April 16, 2026</p>
<p>June 4, 2026</p>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.boc.calendar_scraper import (
            parse_future_boc_meetings,
        )
        meetings = parse_future_boc_meetings(BOC_HTML, today=date(2026, 4, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 4, 16),
            date(2026, 6, 4),
        ]


class TestFetcherBuilders:
    def test_build_assigns_decision(self):
        from lseg_toolkit.timeseries.boc.fetcher import build_boc_meetings_from_dates
        dates = [date(2026, 1, 22), date(2026, 3, 12)]
        rate_history = {date(2026, 1, 22): 4.0, date(2026, 3, 12): 3.75}
        meetings = build_boc_meetings_from_dates(dates, rate_history)
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25


class TestFetchBoCMeetings:
    @patch("lseg_toolkit.timeseries.boc.fetcher.fetch_future_boc_meetings")
    @patch("lseg_toolkit.timeseries.boc.fetcher.fetch_target_rate_history")
    def test_falls_back_when_valet_unreachable(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boc.fetcher import fetch_boc_meetings
        mock_rate.side_effect = RuntimeError("Valet 503")
        mock_future.return_value = [
            BoCMeeting(meeting_date=date(2026, 4, 16), source="boc_calendar")
        ]
        meetings = fetch_boc_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
```

- [ ] **Step 8: Run BoC tests**

```bash
uv run pytest tests/timeseries/test_boc.py -v --no-cov
```

Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/lseg_toolkit/timeseries/boc/ tests/timeseries/test_boc.py
git commit -m "feat(boc): add Bank of Canada FAD meeting data module"
```

---

## Task 7: Default rate-decision job specs + ensure helper

**Goal:** Add a registry of rate-decision-modeling job specs to `default_jobs.py` and an `ensure_rate_decision_jobs(conn, *, skip_eur_ois)` helper that idempotently creates them.

**Files:**
- Modify: `src/lseg_toolkit/timeseries/scheduler/default_jobs.py`
- Modify: `tests/timeseries/test_scheduler.py` (add tests)

- [ ] **Step 1: Write the failing test**

Append to `tests/timeseries/test_scheduler.py`:

```python
def test_rate_decision_job_specs_cover_all_six_groups():
    from lseg_toolkit.timeseries.scheduler.default_jobs import (
        RATE_DECISION_JOB_SPECS,
    )
    groups = {spec.instrument_group for spec in RATE_DECISION_JOB_SPECS}
    assert groups == {
        "ois_usd",
        "ois_eur",
        "ois_gbp",
        "ois_g7",
        "benchmark_fixings",
        "euribor_fixings",
    }


def test_rate_decision_job_specs_use_consistent_cron_and_lookback():
    from lseg_toolkit.timeseries.scheduler.default_jobs import (
        RATE_DECISION_JOB_SPECS,
    )
    for spec in RATE_DECISION_JOB_SPECS:
        assert spec.granularity == "daily"
        assert spec.schedule_cron == "0 22 * * 1-5"
        assert spec.lookback_days == 365
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/timeseries/test_scheduler.py::test_rate_decision_job_specs_cover_all_six_groups -v --no-cov
```

Expected: `ImportError`.

- [ ] **Step 3: Add specs and helper to default_jobs.py**

Append to `src/lseg_toolkit/timeseries/scheduler/default_jobs.py`:

```python
RATE_DECISION_JOB_SPECS: list[DefaultJobSpec] = [
    DefaultJobSpec(
        name="ois_usd_daily",
        instrument_group="ois_usd",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily USD OIS curve",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_eur_daily",
        instrument_group="ois_eur",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily EUR OIS (ESTR-linked)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_gbp_daily",
        instrument_group="ois_gbp",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily GBP OIS (SONIA-linked)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="ois_g7_daily",
        instrument_group="ois_g7",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily G7 OIS (covers CAD, JPY, CHF, AUD, NZD)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="benchmark_fixings_daily",
        instrument_group="benchmark_fixings",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily overnight benchmarks (SOFR, ESTR, GBPOND, CADCORRA, etc.)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
    DefaultJobSpec(
        name="euribor_fixings_daily",
        instrument_group="euribor_fixings",
        granularity="daily",
        schedule_cron="0 22 * * 1-5",
        description="Daily EURIBOR fixings (1M/3M/6M/12M)",
        priority=45,
        lookback_days=365,
        max_chunk_days=90,
    ),
]


def _eur_ois_unwired() -> bool:
    """True iff EUR OIS RICs aren't (or aren't yet) wired to a working pattern."""
    try:
        from lseg_toolkit.timeseries.constants import EUR_OIS_TENORS
    except ImportError:
        return True
    return not EUR_OIS_TENORS


def ensure_rate_decision_jobs(
    conn,
    *,
    skip_eur_ois: bool | None = None,
) -> dict[str, str]:
    """Ensure the rate-decision-modeling jobs exist.

    `skip_eur_ois`:
        - None  (default): auto-skip if EUR_OIS_TENORS is missing/empty.
        - True : always skip ois_eur_daily.
        - False: always include ois_eur_daily.

    Returns a mapping of job name to action (`created`, `exists`, or `skipped`).
    """
    if skip_eur_ois is None:
        skip_eur_ois = _eur_ois_unwired()

    results: dict[str, str] = {}
    for spec in RATE_DECISION_JOB_SPECS:
        if spec.name == "ois_eur_daily" and skip_eur_ois:
            results[spec.name] = "skipped"
            continue
        if get_job_by_name(conn, spec.name):
            results[spec.name] = "exists"
            continue
        create_job(
            conn,
            name=spec.name,
            instrument_group=spec.instrument_group,
            granularity=spec.granularity,
            schedule_cron=spec.schedule_cron,
            description=spec.description,
            priority=spec.priority,
            lookback_days=spec.lookback_days,
            max_chunk_days=spec.max_chunk_days,
        )
        results[spec.name] = "created"
    return results
```

- [ ] **Step 4: Run tests, expect pass**

```bash
uv run pytest tests/timeseries/test_scheduler.py -v --no-cov
```

Expected: tests added in Step 1 PASS. Existing tests still PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lseg_toolkit/timeseries/scheduler/default_jobs.py tests/timeseries/test_scheduler.py
git commit -m "feat(scheduler): add rate-decision-modeling default job specs"
```

---

## Task 8: `seed-rate-decision-modeling` CLI subcommand + tests

**Goal:** Wire the new helper to a CLI command mirroring `seed-ff-strip`.

**Files:**
- Modify: `src/lseg_toolkit/timeseries/scheduler/cli.py`
- Create: `tests/timeseries/test_seed_rate_decision_modeling.py`

- [ ] **Step 1: Write a failing test for the command idempotency**

```python
# tests/timeseries/test_seed_rate_decision_modeling.py
"""Tests for the seed-rate-decision-modeling subcommand."""

from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.scheduler.default_jobs import ensure_rate_decision_jobs


def test_ensure_is_idempotent(monkeypatch):
    # Mimic a connection that already has every job
    from lseg_toolkit.timeseries.scheduler import default_jobs

    captured = {}

    def fake_get_job_by_name(conn, name):
        return {"id": 1, "name": name}  # always exists

    def fake_create_job(*args, **kwargs):
        raise AssertionError("create_job must not be called when job exists")

    monkeypatch.setattr(default_jobs, "get_job_by_name", fake_get_job_by_name)
    monkeypatch.setattr(default_jobs, "create_job", fake_create_job)

    results = ensure_rate_decision_jobs(MagicMock(), skip_eur_ois=False)
    assert all(action == "exists" for action in results.values())


def test_skip_eur_ois_branch(monkeypatch):
    from lseg_toolkit.timeseries.scheduler import default_jobs

    monkeypatch.setattr(default_jobs, "get_job_by_name", lambda c, n: None)
    monkeypatch.setattr(default_jobs, "create_job", lambda *a, **k: 1)

    results = ensure_rate_decision_jobs(MagicMock(), skip_eur_ois=True)
    assert results["ois_eur_daily"] == "skipped"
    assert results["ois_usd_daily"] == "created"


def test_auto_skip_when_eur_tenors_missing(monkeypatch):
    from lseg_toolkit.timeseries.scheduler import default_jobs

    # Force the lookup to think EUR_OIS_TENORS is missing
    monkeypatch.setattr(default_jobs, "_eur_ois_unwired", lambda: True)
    monkeypatch.setattr(default_jobs, "get_job_by_name", lambda c, n: None)
    monkeypatch.setattr(default_jobs, "create_job", lambda *a, **k: 1)

    results = ensure_rate_decision_jobs(MagicMock())
    assert results["ois_eur_daily"] == "skipped"
```

- [ ] **Step 2: Run, expect pass (the helper from Task 7 already covers this)**

```bash
uv run pytest tests/timeseries/test_seed_rate_decision_modeling.py -v --no-cov
```

Expected: 3 PASS. (If any fails, the helper logic in Task 7 needs adjustment — fix it there.)

- [ ] **Step 3: Add the subcommand to `cli.py`**

In `src/lseg_toolkit/timeseries/scheduler/cli.py`:

a) Update the import block at the top to add `ensure_rate_decision_jobs`:

```python
from lseg_toolkit.timeseries.scheduler.default_jobs import (
    ensure_ff_strip_jobs,
    ensure_rate_decision_jobs,
)
```

b) Register the subparser. Insert after the `seed-ff-strip` block (around line 109):

```python
    seed_rd_parser = subparsers.add_parser(
        "seed-rate-decision-modeling",
        help=(
            "Create the default rate-decision-modeling daily jobs "
            "(OIS USD/EUR/GBP/G7, benchmark fixings, EURIBOR fixings)"
        ),
    )
    seed_rd_parser.add_argument(
        "--skip-eur-ois",
        action="store_true",
        help="Skip ois_eur_daily even if EUR_OIS_TENORS is wired",
    )
    seed_rd_parser.add_argument(
        "--include-eur-ois",
        action="store_true",
        help="Force ois_eur_daily even if EUR_OIS_TENORS is empty",
    )
```

c) Wire the dispatch. Insert in the `if/elif` chain (around line 172):

```python
        elif args.command == "seed-rate-decision-modeling":
            return cmd_seed_rate_decision_modeling(args)
```

d) Add the handler function below `cmd_seed_ff_strip`:

```python
def cmd_seed_rate_decision_modeling(args) -> int:
    """Create the default rate-decision-modeling jobs if they do not exist."""
    db_config = DatabaseConfig.from_env()

    # Resolve skip_eur_ois precedence: explicit flags override auto-detect.
    if args.skip_eur_ois and args.include_eur_ois:
        print("Error: --skip-eur-ois and --include-eur-ois are mutually exclusive")
        return 1
    if args.skip_eur_ois:
        skip = True
    elif args.include_eur_ois:
        skip = False
    else:
        skip = None  # auto-detect via EUR_OIS_TENORS

    with get_connection(config=db_config) as conn:
        results = ensure_rate_decision_jobs(conn, skip_eur_ois=skip)
        conn.commit()

    for name, action in results.items():
        print(f"{name}: {action}")

    created = sum(1 for a in results.values() if a == "created")
    existing = sum(1 for a in results.values() if a == "exists")
    skipped = sum(1 for a in results.values() if a == "skipped")
    print(
        f"\nRate-decision jobs ready ({created} created, "
        f"{existing} existing, {skipped} skipped)"
    )
    return 0
```

- [ ] **Step 4: Smoke-check the CLI parses (no DB connection)**

```bash
uv run lseg-scheduler seed-rate-decision-modeling --help
```

Expected: prints help text with both flags listed; exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/lseg_toolkit/timeseries/scheduler/cli.py \
        tests/timeseries/test_seed_rate_decision_modeling.py
git commit -m "feat(scheduler): add seed-rate-decision-modeling CLI subcommand"
```

---

## Task 9: Smoke run — seed jobs, run backfill, populate meeting tables

**Goal:** End-to-end exercise the new code paths against the live DB.

**Files:** none (operational task)

- [ ] **Step 1: Apply DB schema (idempotent)**

Use the timescaledb-access workflow first to confirm DB env. Then:

```bash
uv run python -c "from lseg_toolkit.timeseries.storage import init_db; init_db()"
```

- [ ] **Step 2: Seed the rate-decision jobs**

```bash
uv run lseg-scheduler seed-rate-decision-modeling
```

Expected output: each of the 6 jobs shows `created` or (if previously created) `exists`. If Task 1 returned FAIL, `ois_eur_daily` shows `skipped`.

- [ ] **Step 3: Verify jobs landed**

```bash
uv run lseg-scheduler jobs
```

Expected: the new jobs appear with `Group=ois_*` / `benchmark_fixings` / `euribor_fixings`, `Schedule="0 22 * * 1-5"`, `On=Y`.

- [ ] **Step 4: Run the backfill — one job at a time**

```bash
for j in ois_usd_daily ois_eur_daily ois_gbp_daily ois_g7_daily \
         benchmark_fixings_daily euribor_fixings_daily; do
  echo "=== $j ==="
  uv run lseg-scheduler run "$j" || echo "(continuing despite failure)"
done
```

Skip `ois_eur_daily` if Task 1 returned FAIL. For each job, expect:
- `Status: completed` or `partial`
- `Instruments: N/N success` (some failures are tolerable — record them)
- `Rows extracted: > 0`

Capture per-instrument failures with `uv run lseg-scheduler state --failed` and triage if any are systematic (e.g., a whole currency).

- [ ] **Step 5: Sync the three CB meeting tables**

```bash
uv run python -c "
from lseg_toolkit.timeseries.storage import get_connection
from lseg_toolkit.timeseries.ecb import sync_ecb_meetings
from lseg_toolkit.timeseries.boe import sync_boe_meetings
from lseg_toolkit.timeseries.boc import sync_boc_meetings
with get_connection() as c:
    print('ECB:', sync_ecb_meetings(c))
    print('BoE:', sync_boe_meetings(c))
    print('BoC:', sync_boc_meetings(c))
"
```

Expected: each `sync_*` returns a count > 0. If FRED key is missing, expect `WARNING: ... without rate history` and rows with NULL rate columns — that's acceptable for the calendar half.

- [ ] **Step 6: Verify row counts in DB**

```bash
psql -c "
SELECT 'ecb' AS cb, COUNT(*) FROM ecb_meetings
UNION ALL SELECT 'boe', COUNT(*) FROM boe_meetings
UNION ALL SELECT 'boc', COUNT(*) FROM boc_meetings
UNION ALL SELECT 'fomc', COUNT(*) FROM fomc_meetings;
"
```

```bash
psql -c "
SELECT instrument_group, COUNT(DISTINCT instrument_id) AS instruments, MIN(ts), MAX(ts)
FROM scheduler_state s
JOIN scheduler_jobs j ON s.job_id = j.id
JOIN timeseries_rate r ON s.instrument_id = r.instrument_id
WHERE j.name IN ('ois_usd_daily','ois_eur_daily','ois_gbp_daily','ois_g7_daily')
GROUP BY instrument_group;
"
```

Expected: meeting tables have ≥ 4 rows each (last 1Y has at least one meeting per CB), `timeseries_rate` has data spanning roughly the last 365 days.

- [ ] **Step 7: Record what happened in plan tracker**

Edit this plan file and append a "Smoke run results" section with:
- Per-job: status + rows_extracted
- Per-CB: meeting count + min/max meeting_date in DB
- Any RIC failures (so they get triaged before the modeling repo starts pulling)

- [ ] **Step 8: Commit the tracker update**

```bash
git add docs/superpowers/plans/2026-04-25-rate-decision-data.md
git commit -m "chore(plan): record rate-decision smoke-run results"
```

---

## Task 10: Documentation updates

**Goal:** Reflect new state in the docs called out by the spec.

**Files:**
- Modify: `docs/instruments/RATES.md` (EUR OIS section)
- Modify: `docs/instruments/OVERVIEW.md` (line ~43, the EUR-OIS row)
- Modify: `docs/STORAGE_SCHEMA.md` (section 4)
- Modify: `docs/SCHEDULER.md` (commands table)

- [ ] **Step 1: Update `docs/instruments/RATES.md` EUR section**

Replace the "EUR - Use IRS Instead of OIS" block (around line 32–35 — locate via `rg -n 'EUR - Use IRS' docs/instruments/RATES.md`) with the actual validation outcome.

If Task 1 was FULL or PARTIAL, write a table mirroring the USD OIS table:

```markdown
### EUR ESTR OIS (Validated YYYY-MM-DD)

**Pattern**: `EUREST{tenor}=`

| Tenor | LSEG RIC | Status | Daily | Notes |
|-------|----------|--------|-------|-------|
| 1W | `EUREST1W=` | ✅/❌ | ✅/❌ |  |
| 1M | `EUREST1M=` | ✅/❌ | ✅/❌ |  |
| ... | ... | ... | ... | ... |

For longer tenors (>= 1Y) the EUR IRS table below remains the recommended source.
```

If Task 1 was FAIL, replace with:

```markdown
### EUR OIS — not currently accessible

`EUR{tenor}OIS=` and `EUREST{tenor}=` patterns both failed validation on YYYY-MM-DD
(see `dev_scripts/eurest_validation_YYYY-MM-DD.log`). For ECB-meeting probability
modeling, use EURIBOR fixings (table below) plus `FEIc1` 3M EURIBOR futures, accepting
the EURIBOR-ESTR basis.
```

- [ ] **Step 2: Update `docs/instruments/OVERVIEW.md:43`**

Find the line:

```markdown
| EUR OIS | `EUR1YOIS=` ❌ | `EUREST1Y=` | Use `EUREST{tenor}=` pattern |
```

If Task 1 was FULL/PARTIAL:

```markdown
| EUR OIS | `EUR1YOIS=` ❌ | `EUREST1Y=` ✅ | Validated YYYY-MM-DD; see RATES.md for tenor coverage |
```

If Task 1 was FAIL:

```markdown
| EUR OIS | `EUR1YOIS=` ❌ | `EUREST1Y=` ❌ | Both patterns failed YYYY-MM-DD; use EURIBOR for short-end |
```

- [ ] **Step 3: Update `docs/STORAGE_SCHEMA.md` section 4**

Locate the FOMC table block (around the heading "## 4. FOMC and prediction-market tables") and add three rows immediately under `fomc_meetings`:

```markdown
| `ecb_meetings` | ECB Governing Council monetary-policy decisions (Deposit Facility Rate) |
| `boe_meetings` | BoE MPC decisions (Bank Rate) |
| `boc_meetings` | BoC Fixed Announcement Date decisions (Target Overnight Rate) |
```

Also rename the section heading to reflect the broader scope:

```markdown
## 4. Central-bank meeting and prediction-market tables
```

- [ ] **Step 4: Update `docs/SCHEDULER.md` commands table**

Locate the commands table (around line 41–54 — `rg -n 'seed-ff-strip' docs/SCHEDULER.md`). Add a new row:

```markdown
| `seed-rate-decision-modeling` | Seed default rate-decision-modeling jobs (OIS USD/EUR/GBP/G7, benchmark/EURIBOR fixings) |
```

- [ ] **Step 5: Smoke-check docs render**

```bash
uv run pre-commit run --all-files --files \
    docs/instruments/RATES.md docs/instruments/OVERVIEW.md \
    docs/STORAGE_SCHEMA.md docs/SCHEDULER.md
```

(If pre-commit doesn't lint markdown, this is a no-op — fine.)

- [ ] **Step 6: Commit**

```bash
git add docs/instruments/RATES.md docs/instruments/OVERVIEW.md \
        docs/STORAGE_SCHEMA.md docs/SCHEDULER.md
git commit -m "docs(rates): reflect EUREST validation outcome and new CB meeting tables"
```

---

## Task 11: Final cleanup + full test run

**Goal:** Last sanity pass.

- [ ] **Step 1: Run the full test suite**

```bash
cd "/home/jlipworth/Refinitiv Projects"
uv run pytest tests/ --no-cov
```

Expected: all tests pass. If any pre-existing test breaks because of an import or constants change, investigate (likely the EUR universe change cascaded somewhere — fix the actual root cause, do not skip the test).

- [ ] **Step 2: Run pre-commit on the diff**

```bash
git diff --name-only HEAD~10 HEAD | xargs -r uv run pre-commit run --files
```

Expected: clean, or fix and re-commit.

- [ ] **Step 3: Final summary log to plan tracker**

Append a "Done" section at the bottom of this plan file with:
- The Task 1 outcome (FULL/PARTIAL/FAIL)
- The 6 commit SHAs (or the commit-range)
- Any deferred items the user should know about (e.g., "BoC Valet series ID was wrong, switched to V122530")

- [ ] **Step 4: Commit and stop**

```bash
git add docs/superpowers/plans/2026-04-25-rate-decision-data.md
git commit -m "chore(plan): record rate-decision implementation completion"
```

---

## Self-review notes (engineer should not need these)

**Spec coverage:** Phase 1 → Task 1; Phase 2 → Task 2; Phase 3 → Tasks 3–6; Phase 4 → Tasks 7–8; Phase 5 → Tasks 9–10; testing posture → spread across Tasks 2/3/4/5/6/7/8 + Task 11. Doc deliverables → Task 10.

**Conditional path:** Task 2 is explicitly skip-if-FAIL. Task 9 Step 4 skips `ois_eur_daily` if Task 1 returned FAIL. Task 10 has FAIL/non-FAIL doc text variants.

**External-data verification:** Tasks 5 and 6 each begin with a "verify FRED/Valet series ID" step before code that hardcodes the ID — prevents silently shipping a wrong series.

**Idempotency:** Task 3 uses `CREATE TABLE IF NOT EXISTS`; Tasks 4/5/6 use `ON CONFLICT DO UPDATE`; Task 7 helper checks `get_job_by_name` before insert; smoke runs in Task 9 are all re-runnable.

---

## Implementation log (2026-04-25)

Branch: `rate-decision-data` (worktree at `.worktrees/rate-decision-data/`).

**Tasks completed autonomously (no live systems):**
- Task 1: probe script written to `dev_scripts/validate_eurest_ois.py`. Live run deferred — LSEG Workspace was offline.
- Task 3 (schema): `328cb0a` — adds `ecb_meetings`, `boe_meetings`, `boc_meetings` to `pg_schema.SCHEMA_SQL`.
- Task 4 (ECB module): `267e6bd` — 5 mocked tests passing.
- Task 5 (BoE module): `624d073` — FRED series **`BOERUKM`** verified via web search (not `IUDSOIA`, which is SONIA). 3 mocked tests passing.
- Task 6 (BoC module): `cf8a0cb` — Valet series **`V39079`** verified live against `https://www.bankofcanada.ca/valet/observations/V39079/json`. 3 mocked tests passing.
- Task 7 (default specs + helper): `264b1dd` — `RATE_DECISION_JOB_SPECS` + `ensure_rate_decision_jobs` with `_eur_ois_unwired()` auto-detect. 2 tests passing.
- Task 8 (CLI): `6ff34af` — `seed-rate-decision-modeling` subcommand with `--skip-eur-ois` / `--include-eur-ois`. 3 tests passing.
- Task 10 (docs, pre-validation form): `3539b42` — RATES.md / OVERVIEW.md flag EUREST as "validation pending"; STORAGE_SCHEMA.md / SCHEDULER.md add CB tables and seeder row.
- Task 11 final test run: 495 passed / 1 pre-existing failure (unrelated, `tests/earnings/test_pipeline.py::test_pipeline_initialization` opens a live LSEG socket and isn't `@pytest.mark.integration`-gated) / 2 skipped / 90 integration deselected.

**Deferred for user (require live systems):**
- **Task 1 live run** (LSEG Workspace required): `uv run python dev_scripts/validate_eurest_ois.py | tee dev_scripts/eurest_validation_$(date +%F).log`
- **Task 2** (conditional): only run if Task 1 ≠ FAIL — wire validated tenors into `EUR_OIS_TENORS` in `constants.py` and switch `_build_ois_eur` to `get_eur_ois_ric`.
- **Task 3 Step 5** (DB apply): `uv run python -c 'from lseg_toolkit.timeseries.storage import init_db; init_db()'` — needs DB env (`TSDB_*`/`POSTGRES_*` or Infisical).
- **Task 9** (smoke run): once DB env loaded, run `uv run lseg-scheduler seed-rate-decision-modeling`, then loop the 6 jobs through `lseg-scheduler run`, then call `sync_ecb_meetings` / `sync_boe_meetings` / `sync_boc_meetings` (FRED key required for ECB/BoE; BoC needs no key).
- **Task 10 doc refinement**: once Task 1 outcome is known, swap the "validation pending" sections in `RATES.md` and `OVERVIEW.md` for the validated tenor table (or the FAIL variant).

**Conditional-path defaults applied:**
- `ensure_rate_decision_jobs` will auto-skip `ois_eur_daily` until `EUR_OIS_TENORS` is added to `constants.py` (so seeding is safe to run before Task 1 completes).

---

## Continuation log (2026-04-25, post-LSEG-restart)

LSEG Workspace started; deferred items executed.

**Task 1 (live EUREST probe)** — outcome **PARTIAL** (3/5 sub-1Y core hits):

| Tenor | Status |
|-------|--------|
| 1W | ❌ DataRetrievalError |
| 1M | ✅ 22 rows |
| 2M | ✅ 22 rows |
| 3M | ✅ 22 rows |
| 6M | ✅ 22 rows |
| 9M | ✅ 22 rows |
| 12M | ❌ DataRetrievalError |
| 18M | ✅ 22 rows |
| 2Y | ✅ 22 rows |

**Task 2 (wire EUR OIS)** — `EUR_OIS_TENORS = ['1M','2M','3M','6M','9M','18M','2Y']` and `get_eur_ois_ric()` added to `constants.py`. `_build_ois_eur` and the EUR branch of `_build_ois_g7` switched to `EUREST{tenor}=`. Regression test `test_eur_ois_now_wired` added.

**Task 3 Step 5 (DB schema apply)** — `init_db()` ran against `jlfinance` (POSTGRES_* loaded from `~/Refinitiv Projects/.env`). All four CB tables present: `fomc_meetings`, `ecb_meetings`, `boe_meetings`, `boc_meetings`.

**Task 9 (smoke run)** — `seed-rate-decision-modeling` created all 6 jobs; all 6 completed successfully:

| Job | Instruments | Rows |
|-----|-------------|------|
| `ois_usd_daily` | 23/23 | 5,908 |
| `ois_eur_daily` | 7/7 | 1,792 |
| `ois_gbp_daily` | 14/14 | 3,598 |
| `ois_g7_daily` | 63/63 | 9,956 |
| `benchmark_fixings_daily` | 4/4 | 993 |
| `euribor_fixings_daily` | 4/4 | 1,004 |

**CB meeting sync** — BoC fully populated; ECB/BoE limited without FRED key:
- `boc_meetings`: 33 rows, 2009-04-21 → 2025-10-30 (full history via Valet API).
- `ecb_meetings`: 22 rows, 2026-04-30 → 2028-12-07 (future calendar only without FRED).
- `boe_meetings`: 1 row, 2026-04-30 (BoE upcoming-MPC page is short; needs FRED for past).

**Scraper bug fixes (committed during continuation):**
- ECB calendar parser was matching the press-conference landing-page date markup, not the actual meeting list. Live page uses `DD/MM/YYYY <description>` rows. Rewrote `parse_future_ecb_meetings` to:
  1. Strip HTML tags / collapse whitespace.
  2. Match `DD/MM/YYYY` followed by description bounded by lookahead at next date.
  3. Filter to "monetary policy" + "Day 2" or "press conference" rows (excludes Day 1, non-monetary, General Council).
  4. Kept legacy long-form regex as fallback for fixture HTML used in unit tests.
- BoE calendar fetch was returning 403 to the default httpx UA. Added `Mozilla/5.0 ...` browser UA to `fetch_boe_calendar_html`. Same UA added to ECB defensively.
- New regression test `test_parse_live_ddmmyyyy_format_filters_to_day2` added against the live row format.

**Final test sweep:** `437 passed, 2 skipped, 24 deselected` (timeseries package, integration deselected).

**Still deferred for user:**
- Set `FRED_API_KEY` and re-run `sync_ecb_meetings` / `sync_boe_meetings` for historical decision rows (rate_upper, decision, dissent_count). BoC already has full history via Valet.
- 1W and 12M EUREST tenors are unavailable; for 12M EUR rates, fall back to `EURIRS1Y=`.
