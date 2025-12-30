"""Tests for data processing utilities."""

import pandas as pd

from lseg_toolkit.data import DataProcessor


class TestDataProcessor:
    """Test cases for DataProcessor."""

    def test_calculate_yoy_growth(self):
        """Test YoY growth calculation."""
        current = pd.Series([110, 120, 100])
        prior = pd.Series([100, 100, 100])
        expected = pd.Series([10.0, 20.0, 0.0])

        result = DataProcessor.calculate_yoy_growth(current, prior)
        pd.testing.assert_series_equal(result, expected)

    def test_format_market_cap(self):
        """Test market cap formatting to millions."""
        values = pd.Series([1_000_000_000, 500_000_000, 2_500_000_000])
        expected = pd.Series([1000.0, 500.0, 2500.0])

        result = DataProcessor.format_market_cap(values)
        pd.testing.assert_series_equal(result, expected)

    # TODO: Add tests for:
    # - convert_timezone
    # - aggregate_by_sector
