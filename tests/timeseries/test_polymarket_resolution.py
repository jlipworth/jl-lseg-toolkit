"""Tests for conservative Polymarket market-family resolution helpers."""

from datetime import datetime

from lseg_toolkit.timeseries.prediction_markets.polymarket.resolution import (
    is_macro_resolution_candidate,
    resolve_market_family,
    suggest_fomc_meeting_id,
)


def _raw(
    *,
    slug: str,
    title: str,
    description: str = "",
    tags: list[dict] | None = None,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "tags": tags or [],
        "markets": [],
    }


class TestResolveMarketFamily:
    def test_resolves_fomc_decision(self):
        raw = _raw(
            slug="fed-decision-in-april",
            title="Fed decision in April?",
            description="FOMC decision market for the April meeting.",
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "fomc_decision"
        assert resolution.is_fomc_link_candidate is True

    def test_resolves_powell_press_conference(self):
        raw = _raw(
            slug="what-will-powell-say-during-march-press-conference",
            title="What will Powell say during March press conference?",
            description="Powell press conference market after the FOMC meeting.",
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "powell_press_conference"
        assert resolution.is_fomc_link_candidate is True

    def test_resolves_cut_count(self):
        raw = _raw(
            slug="how-many-fed-rate-cuts-in-2026",
            title="How many Fed rate cuts in 2026?",
            description="Cumulative number of rate cuts by year-end.",
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "cut_count"
        assert resolution.is_fomc_link_candidate is False

    def test_resolves_year_end_rate(self):
        raw = _raw(
            slug="what-will-the-fed-rate-be-at-the-end-of-2026",
            title="What will the fed rate be at the end of 2026?",
            description="Year-end fed funds rate bucket market.",
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "year_end_rate"
        assert resolution.is_fomc_link_candidate is False

    def test_marks_cpi_as_unresolved_macro(self):
        raw = _raw(
            slug="will-cpi-be-above-3-percent",
            title="Will CPI be above 3% this month?",
            description="Inflation threshold market.",
            tags=[{"slug": "inflation", "label": "Inflation"}],
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "unresolved_macro"
        assert resolution.is_macro_candidate is True

    def test_excludes_federal_charge_false_positive(self):
        raw = _raw(
            slug="will-trump-face-a-federal-charge",
            title="Will Trump face a federal charge?",
            description="This resolves on a federal criminal charge.",
        )

        resolution = resolve_market_family(raw)

        assert resolution.family == "exclude"
        assert resolution.is_macro_candidate is False


class TestMacroResolutionCandidate:
    def test_true_for_macro_tag(self):
        raw = _raw(
            slug="unclear-slug",
            title="Completely generic title",
            tags=[{"slug": "macro", "label": "Macro"}],
        )

        assert is_macro_resolution_candidate(raw) is True

    def test_false_for_non_macro_text(self):
        raw = _raw(
            slug="will-team-a-win",
            title="Will Team A win tonight?",
            description="Sports market.",
        )

        assert is_macro_resolution_candidate(raw) is False


class TestSuggestFomcMeetingId:
    def test_exact_match_for_linkable_family(self):
        raw = _raw(
            slug="fed-decision-in-april",
            title="Fed decision in April?",
        )
        resolution = resolve_market_family(raw)

        meeting_id = suggest_fomc_meeting_id(
            datetime.fromisoformat("2026-04-29T00:00:00+00:00"),
            resolution,
            {datetime(2026, 4, 29).date(): 1149},
        )

        assert meeting_id == 1149

    def test_none_for_non_linkable_family(self):
        raw = _raw(
            slug="how-many-fed-rate-cuts-in-2026",
            title="How many Fed rate cuts in 2026?",
        )
        resolution = resolve_market_family(raw)

        meeting_id = suggest_fomc_meeting_id(
            datetime.fromisoformat("2026-12-31T00:00:00+00:00"),
            resolution,
            {datetime(2026, 12, 31).date(): 9999},
        )

        assert meeting_id is None
