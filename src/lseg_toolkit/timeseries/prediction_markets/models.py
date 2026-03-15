"""Pydantic models for prediction market data."""

from datetime import datetime

from pydantic import BaseModel


class Platform(BaseModel):
    """Prediction market platform (e.g., Kalshi, Polymarket)."""

    id: int | None = None
    name: str
    display_name: str
    api_base_url: str
    is_regulated: bool = False
    currency: str = "USD"


class Series(BaseModel):
    """Group of related markets (e.g., KXFED, KXFEDDECISION)."""

    id: int | None = None
    platform_id: int
    series_ticker: str
    title: str
    category: str = "economics"
    created_at: datetime | None = None


class Market(BaseModel):
    """Individual prediction market contract."""

    id: int | None = None
    platform_id: int
    series_id: int | None = None
    market_ticker: str
    platform_market_id: str
    event_ticker: str | None = None
    title: str
    subtitle: str | None = None
    strike_value: float | None = None
    open_time: datetime | None = None
    close_time: datetime | None = None
    status: str = "active"
    result: str | None = None
    last_price: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    fomc_meeting_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Candlestick(BaseModel):
    """Daily OHLC candlestick for a market."""

    market_id: int
    ts: datetime
    price_open: float | None = None
    price_high: float | None = None
    price_low: float | None = None
    price_close: float | None = None
    price_mean: float | None = None
    yes_bid_close: float | None = None
    yes_ask_close: float | None = None
    volume: int | None = None
    open_interest: int | None = None
