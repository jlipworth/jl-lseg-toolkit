"""Tests for Polymarket trade normalization and aggregation helpers."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import httpx

from lseg_toolkit.timeseries.prediction_markets.polymarket.trades import (
    aggregate_daily_candles,
    get_condition_trades,
    get_last_trade_times_by_token,
    parse_trade,
)


def sample_trade(
    *,
    asset: str = "token-yes",
    price: float = 0.42,
    size: float = 10.0,
    timestamp: int | str = 1774133887,
    tx: str = "0xabc",
) -> dict:
    return {
        "asset": asset,
        "conditionId": "cond-1",
        "price": price,
        "size": size,
        "timestamp": timestamp,
        "side": "BUY",
        "outcome": "Yes" if asset == "token-yes" else "No",
        "transactionHash": tx,
    }


class TestParseTrade:
    def test_parse_trade_from_unix_timestamp(self):
        trade = parse_trade(sample_trade())
        assert trade.condition_id == "cond-1"
        assert trade.token_id == "token-yes"
        assert trade.timestamp == datetime.fromtimestamp(1774133887, tz=UTC)

    def test_parse_trade_from_iso_timestamp(self):
        trade = parse_trade(sample_trade(timestamp="2026-03-21T16:18:07Z"))
        assert trade.timestamp == datetime(2026, 3, 21, 16, 18, 7, tzinfo=UTC)


class TestConditionTradeFetch:
    def test_get_condition_trades_uses_offset_pagination(self):
        client = MagicMock()
        client.get_trades.side_effect = [
            [
                sample_trade(timestamp=1774133887, tx="0x1"),
                sample_trade(asset="token-no", timestamp=1774133880, tx="0x2"),
            ],
            [sample_trade(timestamp=1774133870, tx="0x3")],
        ]

        trades = get_condition_trades(client, condition_id="cond-1", limit=2)

        assert len(trades) == 3
        assert client.get_trades.call_args_list[0].kwargs == {
            "limit": 2,
            "offset": 0,
            "market": "cond-1",
        }
        assert client.get_trades.call_args_list[1].kwargs == {
            "limit": 2,
            "offset": 2,
            "market": "cond-1",
        }

    def test_get_last_trade_times_by_token_stops_when_all_seen(self):
        client = MagicMock()
        client.get_trades.side_effect = [
            [sample_trade(asset="token-yes", timestamp=1774133887, tx="0x1")],
            [sample_trade(asset="token-no", timestamp=1774133800, tx="0x2")],
        ]

        latest = get_last_trade_times_by_token(
            client,
            condition_id="cond-1",
            token_ids=["token-yes", "token-no"],
            limit=1,
            max_pages=5,
        )

        assert latest["token-yes"] == datetime.fromtimestamp(1774133887, tz=UTC)
        assert latest["token-no"] == datetime.fromtimestamp(1774133800, tz=UTC)
        assert client.get_trades.call_count == 2

    def test_get_condition_trades_tolerates_deep_offset_400(self):
        client = MagicMock()
        request = httpx.Request("GET", "https://data-api.polymarket.com/trades")
        response = httpx.Response(400, request=request)
        client.get_trades.side_effect = [
            [sample_trade(timestamp=1774133887, tx="0x1")],
            httpx.HTTPStatusError("bad request", request=request, response=response),
        ]

        trades = get_condition_trades(client, condition_id="cond-1", limit=1)

        assert len(trades) == 1
        assert client.get_trades.call_count == 2

    def test_get_condition_trades_raises_initial_400(self):
        client = MagicMock()
        request = httpx.Request("GET", "https://data-api.polymarket.com/trades")
        response = httpx.Response(400, request=request)
        client.get_trades.side_effect = httpx.HTTPStatusError(
            "bad request",
            request=request,
            response=response,
        )

        try:
            get_condition_trades(client, condition_id="cond-1", limit=1)
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 400
        else:
            raise AssertionError("Expected HTTPStatusError on initial page")

    def test_get_last_trade_times_by_token_tolerates_deep_offset_400(self):
        client = MagicMock()
        request = httpx.Request("GET", "https://data-api.polymarket.com/trades")
        response = httpx.Response(400, request=request)
        client.get_trades.side_effect = [
            [sample_trade(asset="token-yes", timestamp=1774133887, tx="0x1")],
            httpx.HTTPStatusError("bad request", request=request, response=response),
        ]

        latest = get_last_trade_times_by_token(
            client,
            condition_id="cond-1",
            token_ids=["token-yes", "token-no"],
            limit=1,
            max_pages=5,
        )

        assert latest["token-yes"] == datetime.fromtimestamp(1774133887, tz=UTC)
        assert latest["token-no"] is None


class TestDailyAggregation:
    def test_aggregate_daily_candles(self):
        trades = [
            parse_trade(
                sample_trade(
                    asset="token-yes",
                    price=0.40,
                    size=10.0,
                    timestamp="2026-03-20T15:00:00Z",
                    tx="0x1",
                )
            ),
            parse_trade(
                sample_trade(
                    asset="token-yes",
                    price=0.50,
                    size=20.0,
                    timestamp="2026-03-20T16:00:00Z",
                    tx="0x2",
                )
            ),
            parse_trade(
                sample_trade(
                    asset="token-yes",
                    price=0.45,
                    size=5.0,
                    timestamp="2026-03-21T14:00:00Z",
                    tx="0x3",
                )
            ),
            parse_trade(
                sample_trade(
                    asset="token-no",
                    price=0.55,
                    size=7.0,
                    timestamp="2026-03-20T16:30:00Z",
                    tx="0x4",
                )
            ),
        ]

        candles = aggregate_daily_candles(trades, market_id=101, token_id="token-yes")

        assert len(candles) == 2

        first = candles[0]
        assert first.market_id == 101
        assert first.ts == datetime(2026, 3, 20, 0, 0, tzinfo=UTC)
        assert first.price_open == 0.40
        assert first.price_high == 0.50
        assert first.price_low == 0.40
        assert first.price_close == 0.50
        assert round(first.price_mean or 0, 6) == round((0.4 * 10 + 0.5 * 20) / 30, 6)
        assert first.volume == 30

        second = candles[1]
        assert second.ts == datetime(2026, 3, 21, 0, 0, tzinfo=UTC)
        assert second.price_open == 0.45
        assert second.price_close == 0.45
        assert second.volume == 5
