"""
Unit tests for the CLI module.

Tests date parsing, argument handling, and help output.
These tests don't require LSEG Workspace.
"""

import argparse
from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

import pytest

from lseg_toolkit.timeseries.cli import list_instruments, parse_date


class TestParseDate:
    """Test date string parsing."""

    def test_valid_date_format(self):
        """Valid YYYY-MM-DD dates should parse correctly."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_valid_date_edge_of_month(self):
        """End of month dates should parse correctly."""
        assert parse_date("2024-01-31") == date(2024, 1, 31)
        assert parse_date("2024-02-29") == date(2024, 2, 29)  # Leap year

    def test_valid_date_edge_of_year(self):
        """Beginning and end of year should parse correctly."""
        assert parse_date("2024-01-01") == date(2024, 1, 1)
        assert parse_date("2024-12-31") == date(2024, 12, 31)

    def test_invalid_format_raises_error(self):
        """Invalid date formats should raise ArgumentTypeError."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_date("01-15-2024")

        assert "Invalid date format" in str(exc_info.value)
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_format_american_style(self):
        """MM/DD/YYYY format should raise error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("01/15/2024")

    def test_invalid_format_no_dashes(self):
        """Dates without dashes should raise error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("20240115")

    def test_invalid_date_values(self):
        """Invalid date values should raise error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024-13-01")  # Invalid month

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024-02-30")  # Invalid day for Feb

    def test_empty_string_raises_error(self):
        """Empty string should raise error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("")

    def test_whitespace_raises_error(self):
        """Whitespace should raise error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("   ")


class TestListInstruments:
    """Test instrument listing output."""

    def test_list_instruments_contains_futures(self):
        """Output should contain bond futures."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_instruments()
            output = mock_stdout.getvalue()

        assert "BOND FUTURES" in output
        assert "ZN" in output
        assert "ZB" in output
        assert "10-Year T-Note" in output

    def test_list_instruments_contains_fx(self):
        """Output should contain FX pairs."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_instruments()
            output = mock_stdout.getvalue()

        assert "FX SPOT" in output
        assert "EURUSD" in output
        assert "USDJPY" in output

    def test_list_instruments_contains_ois(self):
        """Output should contain OIS curve tenors."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_instruments()
            output = mock_stdout.getvalue()

        assert "OIS CURVE" in output

    def test_list_instruments_contains_treasury(self):
        """Output should contain Treasury yields."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_instruments()
            output = mock_stdout.getvalue()

        assert "TREASURY YIELDS" in output

    def test_list_instruments_contains_examples(self):
        """Output should contain usage examples."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            list_instruments()
            output = mock_stdout.getvalue()

        assert "Examples:" in output
        assert "lseg-extract" in output


class TestDefaultDateRange:
    """Test default date range logic."""

    def test_default_start_date_is_one_year_ago(self):
        """Default start should be approximately 1 year ago."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig

        config = TimeSeriesConfig()
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        # Allow some tolerance (within a week)
        assert abs((config.start_date - one_year_ago).days) <= 7

    def test_default_end_date_is_today(self):
        """Default end should be today."""
        from lseg_toolkit.timeseries.config import TimeSeriesConfig

        config = TimeSeriesConfig()
        today = date.today()

        # Should be today or very close
        assert abs((config.end_date - today).days) <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
