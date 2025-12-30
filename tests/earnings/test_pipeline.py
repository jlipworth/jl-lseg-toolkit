"""Tests for earnings pipeline."""

from lseg_toolkit.earnings.config import EarningsConfig
from lseg_toolkit.earnings.pipeline import EarningsReportPipeline


class TestEarningsReportPipeline:
    """Test cases for EarningsReportPipeline."""

    def test_pipeline_initialization(self):
        """Test pipeline can be initialized."""
        config = EarningsConfig()
        pipeline = EarningsReportPipeline(config)
        assert pipeline.config == config
        assert pipeline.client is not None

    # TODO: Add tests for:
    # - Full pipeline execution
    # - Universe filtering
    # - Data fetching
    # - Data processing
    # - Excel export
