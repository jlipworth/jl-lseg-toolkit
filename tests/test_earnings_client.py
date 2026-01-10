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

from lseg_toolkit.client import LsegClient  # noqa: E402
from lseg_toolkit.exceptions import DataRetrievalError  # noqa: E402

pytestmark = pytest.mark.integration  # Skip in CI


class TestEarningsData:
    """Test earnings data retrieval."""

    def test_get_earnings_data_basic(self, lseg_client_class):
        """Test basic earnings data retrieval with date range."""
        tickers = ["AAPL.O", "MSFT.O", "GOOGL.O"]

        today = datetime.now()
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

        df = lseg_client_class.get_earnings_data(
            tickers, start_date=start_date, end_date=end_date
        )

        assert isinstance(df, pd.DataFrame)

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

        assert len(df) > 0, f"No earnings found in date range {start_date} to {end_date}"

        if len(df) > 0:
            assert (df["Company Event Type"] == "EarningsReleases").all()

    def test_get_earnings_data_with_date_filter(self, lseg_client_class):
        """Test earnings data retrieval with date filtering."""
        rics = lseg_client_class.get_index_constituents("SPX")
        sample_rics = rics[:50]

        today = datetime.now()
        start_date = today.strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

        df = lseg_client_class.get_earnings_data(
            sample_rics, start_date=start_date, end_date=end_date
        )

        assert isinstance(df, pd.DataFrame)

        if len(df) > 0:
            df_dates = pd.to_datetime(df["Event Start Date"])
            assert df_dates.min() >= pd.to_datetime(start_date)
            assert df_dates.max() <= pd.to_datetime(end_date)

    def test_get_earnings_data_empty_result(self, lseg_client_class):
        """Test that empty results are handled properly."""
        df = lseg_client_class.get_earnings_data(
            ["AAPL.O"], start_date="2020-01-01", end_date="2020-01-02"
        )

        assert isinstance(df, pd.DataFrame)

    def test_earnings_times_format(self, lseg_client_class):
        """Test that earnings times are in expected format."""
        tickers = ["AAPL.O", "MSFT.O"]

        df = lseg_client_class.get_earnings_data(tickers)

        if len(df) > 0 and "Event Start Time" in df.columns:
            times_with_values = df["Event Start Time"].dropna()

            for time_val in times_with_values:
                time_str = str(time_val)
                assert ":" in time_str or time_str == "", (
                    f"Unexpected time format: {time_str}"
                )


class TestIndexConstituents:
    """Test index constituent retrieval."""

    def test_get_index_constituents_basic(self, lseg_client_class):
        """Test basic index constituent retrieval."""
        rics = lseg_client_class.get_index_constituents("SPX")

        assert isinstance(rics, list)
        assert 400 < len(rics) < 600
        assert all(isinstance(ric, str) for ric in rics)
        assert any("." in ric for ric in rics)

    def test_get_index_constituents_with_prefix(self, lseg_client_class):
        """Test that index symbols work with or without . prefix."""
        rics1 = lseg_client_class.get_index_constituents("SPX")
        rics2 = lseg_client_class.get_index_constituents(".SPX")

        assert len(rics1) == len(rics2)
        assert set(rics1) == set(rics2)

    def test_get_index_constituents_market_cap_filter(self, lseg_client_class):
        """Test market cap filtering (2-step process)."""
        all_rics = lseg_client_class.get_index_constituents("DJI")

        filtered_rics = lseg_client_class.get_index_constituents(
            "DJI",
            min_market_cap=100_000,
        )

        assert isinstance(filtered_rics, list)
        assert len(filtered_rics) <= len(all_rics)
        assert all(ric in all_rics for ric in filtered_rics)

        print(
            f"\nDow 30: {len(all_rics)} total, {len(filtered_rics)} with market cap >= $100B"
        )

    def test_get_index_constituents_invalid_index(self, lseg_client_class):
        """Test handling of invalid index."""
        with pytest.raises(DataRetrievalError):
            lseg_client_class.get_index_constituents("INVALID_INDEX")


class TestSessionManagement:
    """Test LSEG session management.

    Note: These tests create their own clients to test session lifecycle.
    """

    def test_context_manager(self):
        """Test that context manager works properly."""
        with LsegClient() as client:
            assert client._session_opened

            rics = client.get_index_constituents("SPX")
            assert len(rics) > 0

        assert not client._session_opened

    def test_manual_session_management(self):
        """Test manual session open/close."""
        client = LsegClient(auto_open=False)
        assert not client._session_opened

        client.open_session()
        assert client._session_opened

        rics = client.get_index_constituents("SPX")
        assert len(rics) > 0

        client.close_session()
        assert not client._session_opened


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
