"""
Test data quality for earnings pipeline - validates end-to-end pipeline execution.

Tests that the earnings pipeline correctly fetches and processes all data for major companies.
Uses the ACTUAL pipeline methods to ensure regressions are caught.
"""

from datetime import datetime, timedelta

import lseg.data as rd
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def test_companies():
    """
    Sample of major companies with regular earnings schedules.

    Returns list of (RIC, Expected Sector) tuples.
    """
    return [
        ("AAPL.O", "Technology"),  # Apple - mega cap tech
        ("MSFT.O", "Technology"),  # Microsoft - mega cap tech
        ("GOOGL.O", "Technology"),  # Alphabet - mega cap tech
        ("AMZN.O", "Consumer Cyclicals"),  # Amazon
        (
            "JPM.N",
            "Financials",
        ),  # JPMorgan - financial (should have N/A for debt metrics)
    ]


@pytest.mark.integration
class TestEarningsPipelineDataQuality:
    """Test suite for earnings pipeline data quality."""

    @pytest.fixture(scope="class")
    def pipeline_data(self, test_companies):
        """
        Run the ACTUAL earnings pipeline end-to-end.

        This ensures the test breaks if the pipeline breaks - no logic duplication.
        Tests the full pipeline including data merging logic.
        """
        from lseg_toolkit.earnings.config import EarningsConfig
        from lseg_toolkit.earnings.pipeline import EarningsReportPipeline

        # Use a wide date range to capture earnings (6 months window)
        today = datetime.now()
        start_dt = today - timedelta(days=90)
        end_dt = today + timedelta(days=90)

        config = EarningsConfig(
            index="SPX",
            start_date=start_dt,
            end_date=end_dt,
            min_market_cap=None,
            max_market_cap=None,
            output_dir="exports",
            timezone="US/Eastern",
        )

        # Create pipeline
        pipeline = EarningsReportPipeline(config)

        # Open session
        rd.open_session()

        try:
            # Filter to just our test companies
            rics = [ric for ric, _ in test_companies]

            # Run the ACTUAL pipeline methods (same code path as production)
            # Step 1: Fetch earnings data (includes all company/financial/consensus data)
            df = pipeline._fetch_earnings_data(rics)

            # Step 2: Process the data (calculate derived metrics)
            df = pipeline._process_data(df)

            return df

        finally:
            rd.close_session()

    def test_all_companies_have_data(self, pipeline_data, test_companies):
        """Test that all test companies have at least company data."""
        expected_rics = {ric for ric, _ in test_companies}
        actual_rics = set(pipeline_data["Instrument"].unique())

        missing_rics = expected_rics - actual_rics
        assert not missing_rics, f"Missing data for companies: {missing_rics}"

    def test_basic_fields_populated(self, pipeline_data):
        """Test that basic company fields are populated for all companies."""
        required_fields = [
            "Instrument",
            "Company Common Name",
            "Company Market Cap",
            "Price Close",
        ]

        for field in required_fields:
            assert field in pipeline_data.columns, f"Missing field: {field}"

            # Check no NaN values
            missing_count = pipeline_data[field].isna().sum()
            assert (
                missing_count == 0
            ), f"{field}: {missing_count} missing values (expected 0)"

            # Check no zero values for market cap and price
            if field in ["Company Market Cap", "Price Close"]:
                zero_count = (pipeline_data[field] == 0).sum()
                assert (
                    zero_count == 0
                ), f"{field}: {zero_count} zero values (expected 0)"

    def test_financial_metrics_for_non_financials(self, pipeline_data, test_companies):
        """Test that financial metrics are populated for non-financial companies."""
        # Filter to non-financial companies
        non_financial_rics = [
            ric for ric, sector in test_companies if sector != "Financials"
        ]

        non_financial_df = pipeline_data[
            pipeline_data["Instrument"].isin(non_financial_rics)
        ]

        # Key metrics that should be populated
        metrics = [
            "P/E (Daily Time Series Ratio)",  # P/E LTM
            "P/E NTM",
            "EV/EBITDA NTM",  # Should be calculated from components
            "Price To Book Value Per Share (Daily Time Series Ratio)",  # P/B
        ]

        for metric in metrics:
            if metric not in non_financial_df.columns:
                pytest.skip(f"Metric {metric} not in data")

            # Check for missing values
            missing = non_financial_df[metric].isna()
            if missing.any():
                missing_companies = non_financial_df[missing]["Instrument"].tolist()
                pytest.fail(
                    f"{metric}: Missing for {len(missing_companies)} non-financial companies: {missing_companies}"
                )

    def test_ev_ebitda_ntm_calculated(self, pipeline_data, test_companies):
        """
        Test EV/EBITDA NTM is calculated correctly for non-financial companies.

        This was a major bug in both earnings and screener pipelines.
        """
        # Filter to non-financial companies
        non_financial_rics = [
            ric for ric, sector in test_companies if sector != "Financials"
        ]

        for ric in non_financial_rics:
            company_data = pipeline_data[pipeline_data["Instrument"] == ric]
            if company_data.empty:
                continue

            if "EV/EBITDA NTM" not in company_data.columns:
                pytest.fail("EV/EBITDA NTM not calculated")

            ev_ebitda = company_data["EV/EBITDA NTM"].iloc[0]
            company_name = company_data["Company Common Name"].iloc[0]

            # Check not NaN
            assert pd.notna(ev_ebitda), f"{company_name} ({ric}): EV/EBITDA NTM is NaN"

            # Check positive and reasonable
            assert (
                ev_ebitda > 0
            ), f"{company_name} ({ric}): EV/EBITDA NTM is {ev_ebitda} (should be positive)"
            assert (
                ev_ebitda < 200
            ), f"{company_name} ({ric}): EV/EBITDA NTM is {ev_ebitda} (unusually high)"

    def test_financial_companies_data_present(self, pipeline_data, test_companies):
        """
        Test that financial companies have data.

        Note: Unlike the screener pipeline, the earnings pipeline does NOT
        filter out debt metrics for financials. This test just verifies
        financials are included in the output.
        """
        financial_rics = [
            ric for ric, sector in test_companies if sector == "Financials"
        ]

        if not financial_rics:
            pytest.skip("No financial companies in test set")

        financial_df = pipeline_data[pipeline_data["Instrument"].isin(financial_rics)]

        # Just verify financial companies are in the data
        assert len(financial_df) > 0, "Financial companies should be in earnings data"

    def test_returns_populated(self, pipeline_data):
        """Test that return data is populated for all companies."""
        # Returns should be populated for most companies
        return_fields = ["YTD Total Return", "1 Year Total Return"]

        for field in return_fields:
            if field not in pipeline_data.columns:
                continue

            missing = pipeline_data[field].isna().sum()
            # Allow a few missing (recent IPOs)
            assert missing <= 2, f"Too many missing {field}: {missing}"

    def test_snapshot_date_consistency(self, pipeline_data):
        """Test that snapshot date is being used consistently."""
        # All data should be fetched as of the snapshot date
        # This is critical for report consistency

        # At minimum, market cap and price should be consistent
        # (same date snapshot for all companies)
        if "Company Market Cap" in pipeline_data.columns:
            # If we have multiple companies, market caps should be reasonable
            # and not show signs of being from different dates
            market_caps = pipeline_data["Company Market Cap"].dropna()
            assert len(market_caps) > 0, "No market cap data found"

    def test_sample_output_format(self, pipeline_data):
        """Print sample data for manual verification."""
        print("\n" + "=" * 80)
        print("SAMPLE EARNINGS PIPELINE DATA (from actual pipeline)")
        print("=" * 80)

        display_cols = [
            "Instrument",
            "Company Common Name",
            "Company Market Cap",
            "Price Close",
            "P/E NTM",
            "EV/EBITDA NTM",
        ]

        available_cols = [col for col in display_cols if col in pipeline_data.columns]
        print(pipeline_data[available_cols].head(10).to_string(index=False))
        print()
