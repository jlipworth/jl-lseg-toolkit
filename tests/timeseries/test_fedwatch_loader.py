"""Tests for FedWatch loading and comparison helpers."""

from datetime import date

import pandas as pd

from lseg_toolkit.timeseries.prediction_markets.analysis.comparison import (
    compare_markets_to_fedwatch,
)
from lseg_toolkit.timeseries.prediction_markets.fedwatch.loader import (
    build_distribution,
    load_fedwatch_probabilities,
    normalize_fedwatch_frame,
)
from lseg_toolkit.timeseries.prediction_markets.models import Market


class TestFedWatchLoader:
    def test_normalizes_long_format(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-03-14", "2026-03-14"],
                "Meeting Date": ["2026-03-18", "2026-03-18"],
                "Target Range": ["4.25-4.50", "4.50-4.75"],
                "Probability": [75.0, 25.0],
            }
        )

        result = normalize_fedwatch_frame(df)

        assert list(result.columns) == [
            "as_of_date",
            "meeting_date",
            "rate_bucket",
            "probability",
        ]
        assert result["as_of_date"].tolist() == [date(2026, 3, 14), date(2026, 3, 14)]
        assert result["probability"].tolist() == [0.75, 0.25]

    def test_normalizes_wide_format(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-03-14"],
                "4.25-4.50": [60.0],
                "4.50-4.75": [40.0],
            }
        )

        result = normalize_fedwatch_frame(df, meeting_date="2026-03-18")

        assert result["meeting_date"].tolist() == [date(2026, 3, 18), date(2026, 3, 18)]
        assert set(result["rate_bucket"]) == {"4.25-4.50", "4.50-4.75"}

    def test_loads_csv_file(self, tmp_path):
        path = tmp_path / "fedwatch.csv"
        pd.DataFrame(
            {
                "Date": ["2026-03-14"],
                "Meeting Date": ["2026-03-18"],
                "Target Range": ["4.25-4.50"],
                "Probability": [100.0],
            }
        ).to_csv(path, index=False)

        result = load_fedwatch_probabilities(path)

        assert len(result) == 1
        assert result.iloc[0]["probability"] == 1.0

    def test_build_distribution_filters_by_meeting_and_as_of(self):
        df = pd.DataFrame(
            {
                "as_of_date": [date(2026, 3, 14), date(2026, 3, 14)],
                "meeting_date": [date(2026, 3, 18), date(2026, 3, 18)],
                "rate_bucket": ["4.25-4.50", "4.50-4.75"],
                "probability": [0.6, 0.4],
            }
        )

        dist = build_distribution(
            df,
            meeting_date="2026-03-18",
            as_of_date="2026-03-14",
        )

        assert dist == {"4.25-4.50": 0.6, "4.50-4.75": 0.4}


class TestFedWatchComparison:
    def test_compare_markets_to_fedwatch(self):
        markets = [
            Market(
                platform_id=1,
                series_id=1,
                market_ticker="KXFED-26MAR-T4.25",
                platform_market_id="KXFED-26MAR-T4.25",
                title="Rate > 4.25",
                strike_value=4.25,
                last_price=0.40,
            ),
            Market(
                platform_id=1,
                series_id=1,
                market_ticker="KXFED-26MAR-T4.50",
                platform_market_id="KXFED-26MAR-T4.50",
                title="Rate > 4.50",
                strike_value=4.50,
                last_price=0.10,
            ),
        ]
        fedwatch_df = pd.DataFrame(
            {
                "as_of_date": [date(2026, 3, 14), date(2026, 3, 14)],
                "meeting_date": [date(2026, 3, 18), date(2026, 3, 18)],
                "rate_bucket": ["4.25-4.50", "4.50-4.75"],
                "probability": [0.7, 0.3],
            }
        )

        result = compare_markets_to_fedwatch(
            markets,
            fedwatch_df,
            meeting_date="2026-03-18",
            as_of_date="2026-03-14",
        )

        assert result is not None
        assert "brier_score" in result
        assert "pm_dist" in result
        assert "fedwatch_dist" in result
