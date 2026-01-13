"""
Tests for financial data extraction methods.

These tests require LSEG Workspace Desktop running.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


pytestmark = pytest.mark.integration  # Skip in CI


class TestCompanyData:
    """Test company data retrieval."""

    def test_get_company_data_basic(self, lseg_client_class):
        """Test basic company data retrieval."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = lseg_client_class.get_company_data(tickers)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        assert "Instrument" in df.columns
        assert "Company Common Name" in df.columns
        assert "TRBC Economic Sector Name" in df.columns
        assert "Price Close" in df.columns
        assert "Company Market Cap" in df.columns

    def test_get_company_data_with_custom_fields(self, lseg_client_class):
        """Test company data with custom fields."""
        tickers = ["AAPL.O"]
        custom_fields = ["TR.CommonName", "TR.HeadquartersCountry"]

        df = lseg_client_class.get_company_data(tickers, fields=custom_fields)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_company_data_empty_list(self, lseg_client_class):
        """Test with empty ticker list."""
        df = lseg_client_class.get_company_data([])

        assert isinstance(df, pd.DataFrame)


class TestFinancialRatios:
    """Test financial ratios retrieval."""

    def test_get_financial_ratios_basic(self, lseg_client_class):
        """Test basic financial ratios retrieval."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = lseg_client_class.get_financial_ratios(tickers)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        assert "P/E (Daily Time Series Ratio)" in df.columns or "P/E" in df.columns
        assert (
            "Price To Book Value Per Share (Daily Time Series Ratio)" in df.columns
            or "P/B" in df.columns
        )

        assert "YTD Total Return" in df.columns
        assert "1 Year Total Return" in df.columns
        assert "3 Year Total Return" in df.columns
        assert "5 Year Total Return" in df.columns

        if "P/E NTM" in df.columns:
            assert df["P/E NTM"].notna().any()

    def test_get_financial_ratios_with_estimates(self, lseg_client_class):
        """Test financial ratios with estimates included."""
        tickers = ["AAPL.O"]
        df = lseg_client_class.get_financial_ratios(tickers, include_estimates=True)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        has_estimates = (
            "Earnings Per Share - Mean" in df.columns
            or "EBITDA - Mean" in df.columns
            or "P/E NTM" in df.columns
        )
        assert has_estimates

    def test_get_financial_ratios_without_estimates(self, lseg_client_class):
        """Test financial ratios without estimates."""
        tickers = ["AAPL.O"]
        df = lseg_client_class.get_financial_ratios(tickers, include_estimates=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        assert "Earnings Per Share - Mean" not in df.columns

    def test_calculated_ratios_are_numeric(self, lseg_client_class):
        """Test that calculated ratios are numeric values."""
        tickers = ["AAPL.O"]
        df = lseg_client_class.get_financial_ratios(tickers)

        calc_fields = [
            "P/E NTM",
            "Net Debt to EBITDA NTM",
            "P/FCF LTM",
            "Net Debt % of EV",
        ]

        for field in calc_fields:
            if field in df.columns:
                assert df[field].dtype in [
                    "float64",
                    "int64",
                    "float32",
                    "int32",
                ] or pd.api.types.is_numeric_dtype(df[field])


class TestConsensusEstimates:
    """Test consensus estimates retrieval."""

    def test_get_consensus_estimates_ntm(self, lseg_client_class):
        """Test NTM consensus estimates."""
        tickers = ["AAPL.O", "MSFT.O"]
        df = lseg_client_class.get_consensus_estimates(tickers, period="NTM")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        assert "Instrument" in df.columns
        assert "Company Common Name" in df.columns

        estimate_fields = [
            "Revenue - Mean",
            "EBITDA - Mean",
            "Earnings Per Share - Mean",
            "Number of Analysts",
        ]

        has_estimate = any(field in df.columns for field in estimate_fields)
        assert has_estimate

    def test_get_consensus_estimates_fy1(self, lseg_client_class):
        """Test FY1 consensus estimates."""
        tickers = ["AAPL.O"]
        df = lseg_client_class.get_consensus_estimates(tickers, period="FY1")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_consensus_estimates_empty(self, lseg_client_class):
        """Test with empty ticker list."""
        df = lseg_client_class.get_consensus_estimates([])

        assert isinstance(df, pd.DataFrame)


class TestIntegration:
    """Integration tests combining multiple data methods."""

    def test_combined_data_retrieval(self, lseg_client_class):
        """Test retrieving multiple data types for same companies."""
        tickers = ["AAPL.O", "MSFT.O"]

        company_df = lseg_client_class.get_company_data(tickers)
        assert len(company_df) > 0

        ratios_df = lseg_client_class.get_financial_ratios(tickers)
        assert len(ratios_df) > 0

        estimates_df = lseg_client_class.get_consensus_estimates(tickers)
        assert len(estimates_df) > 0

        assert set(company_df["Instrument"]) == set(ratios_df["Instrument"])
        assert set(company_df["Instrument"]) == set(estimates_df["Instrument"])

    def test_merge_all_data(self, lseg_client_class):
        """Test that all data can be merged on instrument."""
        tickers = ["AAPL.O"]

        company_df = lseg_client_class.get_company_data(tickers)
        ratios_df = lseg_client_class.get_financial_ratios(tickers)
        estimates_df = lseg_client_class.get_consensus_estimates(tickers)

        combined = company_df.merge(
            ratios_df, on="Instrument", how="outer", suffixes=("", "_ratio")
        )
        combined = combined.merge(
            estimates_df, on="Instrument", how="outer", suffixes=("", "_est")
        )

        assert len(combined) > 0
        assert "Instrument" in combined.columns
        assert (
            "Company Common Name" in combined.columns
            or "Company Common Name_ratio" in combined.columns
        )
        assert "P/E (Daily Time Series Ratio)" in combined.columns
        assert "Revenue - Mean" in combined.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
