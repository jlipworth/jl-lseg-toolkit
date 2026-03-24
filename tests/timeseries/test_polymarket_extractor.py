"""Tests for Polymarket extractor/orchestrator."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.polymarket.extractor import (
    FED_DISCOVERY_QUERIES,
    backfill,
    backfill_fed_discovery,
    build_market_ticker,
    cleanup_stale_active_statuses,
    daily_refresh,
    discover_fed_event_summaries,
    discover_fed_events,
    discover_fed_markets,
    extract_event_markets,
    is_fed_discovery_match,
    parse_series,
    parse_token_markets,
)


def sample_gamma_market() -> dict:
    return {
        "question": "Will the Fed cut in September?",
        "conditionId": "cond-1",
        "slug": "will-the-fed-cut-in-september",
        "startDate": "2026-03-01T12:00:00Z",
        "endDate": "2026-09-16T18:00:00Z",
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '["0.42", "0.58"]',
        "clobTokenIds": '["token-yes", "token-no"]',
        "volume": 17745616.79,
        "volumeNum": 17745617,
        "active": True,
        "closed": False,
        "archived": False,
        "events": [
            {
                "slug": "fed-september-2026-decision",
                "title": "Fed September 2026 Decision",
            }
        ],
    }


class TestTickerHelpers:
    def test_build_market_ticker(self):
        assert build_market_ticker("cond-1", "token-1") == "POLY:cond-1:token-1"


class TestParseSeries:
    def test_parse_series_uses_event_slug(self):
        series = parse_series(sample_gamma_market(), platform_id=2)
        assert series.series_ticker == "fed-september-2026-decision"
        assert series.title == "Fed September 2026 Decision"
        assert series.category == "prediction_markets"


class TestParseTokenMarkets:
    def test_parse_token_markets_creates_one_row_per_outcome(self):
        markets = parse_token_markets(
            sample_gamma_market(), platform_id=2, series_id=10
        )

        assert len(markets) == 2
        assert markets[0].market_ticker == "POLY:cond-1:token-yes"
        assert markets[0].platform_market_id == "token-yes"
        assert markets[0].condition_id == "cond-1"
        assert markets[0].event_ticker == "cond-1"
        assert markets[0].outcome_label == "Yes"
        assert markets[0].subtitle == "Yes"
        assert markets[0].event_slug == "fed-september-2026-decision"
        assert markets[0].question_slug == "will-the-fed-cut-in-september"
        assert markets[0].last_price == 0.42
        assert markets[0].volume == 17745617
        assert markets[0].status == "active"

    def test_parse_token_markets_parses_timestamps(self):
        markets = parse_token_markets(
            sample_gamma_market(), platform_id=2, series_id=10
        )
        assert markets[0].open_time == datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
        assert markets[0].close_time == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)

    def test_parse_token_markets_closed_beats_active_for_status(self):
        raw = sample_gamma_market() | {"active": True, "closed": True}
        markets = parse_token_markets(raw, platform_id=2, series_id=10)
        assert all(m.status == "closed" for m in markets)

    def test_parse_token_markets_rounds_volume_from_volume_when_volume_num_missing(
        self,
    ):
        raw = sample_gamma_market()
        raw.pop("volumeNum")
        raw["volume"] = 123.6

        markets = parse_token_markets(raw, platform_id=2, series_id=10)

        assert all(m.volume == 124 for m in markets)


def sample_fed_event() -> dict:
    return {
        "id": "75478",
        "slug": "fed-decision-in-april",
        "title": "Fed decision in April?",
        "description": "The Federal Open Market Committee (FOMC) sets the federal funds rate.",
        "startDate": "2025-11-13T00:40:50.267805Z",
        "endDate": "2026-04-29T00:00:00Z",
        "volume": 17745616.79,
        "volume24hr": 1733990.25,
        "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
        "markets": [sample_gamma_market()],
    }


class TestDiscoveryHelpers:
    def test_is_fed_discovery_match_true_for_fomc_event(self):
        assert is_fed_discovery_match(sample_fed_event()) is True

    def test_is_fed_discovery_match_false_for_federal_charge(self):
        raw = {
            "slug": "will-trump-face-a-federal-charge",
            "title": "Will Trump face a federal charge?",
            "description": "This market resolves based on a federal criminal charge.",
            "tags": [],
            "markets": [],
        }
        assert is_fed_discovery_match(raw) is False

    def test_extract_event_markets_attaches_event_context(self):
        markets = extract_event_markets([sample_fed_event()])
        assert len(markets) == 1
        assert markets[0]["events"][0]["slug"] == "fed-decision-in-april"
        assert markets[0]["conditionId"] == "cond-1"


class TestDiscovery:
    def test_default_discovery_queries_match_curated_macro_rates_seed_list(self):
        assert FED_DISCOVERY_QUERIES == (
            "fed",
            "fomc",
            "federal reserve",
            "rate cut",
            "interest rate",
            "fed funds",
            "powell",
            "cpi",
            "inflation",
            "recession",
        )

    def test_discover_fed_events_dedupes_search_and_tag_expansion(self):
        client = MagicMock()
        client.search_public.side_effect = [
            {
                "events": [sample_fed_event()],
                "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
            },
            {
                "events": [sample_fed_event()],
                "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
            },
        ]
        client.list_tags.return_value = [{"id": 159, "slug": "fed", "label": "Fed"}]
        client.list_events.return_value = [sample_fed_event()]

        events = discover_fed_events(
            client=client,
            queries=("fed decision", "fomc"),
            limit_per_type=5,
            max_event_pages=1,
            active=True,
            closed=False,
        )

        assert len(events) == 1
        assert events[0]["slug"] == "fed-decision-in-april"
        client.list_events.assert_called_once_with(
            tag_id=159,
            related_tags=True,
            active=True,
            closed=False,
            order="volume",
            ascending=False,
            max_pages=1,
        )

    def test_discover_fed_markets_returns_nested_market_rows(self):
        client = MagicMock()
        client.search_public.return_value = {
            "events": [sample_fed_event()],
            "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
        }
        client.list_tags.return_value = []
        client.list_events.return_value = []

        markets = discover_fed_markets(
            client=client,
            queries=("fed decision",),
            limit_per_type=5,
            max_event_pages=1,
        )

        assert len(markets) == 1
        assert markets[0]["events"][0]["slug"] == "fed-decision-in-april"
        assert markets[0]["conditionId"] == "cond-1"

    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.get_fomc_meetings"
    )
    def test_discover_fed_event_summaries_adds_resolution_and_fomc_suggestion(
        self,
        mock_get_fomc_meetings,
    ):
        client = MagicMock()
        client.search_public.return_value = {
            "events": [sample_fed_event()],
            "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
        }
        client.list_tags.return_value = []
        client.list_events.return_value = []
        mock_get_fomc_meetings.return_value = [
            {"id": 1149, "meeting_date": datetime(2026, 4, 29, tzinfo=UTC).date()}
        ]

        summaries = discover_fed_event_summaries(
            conn=MagicMock(),
            client=client,
            queries=("fed decision",),
            limit_per_type=5,
            max_event_pages=1,
        )

        assert len(summaries) == 1
        assert summaries[0]["event_slug"] == "fed-decision-in-april"
        assert summaries[0]["family"] == "fomc_decision"
        assert summaries[0]["suggested_fomc_meeting_id"] == 1149


class TestBackfill:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.PolymarketClient"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_market"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_series"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.seed_polymarket_platform"
    )
    def test_backfill_seeds_platform_and_upserts_markets(
        self,
        mock_seed_platform,
        mock_upsert_series,
        mock_upsert_market,
        mock_client_cls,
    ):
        mock_seed_platform.return_value = 2
        mock_upsert_series.return_value = 10
        mock_upsert_market.side_effect = [101, 102]

        mock_client = MagicMock()
        mock_client.list_markets.return_value = [sample_gamma_market()]
        mock_client_cls.return_value = mock_client

        mock_conn = MagicMock()

        summary = backfill(mock_conn, max_pages=1)

        assert summary["platform_id"] == 2
        assert summary["series"] == 1
        assert summary["markets"] == 2
        mock_client.list_markets.assert_called_once_with(max_pages=1)
        assert mock_upsert_market.call_count == 2
        mock_conn.commit.assert_called_once()


class TestDailyRefresh:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.PolymarketClient"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_market"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_series"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.seed_polymarket_platform"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.get_last_trade_times_by_token"
    )
    def test_daily_refresh_populates_last_trade_time(
        self,
        mock_last_trade_times,
        mock_seed_platform,
        mock_upsert_series,
        mock_upsert_market,
        mock_client_cls,
    ):
        mock_seed_platform.return_value = 2
        mock_upsert_series.return_value = 10
        mock_upsert_market.side_effect = [101, 102]

        trade_ts = datetime(2026, 3, 21, 16, 11, 2, tzinfo=UTC)
        mock_last_trade_times.return_value = {
            "token-yes": trade_ts,
            "token-no": None,
        }
        mock_client = MagicMock()
        mock_client.list_markets.return_value = [sample_gamma_market()]
        mock_client.list_simplified_markets.return_value = []
        mock_client_cls.return_value = mock_client

        mock_conn = MagicMock()

        summary = daily_refresh(mock_conn, max_pages=1)

        assert summary["markets"] == 2
        mock_client.list_markets.assert_called_once_with(
            closed=False,
            active=True,
            max_pages=1,
        )
        first_market = mock_upsert_market.call_args_list[0][0][1]
        assert first_market.last_trade_time == trade_ts
        second_market = mock_upsert_market.call_args_list[1][0][1]
        assert second_market.last_trade_time is None
        mock_conn.commit.assert_called_once()


class TestFedDiscoveryBackfill:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.PolymarketClient"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_market"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_series"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.seed_polymarket_platform"
    )
    def test_backfill_fed_discovery(
        self,
        mock_seed_platform,
        mock_upsert_series,
        mock_upsert_market,
        mock_client_cls,
    ):
        mock_seed_platform.return_value = 2
        mock_upsert_series.return_value = 10
        mock_upsert_market.side_effect = [101, 102]

        mock_client = MagicMock()
        mock_client.search_public.return_value = {
            "events": [sample_fed_event()],
            "tags": [{"id": 159, "slug": "fed", "label": "Fed"}],
        }
        mock_client.list_tags.return_value = [
            {"id": 159, "slug": "fed", "label": "Fed"}
        ]
        mock_client.list_events.return_value = []
        mock_client_cls.return_value = mock_client

        mock_conn = MagicMock()

        summary = backfill_fed_discovery(
            mock_conn,
            queries=("fed decision",),
            limit_per_type=5,
            max_event_pages=1,
            active=True,
            closed=False,
        )

        assert summary["platform_id"] == 2
        assert summary["series"] == 1
        assert summary["markets"] == 2
        mock_conn.commit.assert_called_once()


class TestCleanupStaleActiveStatuses:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.seed_polymarket_platform"
    )
    def test_cleanup_marks_past_close_active_rows_closed_or_settled(
        self,
        mock_seed_platform,
    ):
        mock_seed_platform.return_value = 2
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"count": 7}

        summary = cleanup_stale_active_statuses(mock_conn)

        assert summary["updated_markets"] == 7
        assert mock_cursor.execute.call_count == 2
        sql = mock_cursor.execute.call_args_list[1][0][0]
        assert "UPDATE pm_markets" in sql
        assert "status = CASE" in sql
        mock_conn.commit.assert_called_once()
