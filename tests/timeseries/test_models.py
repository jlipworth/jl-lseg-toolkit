"""Tests for timeseries models and config."""

from datetime import date, datetime

import pandas as pd
import pytest

from lseg_toolkit.timeseries import (
    OHLCV,
    AssetClass,
    ContinuousType,
    FuturesContract,
    FuturesMonth,
    FXSpot,
    Granularity,
    Instrument,
    OISRate,
    RollEvent,
    RollMethod,
    TimeSeries,
    TimeSeriesConfig,
)


class TestTimeSeriesConfig:
    """Tests for TimeSeriesConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = TimeSeriesConfig()
        assert config.symbols == []
        assert config.asset_class is None
        assert config.granularity == Granularity.DAILY
        assert config.continuous is False
        assert config.continuous_type == ContinuousType.RATIO_ADJUSTED
        assert config.roll_method == RollMethod.VOLUME_SWITCH

    def test_custom_config(self):
        """Test custom configuration."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        config = TimeSeriesConfig(
            symbols=["ZN", "ZB"],
            asset_class=AssetClass.BOND_FUTURES,
            start_date=start,
            end_date=end,
            granularity=Granularity.DAILY,  # Use daily for full year
            continuous=True,
        )
        assert config.symbols == ["ZN", "ZB"]
        assert config.asset_class == AssetClass.BOND_FUTURES
        assert config.start_date == start
        assert config.end_date == end
        assert config.granularity == Granularity.DAILY
        assert config.continuous is True

    def test_date_validation(self):
        """Test date range validation."""
        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            TimeSeriesConfig(
                symbols=["ZN"],
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
            )

    def test_intraday_date_range_validation(self):
        """Test intraday data date range limit (365 days max)."""
        with pytest.raises(
            ValueError, match="Intraday data only available for ~365 days"
        ):
            TimeSeriesConfig(
                symbols=["ZN"],
                start_date=date(2023, 1, 1),
                end_date=date(2024, 12, 31),  # > 365 days
                granularity=Granularity.MINUTE_5,
            )

    def test_datetime_conversion(self):
        """Test datetime to date conversion."""
        config = TimeSeriesConfig(
            symbols=["ZN"],
            start_date=datetime(2024, 1, 1, 12, 0, 0),
            end_date=datetime(2024, 1, 31, 18, 0, 0),
        )
        assert config.start_date == date(2024, 1, 1)
        assert config.end_date == date(2024, 1, 31)

    def test_to_dict(self):
        """Test config serialization."""
        config = TimeSeriesConfig(
            symbols=["ZN"],
            asset_class=AssetClass.BOND_FUTURES,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        d = config.to_dict()
        assert d["symbols"] == ["ZN"]
        assert d["asset_class"] == "bond_futures"
        assert d["start_date"] == "2024-01-01"
        assert d["end_date"] == "2024-12-31"


class TestEnums:
    """Tests for enums."""

    def test_asset_class_values(self):
        """Test asset class enum values."""
        assert AssetClass.BOND_FUTURES.value == "bond_futures"
        assert AssetClass.FX_SPOT.value == "fx_spot"
        assert AssetClass.OIS.value == "ois"

    def test_granularity_values(self):
        """Test granularity enum values."""
        assert Granularity.DAILY.value == "daily"
        assert Granularity.HOURLY.value == "hourly"
        assert Granularity.MINUTE_1.value == "1min"

    def test_continuous_type_values(self):
        """Test continuous type enum values."""
        assert ContinuousType.DISCRETE.value == "discrete"
        assert ContinuousType.UNADJUSTED.value == "unadjusted"
        assert ContinuousType.RATIO_ADJUSTED.value == "ratio_adjusted"

    def test_roll_method_values(self):
        """Test roll method enum values."""
        assert RollMethod.VOLUME_SWITCH.value == "volume_switch"
        assert RollMethod.FIRST_NOTICE.value == "first_notice"
        assert RollMethod.FIXED_DAYS.value == "fixed_days"

    def test_futures_month_values(self):
        """Test futures month enum values."""
        assert FuturesMonth.H.value == "H"  # March
        assert FuturesMonth.M.value == "M"  # June
        assert FuturesMonth.U.value == "U"  # September
        assert FuturesMonth.Z.value == "Z"  # December


class TestInstrumentModels:
    """Tests for instrument dataclasses."""

    def test_instrument_base(self):
        """Test base Instrument class."""
        inst = Instrument(
            symbol="ZN",
            lseg_ric="TYc1",
            name="10-Year T-Note",
            asset_class=AssetClass.BOND_FUTURES,
        )
        assert inst.symbol == "ZN"
        assert inst.lseg_ric == "TYc1"
        assert inst.asset_class == AssetClass.BOND_FUTURES

    def test_instrument_validation(self):
        """Test instrument validation."""
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            Instrument(
                symbol="",
                lseg_ric="TYc1",
                name="Test",
                asset_class=AssetClass.BOND_FUTURES,
            )

    def test_futures_contract(self):
        """Test FuturesContract class."""
        contract = FuturesContract(
            symbol="TYH25",
            lseg_ric="TYH5",
            name="10-Year T-Note Mar 2025",
            asset_class=AssetClass.BOND_FUTURES,
            underlying="TY",
            expiry_month="H",
            expiry_year=25,
        )
        assert contract.underlying == "TY"
        assert contract.expiry_month == "H"
        assert contract.is_continuous is False

    def test_futures_contract_continuous(self):
        """Test continuous futures contract."""
        contract = FuturesContract(
            symbol="ZN",
            lseg_ric="TYc1",
            name="10-Year Continuous",
            asset_class=AssetClass.BOND_FUTURES,
            continuous_type=ContinuousType.RATIO_ADJUSTED,
        )
        assert contract.is_continuous is True

    def test_fx_spot(self):
        """Test FXSpot class."""
        fx = FXSpot(
            symbol="EURUSD",
            lseg_ric="EUR=",
            name="EUR/USD",
            asset_class=AssetClass.FX_SPOT,
        )
        assert fx.base_currency == "EUR"
        assert fx.quote_currency == "USD"
        assert fx.pip_size == 0.0001

    def test_fx_spot_jpy(self):
        """Test FXSpot JPY pip size."""
        fx = FXSpot(
            symbol="USDJPY",
            lseg_ric="JPY=",
            name="USD/JPY",
            asset_class=AssetClass.FX_SPOT,
            quote_currency="JPY",
        )
        assert fx.pip_size == 0.01

    def test_ois_rate(self):
        """Test OISRate class."""
        ois = OISRate(
            symbol="USD1MOIS",
            lseg_ric="USD1MOIS=",
            name="USD 1M OIS",
            asset_class=AssetClass.OIS,
            currency="USD",
            tenor="1M",
        )
        assert ois.currency == "USD"
        assert ois.tenor == "1M"
        assert ois.reference_rate == "SOFR"


class TestTimeSeriesModels:
    """Tests for time series dataclasses."""

    def test_ohlcv_basic(self):
        """Test OHLCV dataclass."""
        bar = OHLCV(
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            open=110.0,
            high=110.5,
            low=109.5,
            close=110.25,
            volume=100000,
        )
        assert bar.open == 110.0
        assert bar.close == 110.25
        assert bar.date == date(2024, 1, 15)

    def test_ohlcv_mid(self):
        """Test OHLCV mid price calculation."""
        bar = OHLCV(
            timestamp=datetime(2024, 1, 15),
            high=110.0,
            low=109.0,
            close=109.5,
        )
        assert bar.mid == 109.5

    def test_timeseries_basic(self):
        """Test TimeSeries dataclass."""
        ts = TimeSeries(
            symbol="ZN",
            lseg_ric="TYc1",
            granularity=Granularity.DAILY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert ts.symbol == "ZN"
        assert ts.is_empty is True
        assert len(ts) == 0

    def test_timeseries_with_data(self):
        """Test TimeSeries with DataFrame."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=dates)

        ts = TimeSeries(
            symbol="ZN",
            lseg_ric="TYc1",
            granularity=Granularity.DAILY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            data=df,
        )
        assert ts.is_empty is False
        assert len(ts) == 5
        assert ts.first_date == date(2024, 1, 1)
        assert ts.last_date == date(2024, 1, 5)

    def test_roll_event(self):
        """Test RollEvent dataclass."""
        event = RollEvent(
            roll_date=date(2024, 3, 15),
            from_contract="TYH24",
            to_contract="TYM24",
            from_price=110.0,
            to_price=110.5,
            roll_method="volume_switch",
        )
        assert event.price_gap == 0.5
        assert event.adjustment_factor == pytest.approx(110.5 / 110.0, rel=1e-6)

    def test_roll_event_to_dict(self):
        """Test RollEvent serialization."""
        event = RollEvent(
            roll_date=date(2024, 3, 15),
            from_contract="TYH24",
            to_contract="TYM24",
            from_price=110.0,
            to_price=110.5,
        )
        d = event.to_dict()
        assert d["roll_date"] == "2024-03-15"
        assert d["from_contract"] == "TYH24"
        assert d["to_contract"] == "TYM24"
