"""Conservative Polymarket market-family resolution helpers.

This module intentionally does not try to classify the full Polymarket universe.
It only resolves a small set of high-value market families we currently care
about for macro/Fed workflows. Everything else is left unresolved or excluded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

EXCLUDE_TERMS = (
    "federal charge",
    "federal charges",
    "federal criminal",
    "federal prison",
    "federal judge",
)

MACRO_TERMS = (
    "federal reserve",
    "federal funds",
    "fed decision",
    "fed rate",
    "fed rates",
    "fomc",
    "rate cut",
    "rate hike",
    "interest rate",
    "powell",
    "inflation",
    "cpi",
    "jobs report",
    "unemployment",
)

MACRO_TAG_SLUGS = {
    "fed",
    "fed-rates",
    "fomc",
    "powell",
    "jerome-powell",
    "macro",
    "macro-indicators",
    "macro-unemployment",
    "inflation",
    "jobs-report",
}

FOMC_DECISION_PATTERNS = (
    "fed-decision-in-",
    "fed decision in ",
    "fed interest rates",
    "fed-interest-rates-",
    "fomc decision",
)

POWELL_PRESS_PATTERNS = (
    "press conference",
    "intro statement",
    "say during",
    "powell bingo",
)

CUT_COUNT_PATTERNS = (
    "how many fed rate cuts",
    "how-many-fed-rate-cuts",
)

YEAR_END_RATE_PATTERNS = (
    "what will the fed rate be at the end of",
    "what-will-the-fed-rate-be-at-the-end-of-",
)


@dataclass(frozen=True)
class PolymarketResolution:
    """Conservative resolution result for a Polymarket event/market."""

    family: str
    is_macro_candidate: bool
    is_fomc_link_candidate: bool
    reason: str


def _text_blob(raw: dict[str, Any]) -> str:
    """Build a normalized text blob from event/market payloads."""
    parts: list[str] = []
    for field in (
        "title",
        "question",
        "slug",
        "subtitle",
        "description",
        "resolutionSource",
        "seriesSlug",
        "category",
    ):
        value = raw.get(field)
        if isinstance(value, str):
            parts.append(value)

    for tag in raw.get("tags") or []:
        if isinstance(tag, dict):
            for key in ("label", "slug"):
                value = tag.get(key)
                if isinstance(value, str):
                    parts.append(value)

    for market in raw.get("markets") or []:
        if isinstance(market, dict):
            for key in ("question", "title", "slug", "description"):
                value = market.get(key)
                if isinstance(value, str):
                    parts.append(value)

    return " \n".join(parts).lower()


def _tag_slugs(raw: dict[str, Any]) -> set[str]:
    return {
        str(tag.get("slug")).lower()
        for tag in raw.get("tags") or []
        if isinstance(tag, dict) and tag.get("slug")
    }


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def is_macro_resolution_candidate(raw: dict[str, Any]) -> bool:
    """Return True when a row looks macro/Fed relevant enough to inspect."""
    text = _text_blob(raw)
    if _contains_any(text, EXCLUDE_TERMS):
        return False
    if _contains_any(text, MACRO_TERMS):
        return True
    return bool(_tag_slugs(raw) & MACRO_TAG_SLUGS)


def resolve_market_family(raw: dict[str, Any]) -> PolymarketResolution:
    """Resolve a small allowlisted set of market families.

    Families intentionally supported today:
    - fomc_decision
    - powell_press_conference
    - cut_count
    - year_end_rate
    - unresolved_macro
    - exclude
    """

    text = _text_blob(raw)

    if _contains_any(text, EXCLUDE_TERMS):
        return PolymarketResolution(
            family="exclude",
            is_macro_candidate=False,
            is_fomc_link_candidate=False,
            reason="explicit non-macro federal/legal false positive",
        )

    if _contains_any(text, FOMC_DECISION_PATTERNS):
        return PolymarketResolution(
            family="fomc_decision",
            is_macro_candidate=True,
            is_fomc_link_candidate=True,
            reason="matched allowlisted FOMC decision wording",
        )

    if "powell" in text and _contains_any(text, POWELL_PRESS_PATTERNS):
        return PolymarketResolution(
            family="powell_press_conference",
            is_macro_candidate=True,
            is_fomc_link_candidate=True,
            reason="matched allowlisted Powell press-conference wording",
        )

    if _contains_any(text, CUT_COUNT_PATTERNS):
        return PolymarketResolution(
            family="cut_count",
            is_macro_candidate=True,
            is_fomc_link_candidate=False,
            reason="matched allowlisted cumulative cut-count wording",
        )

    if _contains_any(text, YEAR_END_RATE_PATTERNS):
        return PolymarketResolution(
            family="year_end_rate",
            is_macro_candidate=True,
            is_fomc_link_candidate=False,
            reason="matched allowlisted year-end rate wording",
        )

    if is_macro_resolution_candidate(raw):
        return PolymarketResolution(
            family="unresolved_macro",
            is_macro_candidate=True,
            is_fomc_link_candidate=False,
            reason="macro/Fed candidate but not in a supported resolved family",
        )

    return PolymarketResolution(
        family="exclude",
        is_macro_candidate=False,
        is_fomc_link_candidate=False,
        reason="no supported macro/Fed terms matched",
    )


def suggest_fomc_meeting_id(
    close_time: datetime | None,
    resolution: PolymarketResolution,
    fomc_meeting_ids_by_date: Mapping[date, int],
) -> int | None:
    """Suggest an FOMC meeting id only for exact-date, allowed-family cases."""
    if close_time is None or not resolution.is_fomc_link_candidate:
        return None
    return fomc_meeting_ids_by_date.get(close_time.date())
