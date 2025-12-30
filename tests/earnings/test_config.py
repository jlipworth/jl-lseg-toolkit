"""Tests for earnings configuration."""

from lseg_toolkit.earnings.config import EarningsConfig


class TestEarningsConfig:
    """Test cases for EarningsConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EarningsConfig()
        assert config.index == "SPX"
        assert config.min_market_cap is None
        assert config.max_market_cap is None
        assert config.timezone == "US/Eastern"
        assert config.output_dir == "exports"

    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = EarningsConfig(
            index="NDX", min_market_cap=1000.0, max_market_cap=50000.0
        )
        assert config.index == "NDX"
        assert config.min_market_cap == 1000.0
        assert config.max_market_cap == 50000.0

    def test_default_date_range(self):
        """Test that default date range is set to current week."""
        config = EarningsConfig()
        assert config.start_date is not None
        assert config.end_date is not None
        assert config.start_date <= config.end_date

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = EarningsConfig(index="SPX")
        result = config.to_dict()
        assert "Index" in result
        assert result["Index"] == "SPX"
