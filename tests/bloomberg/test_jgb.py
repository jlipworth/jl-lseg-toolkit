from datetime import date

import pandas as pd
import pytest

from lseg_toolkit.bloomberg import jgb as jgb_module
from lseg_toolkit.exceptions import ConfigurationError


def test_get_jgb_tickers_returns_all_by_default():
    tickers = jgb_module.get_jgb_tickers()
    assert tickers == jgb_module.JGB_TICKERS


def test_get_jgb_tickers_normalizes_case():
    tickers = jgb_module.get_jgb_tickers(["2y", "10y"])
    assert tickers == {
        "2Y": "GJGB2 Index",
        "10Y": "GJGB10 Index",
    }


def test_get_jgb_tickers_rejects_unknown_tenors():
    with pytest.raises(ConfigurationError):
        jgb_module.get_jgb_tickers(["2Y", "99Y"])


def test_extract_jgb_snapshot_normalizes_supported_schema(monkeypatch):
    snapshot_df = pd.DataFrame(
        [
            {
                "security": "GJGB10 Index",
                "PX_LAST": 2.19,
                "NAME": "JGB 10Y",
                "LAST_UPDATE": "2026-03-24T10:00:00",
                "_security_error": None,
            },
            {
                "security": "GJGB2 Index",
                "PX_LAST": 1.20,
                "NAME": "JGB 2Y",
                "LAST_UPDATE": "2026-03-24T10:00:00",
                "_security_error": None,
            },
        ]
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get_reference_data(self, securities, fields):
            assert securities == ["GJGB10 Index", "GJGB2 Index"]
            assert fields == jgb_module.JGB_FIELDS
            return snapshot_df

    monkeypatch.setattr(jgb_module, "BloombergSession", FakeSession)

    result = jgb_module.extract_jgb_snapshot(["10Y", "2Y"])

    assert list(result.columns) == [
        "tenor",
        "yield",
        "name",
        "last_update",
        "currency",
        "instrument",
        "source",
        "ticker",
        "extract_date",
        "_security_error",
    ]
    assert list(result["tenor"]) == ["2Y", "10Y"]
    assert list(result["yield"]) == [1.20, 2.19]
    assert set(result["currency"]) == {"JPY"}
    assert set(result["instrument"]) == {"jgb_yield"}
    assert set(result["source"]) == {"bloomberg"}


def test_extract_jgb_historical_normalizes_supported_schema(monkeypatch):
    historical_df = pd.DataFrame(
        [
            {
                "date": date(2026, 3, 24),
                "security": "GJGB10 Index",
                "PX_LAST": 2.19,
                "_security_error": None,
            },
            {
                "date": date(2026, 3, 24),
                "security": "GJGB2 Index",
                "PX_LAST": 1.20,
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
            assert securities == ["GJGB10 Index", "GJGB2 Index"]
            assert fields == ["PX_LAST"]
            assert start_date == date(2026, 3, 1)
            assert end_date == date(2026, 3, 24)
            return historical_df

    monkeypatch.setattr(jgb_module, "BloombergSession", FakeSession)

    result = jgb_module.extract_jgb_historical(
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 24),
        tenors=["10Y", "2Y"],
    )

    assert list(result.columns) == [
        "date",
        "tenor",
        "yield",
        "currency",
        "instrument",
        "source",
        "ticker",
        "_security_error",
    ]
    assert list(result["tenor"]) == ["2Y", "10Y"]
    assert list(result["yield"]) == [1.20, 2.19]
