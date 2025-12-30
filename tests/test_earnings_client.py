"""
Unit tests for earnings data retrieval functionality in LsegClient.

These tests use the REAL LSEG API and require:
- LSEG Workspace Desktop running and logged in
- Active network connection
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lseg_toolkit.client import LsegClient
from lseg_toolkit.exceptions import DataRetrievalError


class TestEarningsData:
    """Test earnings data retrieval."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_get_earnings_data_basic(self, client):
        """Test basic earnings data retrieval with date range."""
        # Test with a few well-known tickers
        tickers = ["AAPL.O", "MSFT.O", "GOOGL.O"]

        # Use a wide date range to ensure we get earnings for all companies
        # Looking 90 days back and 90 days forward (6 months total)
        from datetime import datetime, timedelta

        today = datetime.now()
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

        df = client.get_earnings_data(tickers, start_date=start_date, end_date=end_date)

        # Should return a DataFrame
        assert isinstance(df, pd.DataFrame)

        # Should have expected columns
        expected_columns = [
            "Instrument",
            "Company Common Name",
            "Event Start Date",
            "Event Start Time",
            "Event Start Date Time",
            "Company Event Type",
            "Event Title",
        ]

        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

        # Should have at least one earnings event (may not be all 3 if outside earnings season)
        assert (
            len(df) > 0
        ), f"No earnings found in date range {start_date} to {end_date}"

        # All event types should be EarningsReleases
        if len(df) > 0:
            assert (df["Company Event Type"] == "EarningsReleases").all()

    def test_get_earnings_data_with_date_filter(self, client):
        """Test earnings data retrieval with date filtering."""
        # Get S&P 500 sample
        rics = client.get_index_constituents("SPX")
        sample_rics = rics[:50]

        # Get next 7 days
        today = datetime.now()
        start_date = today.strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

        df = client.get_earnings_data(
            sample_rics, start_date=start_date, end_date=end_date
        )

        # Should return a DataFrame
        assert isinstance(df, pd.DataFrame)

        # If there are earnings in this period
        if len(df) > 0:
            # All dates should be within range
            df_dates = pd.to_datetime(df["Event Start Date"])
            assert df_dates.min() >= pd.to_datetime(start_date)
            assert df_dates.max() <= pd.to_datetime(end_date)

    def test_get_earnings_data_empty_result(self, client):
        """Test that empty results are handled properly."""
        # Use a date range far in the past
        df = client.get_earnings_data(
            ["AAPL.O"], start_date="2020-01-01", end_date="2020-01-02"
        )

        # Should return empty DataFrame (or very few results)
        assert isinstance(df, pd.DataFrame)

    def test_earnings_times_format(self, client):
        """Test that earnings times are in expected format."""
        tickers = ["AAPL.O", "MSFT.O"]

        df = client.get_earnings_data(tickers)

        if len(df) > 0 and "Event Start Time" in df.columns:
            # Check that times with values are in HH:MM:SS format
            times_with_values = df["Event Start Time"].dropna()

            for time_val in times_with_values:
                time_str = str(time_val)
                # Should be time format or empty
                assert (
                    ":" in time_str or time_str == ""
                ), f"Unexpected time format: {time_str}"


class TestIndexConstituents:
    """Test index constituent retrieval."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_get_index_constituents_basic(self, client):
        """Test basic index constituent retrieval."""
        rics = client.get_index_constituents("SPX")

        # Should return a list
        assert isinstance(rics, list)

        # S&P 500 should have ~500 constituents
        assert 400 < len(rics) < 600

        # All entries should be strings (RICs)
        assert all(isinstance(ric, str) for ric in rics)

        # RICs should have expected format (contains . or suffix)
        assert any("." in ric for ric in rics)

    def test_get_index_constituents_with_prefix(self, client):
        """Test that index symbols work with or without . prefix."""
        # Without prefix
        rics1 = client.get_index_constituents("SPX")

        # With prefix
        rics2 = client.get_index_constituents(".SPX")

        # Should return same results
        assert len(rics1) == len(rics2)
        assert set(rics1) == set(rics2)

    def test_get_index_constituents_market_cap_filter(self, client):
        """Test market cap filtering (2-step process)."""
        # Get all constituents first
        all_rics = client.get_index_constituents("DJI")  # Dow 30 for smaller test

        # Apply market cap filter (very high threshold to get subset)
        # Using $100B+ to filter to only mega-cap stocks
        filtered_rics = client.get_index_constituents(
            "DJI",
            min_market_cap=100_000,  # $100B in millions
        )

        # Should return a list
        assert isinstance(filtered_rics, list)

        # Filtered list should be smaller than or equal to full list
        assert len(filtered_rics) <= len(all_rics)

        # All filtered RICs should be in original list
        assert all(ric in all_rics for ric in filtered_rics)

        print(
            f"\nDow 30: {len(all_rics)} total, {len(filtered_rics)} with market cap >= $100B"
        )

    def test_get_index_constituents_invalid_index(self, client):
        """Test handling of invalid index."""
        with pytest.raises(DataRetrievalError):
            client.get_index_constituents("INVALID_INDEX")


class TestSessionManagement:
    """Test LSEG session management."""

    def test_context_manager(self):
        """Test that context manager works properly."""
        with LsegClient() as client:
            assert client._session_opened

            # Should be able to make API calls
            rics = client.get_index_constituents("SPX")
            assert len(rics) > 0

        # Session should be closed after exiting context
        assert not client._session_opened

    def test_manual_session_management(self):
        """Test manual session open/close."""
        client = LsegClient(auto_open=False)
        assert not client._session_opened

        client.open_session()
        assert client._session_opened

        # Should be able to make API calls
        rics = client.get_index_constituents("SPX")
        assert len(rics) > 0

        client.close_session()
        assert not client._session_opened


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
