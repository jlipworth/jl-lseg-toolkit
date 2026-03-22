"""Tests for Polymarket trade->candlestick orchestration."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.polymarket.extractor import (
    _filter_condition_groups_missing_candles,
    _group_markets_by_condition,
    backfill_candlesticks,
)


def sample_market_rows() -> list[dict]:
    return [
        {
            "id": 101,
            "market_ticker": "POLY:cond-1:token-yes",
            "condition_id": "cond-1",
            "token_id": "token-yes",
            "status": "settled",
            "close_time": datetime(2026, 3, 20, 0, 0, tzinfo=UTC),
            "last_trade_time": datetime(2026, 3, 19, 23, 59, tzinfo=UTC),
        },
        {
            "id": 102,
            "market_ticker": "POLY:cond-1:token-no",
            "condition_id": "cond-1",
            "token_id": "token-no",
            "status": "settled",
            "close_time": datetime(2026, 3, 20, 0, 0, tzinfo=UTC),
            "last_trade_time": datetime(2026, 3, 19, 23, 59, tzinfo=UTC),
        },
        {
            "id": 201,
            "market_ticker": "POLY:cond-2:token-a",
            "condition_id": "cond-2",
            "token_id": "token-a",
            "status": "settled",
            "close_time": datetime(2026, 3, 21, 0, 0, tzinfo=UTC),
            "last_trade_time": None,
        },
    ]


class TestGroupingHelpers:
    def test_group_markets_by_condition(self):
        grouped = _group_markets_by_condition(sample_market_rows())
        assert sorted(grouped) == ["cond-1", "cond-2"]
        assert [row["id"] for row in grouped["cond-1"]] == [101, 102]

    def test_filter_condition_groups_missing_candles(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [{"market_id": 101}, {"market_id": 102}]

        grouped = _group_markets_by_condition(sample_market_rows())
        filtered = _filter_condition_groups_missing_candles(conn, grouped)

        assert list(filtered) == ["cond-2"]


class TestBackfillCandlesticks:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.upsert_candlesticks"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.get_condition_trades"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor._get_polymarket_markets_for_candles"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.seed_polymarket_platform"
    )
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.PolymarketClient"
    )
    def test_backfill_candlesticks_derives_and_upserts(
        self,
        mock_client_cls,
        mock_seed_platform,
        mock_get_markets,
        mock_get_condition_trades,
        mock_upsert_candlesticks,
    ):
        mock_client_cls.return_value = MagicMock()
        mock_seed_platform.return_value = 2
        mock_get_markets.return_value = sample_market_rows()[:2]
        mock_get_condition_trades.return_value = [
            MagicMock(
                token_id="token-yes",
                timestamp=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
                price=0.40,
                size=10.0,
                transaction_hash="0x1",
            ),
            MagicMock(
                token_id="token-no",
                timestamp=datetime(2026, 3, 20, 10, 5, tzinfo=UTC),
                price=0.60,
                size=12.0,
                transaction_hash="0x2",
            ),
        ]
        mock_upsert_candlesticks.return_value = 2

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []

        summary = backfill_candlesticks(conn, max_pages_per_condition=3)

        assert summary["conditions"] == 1
        assert summary["markets"] == 2
        assert summary["candlesticks"] == 2
        mock_get_condition_trades.assert_called_once()
        _, kwargs = mock_get_condition_trades.call_args
        assert kwargs["condition_id"] == "cond-1"
        assert kwargs["max_pages"] == 3
        mock_upsert_candlesticks.assert_called_once()
        conn.commit.assert_called_once()
