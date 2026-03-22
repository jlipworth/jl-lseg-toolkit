"""Tests for opt-in higher-level Polymarket workflows."""

from unittest.mock import MagicMock, patch

from lseg_toolkit.timeseries.prediction_markets.polymarket.extractor import (
    backfill_with_candlesticks,
)


class TestBackfillWithCandlesticks:
    @patch(
        "lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.backfill_candlesticks"
    )
    @patch("lseg_toolkit.timeseries.prediction_markets.polymarket.extractor.backfill")
    def test_runs_metadata_then_candles(self, mock_backfill, mock_backfill_candles):
        mock_backfill.return_value = {"platform_id": 2, "markets": 12, "series": 4}
        mock_backfill_candles.return_value = {
            "platform_id": 2,
            "conditions": 3,
            "markets": 6,
            "candlesticks": 42,
        }

        conn = MagicMock()
        summary = backfill_with_candlesticks(
            conn,
            metadata_max_pages=5,
            candle_status="settled",
            missing_only=False,
            trade_limit=500,
            max_pages_per_condition=7,
        )

        mock_backfill.assert_called_once_with(conn, max_pages=5)
        mock_backfill_candles.assert_called_once_with(
            conn,
            status="settled",
            missing_only=False,
            trade_limit=500,
            max_pages_per_condition=7,
        )
        assert summary["platform_id"] == 2
        assert summary["markets"]["markets"] == 12
        assert summary["candlesticks"]["candlesticks"] == 42
