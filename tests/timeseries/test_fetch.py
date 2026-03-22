"""
Unit tests for the fetch module.

Tests symbol resolution, column normalization, and response parsing.
These tests use mocks and don't require LSEG Workspace.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.timeseries.constants import (
    BOND_COLUMN_MAPPING,
    QUOTE_COLUMN_MAPPING,
    RATE_COLUMN_MAPPING,
)
from lseg_toolkit.timeseries.enums import AssetClass, Granularity
from lseg_toolkit.timeseries.fetch import (
    GRANULARITY_TO_INTERVAL,
    _drop_sparse_intraday_ohlcv_rows,
    _normalize_columns,
    _split_multi_ric_response,
    fetch_timeseries,
    resolve_ric,
)


class TestResolveRic:
    """Test symbol resolution to LSEG RICs."""

    def test_passthrough_ric_with_equals(self):
        """RICs ending with = should pass through unchanged."""
        assert resolve_ric("EUR=") == "EUR="
        assert resolve_ric("USD1MOIS=") == "USD1MOIS="
        assert resolve_ric("US10YT=RRPS") == "US10YT=RRPS"

    def test_passthrough_ric_with_continuous(self):
        """RICs containing c1/c2 should pass through unchanged."""
        assert resolve_ric("TYc1") == "TYc1"
        assert resolve_ric("FGBLc1") == "FGBLc1"
        assert resolve_ric("ESc2") == "ESc2"

    def test_futures_cme_to_lseg(self):
        """CME symbols should map to LSEG RICs."""
        assert resolve_ric("ZN") == "TYc1"
        assert resolve_ric("ZB") == "USc1"
        assert resolve_ric("ZF") == "FVc1"
        assert resolve_ric("ZT") == "TUc1"

    def test_futures_case_insensitive(self):
        """Futures resolution should be case-insensitive."""
        assert resolve_ric("zn") == "TYc1"
        assert resolve_ric("Zn") == "TYc1"
        assert resolve_ric("ZN") == "TYc1"

    def test_fx_pair_resolution(self):
        """FX pair symbols should map to RICs."""
        assert resolve_ric("EURUSD") == "EUR="
        assert resolve_ric("GBPUSD") == "GBP="
        assert resolve_ric("USDJPY") == "JPY="

    def test_fx_case_insensitive(self):
        """FX resolution should be case-insensitive."""
        assert resolve_ric("eurusd") == "EUR="
        assert resolve_ric("EurUsd") == "EUR="

    def test_ois_with_asset_class_hint(self):
        """OIS symbols should add = suffix when asset class specified."""
        assert resolve_ric("USD1MOIS", asset_class=AssetClass.OIS) == "USD1MOIS="
        assert resolve_ric("USD1YOIS", asset_class=AssetClass.OIS) == "USD1YOIS="

    def test_ois_auto_detect(self):
        """OIS symbols should be detected by OIS in name."""
        assert resolve_ric("USD1MOIS") == "USD1MOIS="
        assert resolve_ric("USD10YOIS") == "USD10YOIS="

    def test_stir_symbol_resolution(self):
        """Fed Funds continuous internal symbol should resolve to FFc1."""
        assert resolve_ric("FF_CONTINUOUS") == "FFc1"
        assert resolve_ric("ff_continuous") == "FFc1"
        assert resolve_ric("FF_CONTINUOUS_12") == "FFc12"
        assert resolve_ric("FFc12") == "FFc12"


class TestNormalizeColumns:
    """Test column name normalization from LSEG to storage schema."""

    def test_normalize_ohlcv_columns(self):
        """OHLCV columns should be normalized correctly."""
        df = pd.DataFrame(
            {
                "OPEN_PRC": [100.0],
                "HIGH_1": [101.0],
                "LOW_1": [99.0],
                "TRDPRC_1": [100.5],
                "ACVOL_UNS": [1000],
            }
        )

        result = _normalize_columns(df)

        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns

    def test_normalize_fx_columns(self):
        """FX columns should be normalized correctly."""
        df = pd.DataFrame(
            {
                "BID": [1.0850],
                "ASK": [1.0852],
                "BID_HIGH_1": [1.0860],
                "BID_LOW_1": [1.0840],
            }
        )

        result = _normalize_columns(df, QUOTE_COLUMN_MAPPING)

        assert "bid" in result.columns
        assert "ask" in result.columns
        assert "bid_high" in result.columns
        assert "bid_low" in result.columns

    def test_normalize_rate_columns(self):
        """Rate columns should normalize to rate-specific names."""
        df = pd.DataFrame(
            {
                "BID": [4.10],
                "ASK": [4.12],
                "PRIMACT_1": [4.11],
                "BID_HIGH_1": [4.15],
                "BID_LOW_1": [4.05],
            }
        )

        result = _normalize_columns(df, RATE_COLUMN_MAPPING)

        assert "bid" in result.columns
        assert "ask" in result.columns
        assert "rate" in result.columns
        assert "high_rate" in result.columns
        assert "low_rate" in result.columns

    def test_normalize_bond_columns(self):
        """Bond/yield columns should normalize to bond-specific names."""
        df = pd.DataFrame(
            {
                "OPEN_PRC": [99.5],
                "MID_YLD_1": [4.25],
                "BID": [99.4],
                "ASK": [99.6],
            }
        )

        result = _normalize_columns(df, BOND_COLUMN_MAPPING)

        assert "open_price" in result.columns
        assert "yield" in result.columns
        assert "bid" in result.columns
        assert "ask" in result.columns

    def test_normalize_preserves_unknown_columns(self):
        """Unknown columns should be preserved."""
        df = pd.DataFrame(
            {
                "CUSTOM_FIELD": [1.0],
                "ANOTHER_FIELD": [2.0],
            }
        )

        result = _normalize_columns(df)

        # Unknown columns are preserved (may be lowercased or not)
        assert len(result.columns) == 2

    def test_normalize_empty_dataframe(self):
        """Empty DataFrames should not raise errors."""
        df = pd.DataFrame()
        result = _normalize_columns(df)
        assert result.empty


class TestSparseIntradayFiltering:
    """Test early filtering of sparse intraday OHLCV rows."""

    def test_drop_sparse_intraday_ohlcv_rows(self):
        """Intraday OHLCV rows with null close should be dropped."""
        df = pd.DataFrame(
            {
                "open": [110.0, None],
                "high": [111.0, None],
                "low": [109.5, None],
                "close": [110.5, None],
                "volume": [1000, 250],
            },
            index=pd.to_datetime(["2026-03-20 14:00", "2026-03-20 15:00"]),
        )

        result = _drop_sparse_intraday_ohlcv_rows(
            df,
            granularity=Granularity.HOURLY,
        )

        assert len(result) == 1
        assert result.index[0] == pd.Timestamp("2026-03-20 14:00")

    def test_fetch_timeseries_drops_sparse_intraday_rows_after_normalization(self):
        """Sparse rows should be removed directly from the generic fetch path."""
        mock_client = MagicMock()
        mock_client.get_history.return_value = pd.DataFrame(
            {
                "OPEN_PRC": [110.0, None],
                "HIGH_1": [111.0, None],
                "LOW_1": [109.5, None],
                "TRDPRC_1": [110.5, None],
                "ACVOL_UNS": [1000, 250],
            },
            index=pd.to_datetime(["2026-03-20 14:00", "2026-03-20 15:00"]),
        )

        result = fetch_timeseries(
            rics=["TYc1"],
            start_date=date(2026, 3, 20),
            end_date=date(2026, 3, 21),
            granularity=Granularity.HOURLY,
            client=mock_client,
        )

        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert len(result) == 1
        assert result["close"].notna().all()


class TestGranularityMapping:
    """Test granularity to LSEG interval mapping."""

    def test_daily_mapping(self):
        """Daily granularity maps to 'daily'."""
        assert GRANULARITY_TO_INTERVAL[Granularity.DAILY] == "daily"

    def test_hourly_mapping(self):
        """Hourly granularity maps to 'hourly'."""
        assert GRANULARITY_TO_INTERVAL[Granularity.HOURLY] == "hourly"

    def test_minute_mappings(self):
        """Minute granularities map correctly."""
        assert GRANULARITY_TO_INTERVAL[Granularity.MINUTE_1] == "1min"
        assert GRANULARITY_TO_INTERVAL[Granularity.MINUTE_5] == "5min"
        assert GRANULARITY_TO_INTERVAL[Granularity.MINUTE_30] == "30min"

    def test_all_granularities_have_mapping(self):
        """All Granularity enum values should have mappings."""
        for granularity in Granularity:
            assert granularity in GRANULARITY_TO_INTERVAL


class TestFetchWithMocks:
    """Test fetch functions with mocked LSEG API calls."""

    @patch("lseg_toolkit.timeseries.fetch.fetch_timeseries")
    def test_fetch_futures_returns_dict(self, mock_fetch_timeseries):
        """fetch_futures should return dict of DataFrames."""
        from lseg_toolkit.timeseries.fetch import fetch_futures

        mock_fetch_timeseries.return_value = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [101.0, 102.0],
                "low": [99.0, 100.0],
                "close": [100.5, 101.5],
                "volume": [1000, 1100],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

        result = fetch_futures(
            ["TYc1"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            granularity=Granularity.DAILY,
        )

        assert isinstance(result, dict)
        mock_fetch_timeseries.assert_called_once()

    @patch("lseg_toolkit.timeseries.fetch.fetch_timeseries")
    def test_fetch_fx_returns_dict(self, mock_fetch_timeseries):
        """fetch_fx should return dict of DataFrames."""
        from lseg_toolkit.timeseries.fetch import fetch_fx

        mock_fetch_timeseries.return_value = pd.DataFrame(
            {
                "bid": [1.0850],
                "ask": [1.0852],
            },
            index=pd.to_datetime(["2024-01-01"]),
        )

        result = fetch_fx(
            ["EURUSD"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert isinstance(result, dict)
        mock_fetch_timeseries.assert_called_once()


class TestSplitMultiRicResponse:
    """Test multi-RIC response splitting logic."""

    def test_split_single_ric_returns_dict(self):
        """Single RIC should return dict with one entry."""
        df = pd.DataFrame({"close": [100.0, 101.0]}, index=["2024-01-01", "2024-01-02"])
        key_to_ric = {"ZN": "TYc1"}

        result = _split_multi_ric_response(df, key_to_ric)

        assert len(result) == 1
        assert "ZN" in result
        assert len(result["ZN"]) == 2

    def test_split_with_instrument_column(self):
        """Multi-RIC with 'Instrument' column should split correctly."""
        df = pd.DataFrame(
            {
                "Instrument": ["TYc1", "TYc1", "USc1", "USc1"],
                "close": [100.0, 101.0, 150.0, 151.0],
                "date": ["2024-01-01", "2024-01-02", "2024-01-01", "2024-01-02"],
            }
        )
        key_to_ric = {"ZN": "TYc1", "ZB": "USc1"}

        result = _split_multi_ric_response(df, key_to_ric)

        assert len(result) == 2
        assert "ZN" in result
        assert "ZB" in result
        assert len(result["ZN"]) == 2
        assert len(result["ZB"]) == 2
        # Instrument column should be dropped
        assert "Instrument" not in result["ZN"].columns

    def test_split_with_multiindex(self):
        """Multi-RIC with MultiIndex should split correctly."""
        # Create MultiIndex DataFrame (date, ric)
        idx = pd.MultiIndex.from_tuples(
            [
                ("2024-01-01", "TYc1"),
                ("2024-01-02", "TYc1"),
                ("2024-01-01", "USc1"),
                ("2024-01-02", "USc1"),
            ],
            names=["date", "ric"],
        )
        df = pd.DataFrame({"close": [100.0, 101.0, 150.0, 151.0]}, index=idx)
        key_to_ric = {"ZN": "TYc1", "ZB": "USc1"}

        result = _split_multi_ric_response(df, key_to_ric)

        assert len(result) == 2
        assert "ZN" in result
        assert "ZB" in result

    def test_split_empty_dataframe(self):
        """Empty DataFrame should return empty dict."""
        df = pd.DataFrame()
        key_to_ric = {"ZN": "TYc1"}

        result = _split_multi_ric_response(df, key_to_ric)

        assert result == {}

    def test_split_missing_ric_in_response(self):
        """Missing RIC in response should not be included."""
        df = pd.DataFrame(
            {
                "Instrument": ["TYc1", "TYc1"],
                "close": [100.0, 101.0],
            }
        )
        key_to_ric = {"ZN": "TYc1", "ZB": "USc1"}  # USc1 not in response

        result = _split_multi_ric_response(df, key_to_ric)

        assert "ZN" in result
        assert "ZB" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
