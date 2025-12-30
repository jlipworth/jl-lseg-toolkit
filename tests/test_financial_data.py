"""
Tests for financial data extraction methods.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lseg_toolkit.client import LsegClient


class TestCompanyData:
    """Test company data retrieval."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_get_company_data_basic(self, client):
        """Test basic company data retrieval."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = client.get_company_data(tickers)

        # Should return DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Should have expected columns
        assert "Instrument" in df.columns
        assert "Company Common Name" in df.columns
        assert "TRBC Economic Sector Name" in df.columns
        assert "Price Close" in df.columns
        assert "Company Market Cap" in df.columns

    def test_get_company_data_with_custom_fields(self, client):
        """Test company data with custom fields."""
        tickers = ["AAPL.O"]
        custom_fields = ["TR.CommonName", "TR.HeadquartersCountry"]

        df = client.get_company_data(tickers, fields=custom_fields)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_company_data_empty_list(self, client):
        """Test with empty ticker list."""
        df = client.get_company_data([])

        # Should return empty DataFrame gracefully
        assert isinstance(df, pd.DataFrame)


class TestFinancialRatios:
    """Test financial ratios retrieval."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_get_financial_ratios_basic(self, client):
        """Test basic financial ratios retrieval."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = client.get_financial_ratios(tickers)

        # Should return DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Should have valuation ratios
        assert "P/E (Daily Time Series Ratio)" in df.columns or "P/E" in df.columns
        assert (
            "Price To Book Value Per Share (Daily Time Series Ratio)" in df.columns
            or "P/B" in df.columns
        )

        # Should have return metrics
        assert "YTD Total Return" in df.columns
        assert "1 Year Total Return" in df.columns
        assert "3 Year Total Return" in df.columns
        assert "5 Year Total Return" in df.columns

        # Should have calculated ratios
        if "P/E NTM" in df.columns:
            # Check that calculated P/E NTM exists for at least one company
            assert df["P/E NTM"].notna().any()

    def test_get_financial_ratios_with_estimates(self, client):
        """Test financial ratios with estimates included."""
        tickers = ["AAPL.O"]
        df = client.get_financial_ratios(tickers, include_estimates=True)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Should have estimate fields when include_estimates=True
        # Check for either the raw field name or our calculated field
        has_estimates = (
            "Earnings Per Share - Mean" in df.columns
            or "EBITDA - Mean" in df.columns
            or "P/E NTM" in df.columns
        )
        assert has_estimates

    def test_get_financial_ratios_without_estimates(self, client):
        """Test financial ratios without estimates."""
        tickers = ["AAPL.O"]
        df = client.get_financial_ratios(tickers, include_estimates=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Should not have consensus estimate fields
        assert "Earnings Per Share - Mean" not in df.columns

    def test_calculated_ratios_are_numeric(self, client):
        """Test that calculated ratios are numeric values."""
        tickers = ["AAPL.O"]
        df = client.get_financial_ratios(tickers)

        # Check calculated fields are numeric (if they exist)
        calc_fields = [
            "P/E NTM",
            "Net Debt to EBITDA NTM",
            "P/FCF LTM",
            "Net Debt % of EV",
        ]

        for field in calc_fields:
            if field in df.columns:
                # Should be numeric or NaN (not datetime or string)
                assert df[field].dtype in [
                    "float64",
                    "int64",
                    "float32",
                    "int32",
                ] or pd.api.types.is_numeric_dtype(df[field])


class TestConsensusEstimates:
    """Test consensus estimates retrieval."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_get_consensus_estimates_ntm(self, client):
        """Test NTM consensus estimates."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = client.get_consensus_estimates(tickers, period="NTM")

        # Should return DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Should have expected columns
        assert "Instrument" in df.columns
        assert "Company Common Name" in df.columns

        # Should have at least one estimate field
        estimate_fields = [
            "Revenue - Mean",
            "EBITDA - Mean",
            "Earnings Per Share - Mean",
            "Number of Analysts",
        ]

        has_estimate = any(field in df.columns for field in estimate_fields)
        assert has_estimate

    def test_get_consensus_estimates_fy1(self, client):
        """Test FY1 consensus estimates."""
        tickers = ["AAPL.O"]
        df = client.get_consensus_estimates(tickers, period="FY1")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_consensus_estimates_empty(self, client):
        """Test with empty ticker list."""
        df = client.get_consensus_estimates([])

        assert isinstance(df, pd.DataFrame)


class TestIntegration:
    """Integration tests combining multiple data methods."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a client instance for the test class."""
        client = LsegClient()
        yield client
        client.close_session()

    def test_combined_data_retrieval(self, client):
        """Test retrieving multiple data types for same companies."""
        tickers = ["AAPL.O", "MSFT.O"]

        # Get company basics
        company_df = client.get_company_data(tickers)
        assert len(company_df) > 0

        # Get ratios
        ratios_df = client.get_financial_ratios(tickers)
        assert len(ratios_df) > 0

        # Get estimates
        estimates_df = client.get_consensus_estimates(tickers)
        assert len(estimates_df) > 0

        # All should have same instruments
        assert set(company_df["Instrument"]) == set(ratios_df["Instrument"])
        assert set(company_df["Instrument"]) == set(estimates_df["Instrument"])

    def test_merge_all_data(self, client):
        """Test that all data can be merged on instrument."""
        tickers = ["AAPL.O"]

        company_df = client.get_company_data(tickers)
        ratios_df = client.get_financial_ratios(tickers)
        estimates_df = client.get_consensus_estimates(tickers)

        # Merge all data with suffixes to avoid conflicts
        combined = company_df.merge(
            ratios_df, on="Instrument", how="outer", suffixes=("", "_ratio")
        )
        combined = combined.merge(
            estimates_df, on="Instrument", how="outer", suffixes=("", "_est")
        )

        # Should have data from all sources
        assert len(combined) > 0
        assert "Instrument" in combined.columns
        # Check that we have some data from each source
        assert (
            "Company Common Name" in combined.columns
            or "Company Common Name_ratio" in combined.columns
        )
        assert "P/E (Daily Time Series Ratio)" in combined.columns  # From ratios
        assert "Revenue - Mean" in combined.columns  # From estimates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
