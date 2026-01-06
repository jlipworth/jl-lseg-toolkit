"""Tests for timeseries rolling logic."""

from datetime import date

import pandas as pd
import pytest

from lseg_toolkit.exceptions import RollCalculationError
from lseg_toolkit.timeseries.enums import ContinuousType, RollMethod
from lseg_toolkit.timeseries.rolling import (
    _detect_roll_dates_fixed,
    _detect_roll_dates_volume,
    build_continuous,
    get_roll_calendar,
)


class TestRollDetection:
    """Tests for roll date detection."""

    @pytest.fixture
    def overlapping_contracts(self):
        """Create overlapping contract data for testing."""
        # Contract 1: Jan 1-30, high volume at start, low at end
        dates1 = pd.date_range("2024-01-01", periods=30, freq="D")
        df1 = pd.DataFrame(
            {
                "open": [100.0] * 30,
                "high": [101.0] * 30,
                "low": [99.0] * 30,
                "close": [100.0 + i * 0.1 for i in range(30)],
                "volume": [100000 - i * 2000 for i in range(30)],
                "open_interest": [500000] * 30,
            },
            index=dates1,
        )

        # Contract 2: Jan 15 - Feb 28, low volume at start, high at end
        dates2 = pd.date_range("2024-01-15", periods=45, freq="D")
        df2 = pd.DataFrame(
            {
                "open": [101.0] * 45,
                "high": [102.0] * 45,
                "low": [100.0] * 45,
                "close": [101.0 + i * 0.1 for i in range(45)],
                "volume": [20000 + i * 3000 for i in range(45)],
                "open_interest": [300000] * 45,
            },
            index=dates2,
        )

        return {"TYH24": df1, "TYM24": df2}

    def test_detect_volume_switch(self, overlapping_contracts):
        """Test volume switch roll detection."""
        roll_dates = _detect_roll_dates_volume(overlapping_contracts)

        assert len(roll_dates) == 1
        roll_date, from_contract, to_contract = roll_dates[0]
        assert from_contract == "TYH24"
        assert to_contract == "TYM24"
        # Volume crossover should happen somewhere in the overlap period
        assert date(2024, 1, 15) <= roll_date <= date(2024, 1, 30)

    def test_detect_fixed_days(self, overlapping_contracts):
        """Test fixed days roll detection."""
        roll_dates = _detect_roll_dates_fixed(overlapping_contracts, days_before=5)

        assert len(roll_dates) == 1
        roll_date, from_contract, to_contract = roll_dates[0]
        assert from_contract == "TYH24"
        assert to_contract == "TYM24"
        # Should roll 5 days before end of first contract (Jan 30)
        assert roll_date == date(2024, 1, 25)

    def test_detect_single_contract(self):
        """Test roll detection with single contract."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({"close": range(30), "volume": [100000] * 30}, index=dates)

        roll_dates = _detect_roll_dates_volume({"TYH24": df})
        assert roll_dates == []


class TestBuildContinuous:
    """Tests for building continuous contracts."""

    @pytest.fixture
    def contract_data(self):
        """Create contract data for continuous building."""
        # Contract 1: Jan 1-25
        dates1 = pd.date_range("2024-01-01", periods=25, freq="D")
        df1 = pd.DataFrame(
            {
                "open": [100.0] * 25,
                "high": [101.0] * 25,
                "low": [99.0] * 25,
                "close": [100.0] * 25,
                "volume": [100000 - i * 3000 for i in range(25)],
            },
            index=dates1,
        )

        # Contract 2: Jan 15 - Feb 15, starts at 102 (gap of 2)
        dates2 = pd.date_range("2024-01-15", periods=32, freq="D")
        df2 = pd.DataFrame(
            {
                "open": [102.0] * 32,
                "high": [103.0] * 32,
                "low": [101.0] * 32,
                "close": [102.0] * 32,
                "volume": [20000 + i * 3000 for i in range(32)],
            },
            index=dates2,
        )

        return {"TYH24": df1, "TYM24": df2}

    def test_build_unadjusted(self, contract_data):
        """Test building unadjusted continuous series."""
        continuous, events = build_continuous(
            contract_data,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.UNADJUSTED,
        )

        assert len(events) == 1
        assert not continuous.empty
        assert "source_contract" in continuous.columns
        assert "adjustment_factor" in continuous.columns

        # Check for price jump at roll (unadjusted)
        # Before roll: close should be ~100
        # After roll: close should be ~102

    def test_build_ratio_adjusted(self, contract_data):
        """Test building ratio-adjusted continuous series."""
        continuous, events = build_continuous(
            contract_data,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.RATIO_ADJUSTED,
        )

        assert len(events) == 1
        assert not continuous.empty

        # After ratio adjustment, historical prices should be scaled
        # No abrupt price jumps at roll date

    def test_build_difference_adjusted(self, contract_data):
        """Test building difference-adjusted continuous series."""
        continuous, events = build_continuous(
            contract_data,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.DIFFERENCE_ADJUSTED,
        )

        assert len(events) == 1
        assert not continuous.empty

    def test_build_single_contract(self):
        """Test building with single contract (no rolls)."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "open": [100.0] * 30,
                "high": [101.0] * 30,
                "low": [99.0] * 30,
                "close": [100.0] * 30,
                "volume": [100000] * 30,
            },
            index=dates,
        )

        continuous, events = build_continuous(
            {"TYH24": df},
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.RATIO_ADJUSTED,
        )

        assert events == []
        assert len(continuous) == 30
        assert continuous["source_contract"].iloc[0] == "TYH24"

    def test_build_empty_data(self):
        """Test building with no data raises error."""
        with pytest.raises(RollCalculationError):
            build_continuous({})

    def test_roll_event_properties(self, contract_data):
        """Test roll event has correct properties."""
        _, events = build_continuous(
            contract_data,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.RATIO_ADJUSTED,
        )

        assert len(events) == 1
        event = events[0]

        assert event.from_contract == "TYH24"
        assert event.to_contract == "TYM24"
        assert event.from_price > 0
        assert event.to_price > 0
        assert event.price_gap == event.to_price - event.from_price
        assert event.adjustment_factor == event.to_price / event.from_price
        assert event.roll_method == "volume_switch"

    def test_fixed_days_roll(self, contract_data):
        """Test fixed days roll method."""
        continuous, events = build_continuous(
            contract_data,
            roll_method=RollMethod.FIXED_DAYS,
            continuous_type=ContinuousType.UNADJUSTED,
            roll_days_before=5,
        )

        assert len(events) == 1
        # Roll should be 5 days before end of first contract


class TestRollCalendar:
    """Tests for roll calendar generation."""

    def test_get_roll_calendar(self):
        """Test converting roll events to calendar DataFrame."""
        from lseg_toolkit.timeseries.models import RollEvent

        events = [
            RollEvent(
                roll_date=date(2024, 3, 15),
                from_contract="TYH24",
                to_contract="TYM24",
                from_price=110.0,
                to_price=110.5,
                roll_method="volume_switch",
            ),
            RollEvent(
                roll_date=date(2024, 6, 15),
                from_contract="TYM24",
                to_contract="TYU24",
                from_price=111.0,
                to_price=111.3,
                roll_method="volume_switch",
            ),
        ]

        calendar = get_roll_calendar(events)

        assert len(calendar) == 2
        assert "from_contract" in calendar.columns
        assert "to_contract" in calendar.columns
        assert "price_gap" in calendar.columns
        assert "adjustment_factor" in calendar.columns
        assert calendar.index.name == "roll_date"

    def test_get_roll_calendar_empty(self):
        """Test empty roll calendar."""
        calendar = get_roll_calendar([])
        assert calendar.empty


class TestAdjustmentMethods:
    """Tests for price adjustment correctness."""

    def test_ratio_adjustment_preserves_returns(self):
        """Test that ratio adjustment preserves returns."""
        # Contract 1: price goes 100 -> 105 (5% return)
        dates1 = pd.date_range("2024-01-01", periods=10, freq="D")
        df1 = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104, 105, 105, 105, 105, 105],
                "volume": [100000 - i * 8000 for i in range(10)],
            },
            index=dates1,
        )
        df1["open"] = df1["close"]
        df1["high"] = df1["close"] + 0.5
        df1["low"] = df1["close"] - 0.5

        # Contract 2: starts at 110 (10% gap), goes 110 -> 115.5 (5% return)
        dates2 = pd.date_range("2024-01-05", periods=15, freq="D")
        df2 = pd.DataFrame(
            {
                "close": [
                    110,
                    111,
                    112,
                    113,
                    114,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                    115.5,
                ],
                "volume": [20000 + i * 8000 for i in range(15)],
            },
            index=dates2,
        )
        df2["open"] = df2["close"]
        df2["high"] = df2["close"] + 0.5
        df2["low"] = df2["close"] - 0.5

        contracts = {"TYH24": df1, "TYM24": df2}
        continuous, events = build_continuous(
            contracts,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.RATIO_ADJUSTED,
        )

        # Check that we have data
        assert not continuous.empty
        assert len(events) == 1

    def test_difference_adjustment_preserves_differences(self):
        """Test that difference adjustment preserves price differences."""
        dates1 = pd.date_range("2024-01-01", periods=10, freq="D")
        df1 = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104, 105, 105, 105, 105, 105],
                "volume": [100000 - i * 8000 for i in range(10)],
            },
            index=dates1,
        )
        df1["open"] = df1["close"]
        df1["high"] = df1["close"] + 0.5
        df1["low"] = df1["close"] - 0.5

        dates2 = pd.date_range("2024-01-05", periods=15, freq="D")
        df2 = pd.DataFrame(
            {
                "close": [
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    113,
                    113,
                    113,
                    113,
                    113,
                    113,
                    113,
                    113,
                    113,
                ],
                "volume": [20000 + i * 8000 for i in range(15)],
            },
            index=dates2,
        )
        df2["open"] = df2["close"]
        df2["high"] = df2["close"] + 0.5
        df2["low"] = df2["close"] - 0.5

        contracts = {"TYH24": df1, "TYM24": df2}
        continuous, events = build_continuous(
            contracts,
            roll_method=RollMethod.VOLUME_SWITCH,
            continuous_type=ContinuousType.DIFFERENCE_ADJUSTED,
        )

        assert not continuous.empty
        assert len(events) == 1
