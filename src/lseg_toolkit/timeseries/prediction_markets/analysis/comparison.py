"""Comparison helpers for Kalshi/PM distributions versus FedWatch."""

from __future__ import annotations

import pandas as pd

from lseg_toolkit.timeseries.prediction_markets.analysis.probability import (
    compare_distributions,
    rate_distribution,
)
from lseg_toolkit.timeseries.prediction_markets.fedwatch.loader import (
    build_distribution,
)
from lseg_toolkit.timeseries.prediction_markets.models import Market


def compare_markets_to_fedwatch(
    markets: list[Market],
    fedwatch_df: pd.DataFrame,
    *,
    meeting_date: str | None = None,
    as_of_date: str | None = None,
) -> dict | None:
    """
    Compare a Kalshi strike ladder to a FedWatch distribution.

    Returns the generic comparison metrics plus the normalized distributions used.
    """
    pm_dist = rate_distribution(markets)
    fedwatch_dist = build_distribution(
        fedwatch_df,
        meeting_date=meeting_date,
        as_of_date=as_of_date,
    )
    metrics = compare_distributions(pm_dist, fedwatch_dist)
    if metrics is None:
        return None
    return {
        **metrics,
        "pm_dist": pm_dist,
        "fedwatch_dist": fedwatch_dist,
    }
