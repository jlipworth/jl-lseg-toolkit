"""
Prediction markets data module.

Provides tools for fetching and storing prediction market data (Kalshi),
linking to FOMC meetings, and reconstructing implied probability distributions.

Usage:
    from lseg_toolkit.timeseries.prediction_markets import (
        # Models
        Platform, Series, Market, Candlestick,
        # Schema
        init_pm_schema, seed_kalshi_platform, seed_polymarket_platform,
        # Storage
        upsert_series, upsert_market, upsert_candlestick, upsert_candlesticks,
        get_platform_by_name, get_markets_by_series, get_markets_by_event,
        get_candlesticks,
        # Analysis
        rate_distribution, implied_rate, compare_distributions,
    )

    from lseg_toolkit.timeseries.prediction_markets.kalshi import (
        KalshiClient, backfill, daily_refresh,
    )
"""

from lseg_toolkit.timeseries.prediction_markets.analysis.comparison import (
    compare_markets_to_fedwatch,
)
from lseg_toolkit.timeseries.prediction_markets.analysis.probability import (
    compare_distributions,
    implied_rate,
    rate_distribution,
)
from lseg_toolkit.timeseries.prediction_markets.fedwatch.loader import (
    build_distribution,
    load_fedwatch_probabilities,
    normalize_fedwatch_frame,
)
from lseg_toolkit.timeseries.prediction_markets.models import (
    Candlestick,
    Market,
    Platform,
    Series,
)
from lseg_toolkit.timeseries.prediction_markets.schema import (
    init_pm_schema,
    seed_kalshi_platform,
    seed_polymarket_platform,
)
from lseg_toolkit.timeseries.prediction_markets.storage import (
    get_candlesticks,
    get_markets_by_event,
    get_markets_by_series,
    get_platform_by_name,
    upsert_candlestick,
    upsert_candlesticks,
    upsert_market,
    upsert_series,
)

__all__ = [
    # Models
    "Candlestick",
    "Market",
    "Platform",
    "Series",
    # Schema
    "init_pm_schema",
    "seed_kalshi_platform",
    "seed_polymarket_platform",
    # Storage
    "get_candlesticks",
    "get_markets_by_event",
    "get_markets_by_series",
    "get_platform_by_name",
    "upsert_candlestick",
    "upsert_candlesticks",
    "upsert_market",
    "upsert_series",
    # Analysis
    "compare_distributions",
    "compare_markets_to_fedwatch",
    "implied_rate",
    "rate_distribution",
    # FedWatch
    "build_distribution",
    "load_fedwatch_probabilities",
    "normalize_fedwatch_frame",
]
