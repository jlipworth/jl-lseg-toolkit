"""Polymarket public market-data integration."""

from lseg_toolkit.timeseries.prediction_markets.polymarket.client import (
    PolymarketClient,
)
from lseg_toolkit.timeseries.prediction_markets.polymarket.extractor import (
    backfill,
    backfill_fed_discovery,
    build_market_ticker,
    daily_refresh,
    discover_fed_event_summaries,
    discover_fed_events,
    discover_fed_markets,
    extract_event_markets,
    is_fed_discovery_match,
    normalize_status,
    parse_market_tokens,
    parse_markets,
    parse_series,
    parse_token_markets,
)
from lseg_toolkit.timeseries.prediction_markets.polymarket.resolution import (
    PolymarketResolution,
    is_macro_resolution_candidate,
    resolve_market_family,
    suggest_fomc_meeting_id,
)

__all__ = [
    "PolymarketClient",
    "backfill",
    "backfill_fed_discovery",
    "build_market_ticker",
    "daily_refresh",
    "discover_fed_event_summaries",
    "discover_fed_events",
    "discover_fed_markets",
    "extract_event_markets",
    "is_fed_discovery_match",
    "normalize_status",
    "parse_markets",
    "parse_market_tokens",
    "parse_token_markets",
    "parse_series",
    "PolymarketResolution",
    "is_macro_resolution_candidate",
    "resolve_market_family",
    "suggest_fomc_meeting_id",
]
