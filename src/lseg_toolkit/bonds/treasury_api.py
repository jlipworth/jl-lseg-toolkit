"""
Treasury Fiscal Data API client for fetching historical note/bond data.

Used to reconstruct historical deliverable baskets for bond basis analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)

FISCAL_DATA_BASE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    "/v1/accounting/od/auctions_query"
)

# Eligibility rules: (min_remaining_days, max_remaining_days, max_original_days)
# Based on CME contract specifications
ELIGIBILITY_RULES: dict[str, tuple[int, int, int]] = {
    # 2-Year: original ≤ 2y 3m, remaining 1y 9m - 2y
    "TU": (int(1.75 * 365), int(2 * 365), int(2.25 * 365)),
    "ZT": (int(1.75 * 365), int(2 * 365), int(2.25 * 365)),
    # 5-Year: original ≤ 5y 3m, remaining 4y 2m - 5y 3m
    "FV": (int(4.17 * 365), int(5.25 * 365), int(5.25 * 365)),
    "ZF": (int(4.17 * 365), int(5.25 * 365), int(5.25 * 365)),
    # 10-Year: original ≤ 10y, remaining 6y 6m - 10y
    "TY": (int(6.5 * 365), int(10 * 365), int(10 * 365)),
    "ZN": (int(6.5 * 365), int(10 * 365), int(10 * 365)),
    # Ultra 10-Year: original = 10y, remaining 9y 5m - 10y
    "TN": (int(9.42 * 365), int(10 * 365), int(10 * 365)),
}


@dataclass
class TreasuryNote:
    """Treasury note/bond data from Fiscal Data API."""

    cusip: str
    coupon_rate: float
    issue_date: date
    maturity_date: date
    auction_date: date
    security_term: str

    @property
    def original_term_days(self) -> int:
        """Original term in days from issue to maturity."""
        return (self.maturity_date - self.issue_date).days

    def remaining_term_days(self, as_of: date) -> int:
        """Remaining term in days from given date to maturity."""
        return (self.maturity_date - as_of).days

    def lseg_ric(self) -> str:
        """LSEG RIC format for this bond."""
        return f"{self.cusip}="


def _parse_date(date_str: str | None) -> date | None:
    """Parse date from API response."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


@lru_cache(maxsize=1)
def fetch_all_notes() -> list[TreasuryNote]:
    """
    Fetch all Treasury notes from Fiscal Data API.

    Results are cached in memory for the session.

    Returns:
        List of TreasuryNote objects.
    """
    all_notes: list[TreasuryNote] = []
    page = 1

    logger.info("Fetching Treasury notes from Fiscal Data API...")

    while True:
        params: dict[str, str | int] = {
            "filter": "security_type:eq:Note",
            "fields": "cusip,security_term,int_rate,issue_date,maturity_date,auction_date,original_security_term",
            "sort": "-auction_date",
            "page[size]": 500,
            "page[number]": page,
        }

        try:
            resp = requests.get(FISCAL_DATA_BASE_URL, params=params, timeout=60)  # type: ignore[arg-type]
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Error fetching page {page}: {e}")
            break

        result = resp.json()
        data = result.get("data", [])

        if not data:
            break

        for row in data:
            issue = _parse_date(row.get("issue_date"))
            maturity = _parse_date(row.get("maturity_date"))
            auction = _parse_date(row.get("auction_date"))

            if not all([issue, maturity, auction]):
                continue

            coupon = row.get("int_rate")
            if coupon is None or coupon == "null" or coupon == "":
                continue

            try:
                coupon_float = float(coupon)
            except (ValueError, TypeError):
                continue

            note = TreasuryNote(
                cusip=row.get("cusip", ""),
                coupon_rate=coupon_float,
                issue_date=issue,  # type: ignore
                maturity_date=maturity,  # type: ignore
                auction_date=auction,  # type: ignore
                security_term=row.get("original_security_term")
                or row.get("security_term")
                or "",
            )
            all_notes.append(note)

        meta = result.get("meta", {})
        total = meta.get("total-count", 0)

        if len(all_notes) >= total:
            break
        page += 1

    logger.info(f"Fetched {len(all_notes)} Treasury notes")
    return all_notes


def get_deliverable_basket(
    futures_root: str,
    first_delivery_date: date,
    notes: list[TreasuryNote] | None = None,
) -> list[TreasuryNote]:
    """
    Get deliverable basket for a futures contract.

    Reconstructs the basket by applying CME eligibility rules to all
    Treasury notes that were issued before the delivery date.

    Args:
        futures_root: Futures root ('TY', 'FV', 'TU', etc.)
        first_delivery_date: First delivery date of the contract
        notes: Pre-fetched notes, or None to fetch from API

    Returns:
        List of eligible TreasuryNote objects
    """
    if notes is None:
        notes = fetch_all_notes()

    rules = ELIGIBILITY_RULES.get(futures_root)
    if not rules:
        logger.error(f"Unknown futures root: {futures_root}")
        return []

    min_remaining, max_remaining, max_original = rules

    eligible = []
    for note in notes:
        # Must be issued before delivery
        if note.issue_date >= first_delivery_date:
            continue

        # Must not have matured
        if note.maturity_date <= first_delivery_date:
            continue

        # Check original maturity
        if note.original_term_days > max_original:
            continue

        # Check remaining maturity at delivery
        remaining = note.remaining_term_days(first_delivery_date)
        if min_remaining <= remaining <= max_remaining:
            eligible.append(note)

    # Deduplicate by CUSIP (same note can appear in multiple auctions/reopenings)
    seen_cusips: set[str] = set()
    unique_eligible = []
    for note in eligible:
        if note.cusip not in seen_cusips:
            seen_cusips.add(note.cusip)
            unique_eligible.append(note)
    eligible = unique_eligible

    # Sort by maturity (longest first - typically higher duration)
    eligible.sort(key=lambda n: n.maturity_date, reverse=True)

    logger.info(
        f"Found {len(eligible)} deliverable notes for {futures_root} "
        f"at {first_delivery_date}"
    )
    return eligible
