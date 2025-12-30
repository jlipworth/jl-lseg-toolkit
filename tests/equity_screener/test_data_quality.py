"""
Test data quality for equity screener - validates all fields are populated correctly.

Tests that major, well-covered companies have valid (non-NaN, non-zero) values
for key financial metrics.
"""

import lseg.data as rd
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def test_companies():
    """
    Sample of major companies with good analyst coverage.

    Includes diverse sectors and geographies to test various scenarios.
    Returns list of (RIC, Expected Sector, Has Analyst Coverage) tuples.
    """
    return [
        ("AAPL.O", "Technology", True),  # Apple - mega cap tech
        ("MSFT.O", "Technology", True),  # Microsoft - mega cap tech
        ("GOOGL.O", "Technology", True),  # Alphabet - mega cap tech
        ("AMZN.O", "Consumer Cyclicals", True),  # Amazon - large cap retail
        ("TSLA.O", "Consumer Cyclicals", True),  # Tesla - large cap auto
        ("JNJ.N", "Healthcare", True),  # J&J - large cap pharma
        ("PG.N", "Consumer Non-Cyclicals", True),  # P&G - consumer staples
        ("XOM.N", "Energy", True),  # Exxon - energy
        ("WMT.N", "Consumer Non-Cyclicals", True),  # Walmart - retail
        ("HD.N", "Consumer Cyclicals", True),  # Home Depot - retail
        # Financials - should have N/A for debt metrics
        ("JPM.N", "Financials", False),  # JPMorgan - bank (no EV/EBITDA)
        ("BAC.N", "Financials", False),  # Bank of America - bank
    ]


@pytest.mark.integration
class TestEquityScreenerDataQuality:
    """Test suite for equity screener data quality."""

    @pytest.fixture(scope="class")
    def screener_data(self, test_companies):
        """
        Fetch equity screener data using the ACTUAL pipeline methods.

        This ensures the test breaks if the pipeline breaks - no logic duplication.
        Uses the real EquityScreenerPipeline._fetch_financial_data() and _process_data().
        """
        from lseg_toolkit.equity_screener.config import EquityScreenerConfig
        from lseg_toolkit.equity_screener.pipeline import EquityScreenerPipeline

        # Open session for the test
        rd.open_session()

        try:
            rics = [ric for ric, _, _ in test_companies]

            # Create pipeline with minimal config
            config = EquityScreenerConfig(index=None, country=None)
            pipeline = EquityScreenerPipeline(config)

            # Use the ACTUAL pipeline methods (not duplicated logic!)
            df = pipeline._fetch_financial_data(rics)
            activism_df = pipeline._fetch_activism_data(rics)
            df = pipeline._process_data(df, activism_df)

            return df

        finally:
            rd.close_session()

    def test_all_companies_fetched(self, screener_data, test_companies):
        """Test that data was fetched for all test companies."""
        expected_count = len(test_companies)
        actual_count = len(screener_data)
        assert (
            actual_count == expected_count
        ), f"Expected {expected_count} companies, got {actual_count}"

    def test_basic_fields_populated(self, screener_data):
        """Test that basic company fields are populated for all companies."""
        # Use renamed column names that the pipeline outputs
        required_fields = [
            "RIC",
            "Company Name",
            "Mkt Cap ($M)",
            "Share Price",
        ]

        for field in required_fields:
            assert field in screener_data.columns, f"Missing field: {field}"

            # Check no NaN values
            missing_count = screener_data[field].isna().sum()
            assert (
                missing_count == 0
            ), f"{field}: {missing_count} missing values (expected 0)"

            # Check no zero values for market cap and price
            if field in ["Mkt Cap ($M)", "Share Price"]:
                zero_count = (screener_data[field] == 0).sum()
                assert (
                    zero_count == 0
                ), f"{field}: {zero_count} zero values (expected 0)"

    def test_valuation_ratios_for_non_financials(self, screener_data, test_companies):
        """Test that valuation ratios are populated for non-financial companies."""
        # Filter to non-financial companies (those with analyst coverage)
        non_financial_rics = [
            ric for ric, _, has_coverage in test_companies if has_coverage
        ]

        non_financial_df = screener_data[screener_data["RIC"].isin(non_financial_rics)]

        # Key valuation ratios that should be populated (using renamed columns)
        ratio_fields = [
            "P/E LTM",  # Renamed from "P/E (Daily Time Series Ratio)"
            "P/E NTM",
            "EV/EBITDA NTM",  # This was the buggy field!
            "P/B",  # Renamed from "Price To Book Value Per Share..."
        ]

        for field in ratio_fields:
            if field not in non_financial_df.columns:
                pytest.skip(f"Field {field} not in data")

            # Check for missing values
            missing = non_financial_df[field].isna()
            if missing.any():
                missing_companies = non_financial_df[missing]["RIC"].tolist()
                pytest.fail(
                    f"{field}: Missing for {len(missing_companies)} non-financial companies: {missing_companies}"
                )

            # Check for zero values (usually indicates missing data)
            zeros = non_financial_df[field] == 0
            if zeros.any():
                zero_companies = non_financial_df[zeros]["RIC"].tolist()
                pytest.fail(
                    f"{field}: Zero values for {len(zero_companies)} companies: {zero_companies}"
                )

    def test_ev_ebitda_ntm_specifically(self, screener_data, test_companies):
        """
        Test EV/EBITDA NTM specifically - this was the main bug.

        Validates that Apple and other major non-financial companies have valid values.
        """
        # Filter to non-financial companies
        non_financial_rics = [
            ric for ric, _, has_coverage in test_companies if has_coverage
        ]
        non_financial_df = screener_data[screener_data["RIC"].isin(non_financial_rics)]

        assert (
            "EV/EBITDA NTM" in non_financial_df.columns
        ), "EV/EBITDA NTM not calculated"

        # Check each non-financial company
        for ric, _, _ in test_companies:
            if ric not in non_financial_rics:
                continue

            company_data = screener_data[screener_data["RIC"] == ric]
            assert not company_data.empty, f"No data for {ric}"

            ev_ebitda = company_data["EV/EBITDA NTM"].iloc[0]
            company_name = company_data["Company Name"].iloc[0]

            # Check not NaN
            assert pd.notna(ev_ebitda), f"{company_name} ({ric}): EV/EBITDA NTM is NaN"

            # Check positive and reasonable (typically 5-100x)
            assert (
                ev_ebitda > 0
            ), f"{company_name} ({ric}): EV/EBITDA NTM is {ev_ebitda} (should be positive)"
            assert (
                ev_ebitda < 200
            ), f"{company_name} ({ric}): EV/EBITDA NTM is {ev_ebitda} (unusually high, check data)"

    def test_financial_companies_show_na(self, screener_data, test_companies):
        """Test that financial companies have N/A for debt-related metrics."""
        financial_rics = [
            ric for ric, sector, _ in test_companies if sector == "Financials"
        ]

        if not financial_rics:
            pytest.skip("No financial companies in test set")

        financial_df = screener_data[screener_data["RIC"].isin(financial_rics)]

        # These fields should be N/A for financials
        na_fields = [
            "Net Debt",
            "Enterprise Value",
            "EV/EBITDA NTM",
            "Net Debt to EBITDA NTM",
            "Net Debt % of EV",
        ]

        for field in na_fields:
            if field not in financial_df.columns:
                continue

            # All values should be NaN for financial companies
            # Note: Pipeline drops "Net Debt" and "Enterprise Value" intermediate columns
            # Only check fields that are in the final output
            if field not in financial_df.columns:
                continue

            non_na_count = financial_df[field].notna().sum()
            if non_na_count > 0:
                companies_with_values = financial_df[financial_df[field].notna()][
                    ["RIC", "Company Name", field]
                ]
                pytest.fail(
                    f"{field}: {non_na_count} financial companies have non-NA values (should be NA):\n{companies_with_values}"
                )

    def test_debt_metrics_consistency(self, screener_data, test_companies):
        """Test that debt-derived metrics are present and reasonable for non-financials."""
        # Filter to non-financial companies
        non_financial_rics = [
            ric for ric, _, has_coverage in test_companies if has_coverage
        ]
        non_financial_df = screener_data[screener_data["RIC"].isin(non_financial_rics)]

        # Check that debt-related metrics are present
        # Note: Pipeline drops intermediate columns (Net Debt, Enterprise Value)
        # but keeps calculated ratios (Net Debt/EBITDA, Net Debt % of EV)
        debt_metrics = ["Net Debt to EBITDA NTM", "Net Debt % of EV"]

        for metric in debt_metrics:
            if metric not in non_financial_df.columns:
                continue

            # Should have some valid values for non-financials
            valid_count = non_financial_df[metric].notna().sum()
            assert (
                valid_count > 0
            ), f"{metric}: No valid values for non-financial companies"

    def test_returns_populated(self, screener_data):
        """Test that return data is populated for all companies."""
        # 1Y returns should be populated for all (using renamed column)
        return_col = "YTD Total Return (%)"  # Renamed from "1 Year Total Return"
        if return_col in screener_data.columns:
            missing = screener_data[return_col].isna().sum()
            # Allow a few missing (IPOs in last year)
            assert missing <= 2, f"Too many missing 1Y returns: {missing}"

    def test_sample_output_format(self, screener_data):
        """Print sample data for manual verification."""
        print("\n" + "=" * 80)
        print("SAMPLE EQUITY SCREENER DATA (from actual pipeline)")
        print("=" * 80)

        # Use renamed column names that the pipeline outputs
        display_cols = [
            "RIC",
            "Company Name",
            "Mkt Cap ($M)",
            "P/E NTM",
            "EV/EBITDA NTM",
            "P/B",
        ]

        available_cols = [col for col in display_cols if col in screener_data.columns]
        print(screener_data[available_cols].head(10).to_string(index=False))
        print()
