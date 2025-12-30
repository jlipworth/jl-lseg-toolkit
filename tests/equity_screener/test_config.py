"""
Tests for equity_screener configuration.
"""

from datetime import date

import pytest

from lseg_toolkit.equity_screener.config import EquityScreenerConfig
from lseg_toolkit.exceptions import ConfigurationError


class TestEquityScreenerConfig:
    """Test EquityScreenerConfig class."""

    def test_default_config(self):
        """Test configuration with default values."""
        config = EquityScreenerConfig()

        assert config.screen_date == date.today().strftime("%Y-%m-%d")
        assert config.index == "SPX"
        assert config.country == "US"
        assert config.min_mkt_cap is None  # Unrestricted by default
        assert config.max_mkt_cap is None  # Unrestricted by default
        assert config.output_dir == "exports"

    def test_custom_config(self):
        """Test configuration with custom values."""
        config = EquityScreenerConfig(
            screen_date="2024-12-31",
            index="NDX",
            country="GB",
            min_mkt_cap=5000.0,
            max_mkt_cap=15000.0,
            output_dir="my_screens",
        )

        assert config.screen_date == "2024-12-31"
        assert config.index == "NDX"
        assert config.country == "GB"
        assert config.min_mkt_cap == 5000.0
        assert config.max_mkt_cap == 15000.0
        assert config.output_dir == "my_screens"

    def test_invalid_date_format(self):
        """Test that invalid date format raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Invalid date format"):
            EquityScreenerConfig(screen_date="12/31/2024")

    def test_negative_market_cap(self):
        """Test that negative market cap raises ConfigurationError."""
        with pytest.raises(
            ConfigurationError, match="Minimum market cap must be positive"
        ):
            EquityScreenerConfig(min_mkt_cap=-100.0)

    def test_invalid_market_cap_range(self):
        """Test that min >= max raises ConfigurationError."""
        with pytest.raises(
            ConfigurationError, match="Minimum market cap must be less than"
        ):
            EquityScreenerConfig(min_mkt_cap=10000.0, max_mkt_cap=5000.0)

    def test_to_dict(self):
        """Test config to dictionary conversion."""
        config = EquityScreenerConfig(
            screen_date="2024-12-31", min_mkt_cap=5000.0, max_mkt_cap=15000.0
        )

        result = config.to_dict()

        assert result["Screen Date"] == "2024-12-31"
        assert result["Index"] == "SPX"  # Default index
        assert result["Country"] == "US"  # Default country
        assert result["Min Market Cap"] == "$5.0B"
        assert result["Max Market Cap"] == "$15.0B"
        assert result["Output Directory"] == "exports"

    def test_get_mkt_cap_range(self):
        """Test market cap range conversion."""
        config = EquityScreenerConfig(min_mkt_cap=2000.0, max_mkt_cap=20000.0)

        min_cap, max_cap = config.get_mkt_cap_range()

        assert min_cap == 2_000_000_000
        assert max_cap == 20_000_000_000

    def test_market_cap_formatting_billions(self):
        """Test market cap formatting for values >= $1B."""
        config = EquityScreenerConfig(min_mkt_cap=5000.0, max_mkt_cap=50000.0)

        result = config.to_dict()

        assert result["Min Market Cap"] == "$5.0B"
        assert result["Max Market Cap"] == "$50.0B"

    def test_market_cap_formatting_millions(self):
        """Test market cap formatting for values < $1B."""
        config = EquityScreenerConfig(min_mkt_cap=500.0, max_mkt_cap=900.0)

        result = config.to_dict()

        assert result["Min Market Cap"] == "$500M"
        assert result["Max Market Cap"] == "$900M"
