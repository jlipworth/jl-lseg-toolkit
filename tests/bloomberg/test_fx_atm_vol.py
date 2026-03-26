from datetime import date

import pandas as pd
import pytest

from lseg_toolkit.bloomberg import fx_atm_vol as fx_module
from lseg_toolkit.exceptions import ConfigurationError


def test_generate_fx_atm_vol_tickers_uses_validated_pattern():
    tickers = fx_module.generate_fx_atm_vol_tickers(["EURUSD"], ["1M"])

    assert tickers == [
        {
            "ticker": "EURUSDV1M BGN Curncy",
            "pair": "EURUSD",
            "tenor": "1M",
        }
    ]


def test_generate_fx_atm_vol_tickers_builds_grid():
    tickers = fx_module.generate_fx_atm_vol_tickers(["EURUSD", "USDJPY"], ["1M", "3M"])
    assert len(tickers) == 4


def test_generate_fx_atm_vol_tickers_normalizes_case():
    tickers = fx_module.generate_fx_atm_vol_tickers(["eurusd"], ["1m"])
    assert tickers[0]["ticker"] == "EURUSDV1M BGN Curncy"


def test_generate_fx_atm_vol_tickers_rejects_unknown_pairs():
    with pytest.raises(ConfigurationError):
        fx_module.generate_fx_atm_vol_tickers(["EURGBP"], ["1M"])


def test_generate_fx_atm_vol_tickers_rejects_unknown_tenors():
    with pytest.raises(ConfigurationError):
        fx_module.generate_fx_atm_vol_tickers(["EURUSD"], ["18M"])


def test_extract_fx_atm_vol_snapshot_normalizes_supported_schema(monkeypatch):
    snapshot_df = pd.DataFrame(
        [
            {
                "security": "USDJPYV1M BGN Curncy",
                "PX_LAST": 8.4,
                "NAME": "USD-JPY OPT VOL 1M",
                "LAST_UPDATE": "2026-03-24T10:00:00",
                "_security_error": None,
            },
            {
                "security": "EURUSDV1M BGN Curncy",
                "PX_LAST": 4.99,
                "NAME": "EUR-USD OPT VOL 1M",
                "LAST_UPDATE": "2026-03-24T10:00:00",
                "_security_error": None,
            },
            {
                "security": "EURUSDV3M BGN Curncy",
                "PX_LAST": None,
                "NAME": "EUR-USD OPT VOL 3M",
                "LAST_UPDATE": "2026-03-24T10:00:00",
                "_security_error": "no value",
            },
        ]
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get_reference_data(self, securities, fields):
            assert fields == fx_module.FX_ATM_VOL_FIELDS
            return snapshot_df

    monkeypatch.setattr(fx_module, "BloombergSession", FakeSession)

    result = fx_module.extract_fx_atm_vol_snapshot(
        pairs=["USDJPY", "EURUSD"],
        tenors=["1M", "3M"],
    )

    assert list(result.columns) == [
        "pair",
        "tenor",
        "atm_vol",
        "name",
        "last_update",
        "source",
        "quote_type",
        "ticker",
        "extract_date",
        "_security_error",
    ]
    assert list(result["pair"]) == ["EURUSD", "USDJPY"]
    assert list(result["tenor"]) == ["1M", "1M"]
    assert list(result["atm_vol"]) == [4.99, 8.4]
    assert set(result["source"]) == {"bloomberg"}
    assert set(result["quote_type"]) == {"atm_vol"}


def test_extract_fx_atm_vol_historical_normalizes_supported_schema(monkeypatch):
    historical_df = pd.DataFrame(
        [
            {
                "date": date(2026, 3, 24),
                "security": "USDJPYV1M BGN Curncy",
                "PX_LAST": 8.4,
                "_security_error": None,
            },
            {
                "date": date(2026, 3, 24),
                "security": "EURUSDV1M BGN Curncy",
                "PX_LAST": 4.99,
                "_security_error": None,
            },
        ]
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get_historical_data(self, securities, fields, start_date, end_date):
            assert fields == ["PX_LAST"]
            assert start_date == date(2026, 3, 1)
            assert end_date == date(2026, 3, 24)
            return historical_df

    monkeypatch.setattr(fx_module, "BloombergSession", FakeSession)

    result = fx_module.extract_fx_atm_vol_historical(
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 24),
        pairs=["USDJPY", "EURUSD"],
        tenors=["1M"],
    )

    assert list(result.columns) == [
        "date",
        "pair",
        "tenor",
        "atm_vol",
        "source",
        "quote_type",
        "ticker",
        "_security_error",
    ]
    assert list(result["pair"]) == ["EURUSD", "USDJPY"]
    assert list(result["atm_vol"]) == [4.99, 8.4]
