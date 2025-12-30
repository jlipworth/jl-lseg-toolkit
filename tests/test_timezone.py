"""
Tests for timezone conversion utilities.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lseg_toolkit.timezone_utils import (
    add_timezone_converted_columns,
    convert_datetime_to_timezone,
)


class TestTimezoneConversion:
    """Test timezone conversion functions."""

    def test_convert_datetime_gmt_to_eastern(self):
        """Test converting GMT to US/Eastern."""
        # 8 PM GMT (typical US AMC time)
        dt_gmt = datetime(2025, 10, 30, 20, 0, 0)

        # Convert to Eastern
        dt_eastern = convert_datetime_to_timezone(
            dt_gmt, from_tz="GMT", to_tz="US/Eastern"
        )

        # Should be 4 PM Eastern (EDT = GMT-4 in October)
        assert dt_eastern.hour == 16
        assert dt_eastern.minute == 0

    def test_convert_datetime_gmt_to_london(self):
        """Test converting GMT to Europe/London."""
        # 7 AM GMT (typical UK BMO time)
        dt_gmt = datetime(2025, 11, 4, 7, 0, 0)

        # Convert to London (same as GMT in November)
        dt_london = convert_datetime_to_timezone(
            dt_gmt, from_tz="GMT", to_tz="Europe/London"
        )

        # Should be same time (GMT = Europe/London in November)
        assert dt_london.hour == 7
        assert dt_london.minute == 0

    def test_convert_datetime_gmt_to_tokyo(self):
        """Test converting GMT to Asia/Tokyo."""
        # 5 AM GMT (typical Japan earnings time)
        dt_gmt = datetime(2025, 11, 5, 4, 55, 0)

        # Convert to Tokyo (JST = GMT+9)
        dt_tokyo = convert_datetime_to_timezone(
            dt_gmt, from_tz="GMT", to_tz="Asia/Tokyo"
        )

        # Should be ~2 PM Tokyo time
        assert dt_tokyo.hour == 13
        assert dt_tokyo.minute == 55

    def test_add_timezone_converted_columns_empty_df(self):
        """Test that empty DataFrame is handled gracefully."""
        df = pd.DataFrame()
        result = add_timezone_converted_columns(df, "US/Eastern")

        assert result.empty

    def test_add_timezone_converted_columns_no_datetime_col(self):
        """Test DataFrame without datetime column."""
        df = pd.DataFrame({"Instrument": ["AAPL.O"], "Name": ["Apple"]})
        result = add_timezone_converted_columns(df, "US/Eastern")

        # Should return original DataFrame unchanged
        assert "Event Time (US/Eastern)" not in result.columns

    def test_add_timezone_converted_columns_with_times(self):
        """Test adding converted timezone columns."""
        # Create sample earnings data
        df = pd.DataFrame(
            {
                "Instrument": ["AAPL.O", "BP.L", "7203.T"],
                "Company Common Name": ["Apple Inc", "BP PLC", "Toyota"],
                "Event Start Date": ["2025-10-30", "2025-11-04", "2025-11-05"],
                "Event Start Time": ["20:00:00", "07:00:00", "04:55:00"],
                "Event Start Date Time": [
                    datetime(2025, 10, 30, 20, 0, 0),
                    datetime(2025, 11, 4, 7, 0, 0),
                    datetime(2025, 11, 5, 4, 55, 0),
                ],
            }
        )

        # Convert to US/Eastern
        result = add_timezone_converted_columns(df, "US/Eastern")

        # Check that new columns were added
        assert "Event Start Date Time (GMT)" in result.columns
        assert "Event Start Date Time (US/Eastern)" in result.columns
        assert "Event Time (US/Eastern)" in result.columns

        # Check Apple earnings (20:00 GMT -> 16:00 EDT)
        apple_row = result[result["Instrument"] == "AAPL.O"].iloc[0]
        eastern_dt = apple_row["Event Start Date Time (US/Eastern)"]
        assert eastern_dt.hour == 16  # 4 PM

        # Check time display string
        time_str = apple_row["Event Time (US/Eastern)"]
        assert "04:00 PM" in time_str
        assert "EDT" in time_str or "EST" in time_str

    def test_add_timezone_converted_columns_with_missing_times(self):
        """Test handling of missing times (NaN/None)."""
        df = pd.DataFrame(
            {
                "Instrument": ["AAPL.O", "MSFT.O"],
                "Event Start Date Time": [
                    datetime(2025, 10, 30, 20, 0, 0),
                    None,  # Missing time
                ],
            }
        )

        result = add_timezone_converted_columns(df, "US/Eastern")

        # First row should have converted time
        assert pd.notna(result.iloc[0]["Event Time (US/Eastern)"])

        # Second row should have None/NaN
        assert pd.isna(result.iloc[1]["Event Time (US/Eastern)"])

    def test_add_timezone_converted_columns_midnight_times(self):
        """Test handling of midnight times (likely just dates, no specific time)."""
        df = pd.DataFrame(
            {
                "Instrument": ["AAPL.O"],
                "Event Start Date Time": [
                    datetime(2025, 10, 30, 0, 0, 0)  # Midnight
                ],
            }
        )

        result = add_timezone_converted_columns(df, "US/Eastern")

        # Midnight times should pass through without conversion
        # (indicates date only, time TBD)
        time_str = result.iloc[0]["Event Time (US/Eastern)"]
        assert pd.isna(time_str) or time_str is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
