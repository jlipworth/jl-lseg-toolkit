"""Offline regression tests for extraction correctness; no service calls."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.exceptions import DataRetrievalError
from lseg_toolkit.timeseries.config import TimeSeriesConfig
from lseg_toolkit.timeseries.enums import RollMethod
from lseg_toolkit.timeseries.fetch import (
    _split_multi_ric_response,
    get_bond_contract_chain,
)
from lseg_toolkit.timeseries.pipeline import (
    ExtractionResult,
    TimeSeriesExtractionPipeline,
)
from lseg_toolkit.timeseries.rolling import (
    _detect_roll_dates_expiry,
    _ordered_contracts,
)


def pipeline(**kwargs):
    return TimeSeriesExtractionPipeline(
        TimeSeriesConfig(
            symbols=kwargs.pop("symbols", ["ZN"]),
            start_date=date(2025, 12, 1),
            end_date=date(2026, 1, 31),
            export_parquet=False,
            **kwargs,
        ),
        verbose=False,
    )


def frame(price=100):
    return pd.DataFrame(
        {"close": [price], "volume": [10]}, index=pd.to_datetime(["2026-01-02"])
    )


def success(symbol="ZN"):
    return ExtractionResult(symbol, 1, date(2026, 1, 2), date(2026, 1, 2), True)


def test_chain_crosses_year_and_includes_following_quarter():
    assert get_bond_contract_chain(
        "ZN", date(2025, 12, 1), date(2026, 1, 31), as_of=date(2026, 9, 10)
    ) == [
        "TYZ25^2",
        "TYH26^2",
        "TYM26^2",
    ]
    assert get_bond_contract_chain(
        "TYc1", date(2026, 1, 1), date(2026, 2, 1), as_of=date(2026, 9, 10)
    ) == [
        "TYH26^2",
        "TYM26^2",
    ]


def test_continuous_roots_fetched_and_built_separately():
    p = pipeline(symbols=["ZN", "ZB"], continuous=True)

    def fetch(contracts, *args, **kwargs):
        assert kwargs["continuous"] is False
        return {ric: frame() for ric in contracts}

    with (
        patch(
            "lseg_toolkit.timeseries.pipeline.fetch_futures", side_effect=fetch
        ) as fetch_mock,
        patch.object(
            p,
            "_build_and_store_continuous",
            side_effect=lambda symbol, data: success(symbol),
        ) as build,
    ):
        assert len(p._extract_futures()) == 2
    assert fetch_mock.call_args_list[0].args[0] == ["TYZ25^2", "TYH26^2", "TYM26^2"]
    assert fetch_mock.call_args_list[1].args[0] == ["USZ25^2", "USH26^2", "USM26^2"]
    for call in build.call_args_list:
        prefix = "TY" if call.args[0] == "ZN" else "US"
        assert all(ric.startswith(prefix) for ric in call.args[1])


@pytest.mark.parametrize(
    "method,fetch_name,symbols,data",
    [
        ("_extract_futures", "fetch_futures", ["ZN", "ZB"], {}),
        ("_extract_fx", "fetch_fx", ["EURUSD"], {}),
        ("_extract_ois", "fetch_ois", ["1M"], {}),
        ("_extract_fras", "fetch_fras", ["1X4"], {}),
        ("_extract_treasury_yields", "fetch_govt_yields", ["10Y"], {}),
    ],
)
def test_missing_responses_are_failures(method, fetch_name, symbols, data):
    p = pipeline(symbols=symbols)
    with patch(f"lseg_toolkit.timeseries.pipeline.{fetch_name}", return_value=data):
        results = getattr(p, method)()
    assert len(results) == len(symbols)
    assert all(not result.success for result in results)


def test_failure_does_not_silently_drop_partial_batch():
    p = pipeline(symbols=["ZN", "ZB"])
    with (
        patch(
            "lseg_toolkit.timeseries.pipeline.fetch_futures",
            return_value={"ZN": frame()},
        ),
        patch.object(
            p,
            "_store_timeseries",
            side_effect=lambda **kw: (
                success(kw["symbol"])
                if not kw["df"].empty
                else ExtractionResult(kw["symbol"], 0, None, None, False)
            ),
        ),
    ):
        results = p._extract_futures()
    assert [r.success for r in results] == [True, False]


def test_roll_order_is_chronological_not_month_code_order():
    data = {
        ric: pd.DataFrame({"close": [100]}, index=pd.to_datetime([end]))
        for ric, end in [
            ("TYZ25", "2025-12-19"),
            ("TYH26", "2026-03-20"),
            ("TYM26", "2026-06-19"),
        ]
    }
    events = _detect_roll_dates_expiry(data)
    assert [(e[1], e[2]) for e in events] == [("TYZ25", "TYH26"), ("TYH26", "TYM26")]
    assert _ordered_contracts({"TYH6": frame(), "TYZ5^2": frame()}) == [
        "TYZ5^2",
        "TYH6",
    ]


def test_roll_days_forwarded_and_failed_save_does_not_write_events():
    p = pipeline(
        continuous=True, roll_method=RollMethod.FIXED_DAYS, roll_days_before=12
    )
    with (
        patch(
            "lseg_toolkit.timeseries.pipeline.build_continuous",
            return_value=(frame(), []),
        ) as build,
        patch.object(
            p,
            "_store_timeseries",
            return_value=ExtractionResult("ZN", 0, None, None, False),
        ),
        patch("lseg_toolkit.timeseries.pipeline.get_connection") as conn,
    ):
        result = p._build_and_store_continuous("ZN", {"TYH26": frame()})
    assert build.call_args.kwargs["roll_days_before"] == 12
    assert not result.success
    conn.assert_not_called()


def test_run_exports_successful_symbols_and_closes_client():
    p = pipeline()
    p.config.export_parquet = True
    client = MagicMock()
    path = Path("/tmp/not-written.parquet")
    with (
        patch.object(p, "_extract_futures", return_value=[success()]),
        patch(
            "lseg_toolkit.timeseries.pipeline.export_to_parquet", return_value=[path]
        ) as export,
        patch("lseg_toolkit.timeseries.pipeline.get_client", return_value=client),
    ):
        result = p.run()
    assert result.parquet_files == [path]
    assert result.results[0].parquet_path == path
    assert export.call_args.kwargs["symbol"] == "ZN"
    client.close.assert_called_once()


def test_export_failure_is_reported():
    p = pipeline()
    p.config.export_parquet = True
    with (
        patch.object(p, "_extract_futures", return_value=[success()]),
        patch(
            "lseg_toolkit.timeseries.pipeline.export_to_parquet",
            side_effect=OSError("disk full"),
        ),
        patch("lseg_toolkit.timeseries.pipeline.get_client"),
    ):
        result = p.run()
    assert result.failure_count == 1
    assert "Data stored, but Parquet export failed" in result.results[0].error


def test_unidentified_multi_response_not_assigned_to_wrong_symbol():
    with pytest.raises(DataRetrievalError):
        _split_multi_ric_response(frame(), {"ZN": "TYc1", "ZB": "USc1"})


def test_aliases_and_single_instrument_column_are_split():
    data = frame().assign(Instrument="TYc1")
    result = _split_multi_ric_response(data, {"ZN": "TYc1", "TYc1": "TYc1"})
    assert set(result) == {"ZN", "TYc1"}
    assert "Instrument" not in result["ZN"]
    assert "Instrument" not in _split_multi_ric_response(data, {"ZN": "TYc1"})["ZN"]


def test_pipeline_rejects_unverified_expiry_rolls_before_fetching():
    p = pipeline(continuous=True, roll_method=RollMethod.EXPIRY)
    with patch("lseg_toolkit.timeseries.pipeline.fetch_futures") as fetch:
        results = p._extract_futures()
    assert not results[0].success
    assert "verified exchange expiry metadata" in results[0].error
    fetch.assert_not_called()


def test_missing_required_chain_member_fails_before_storage():
    p = pipeline(continuous=True)
    with (
        patch(
            "lseg_toolkit.timeseries.pipeline.get_bond_contract_chain",
            return_value=["TYZ25^2", "TYH26^2", "TYM26^2"],
        ),
        patch(
            "lseg_toolkit.timeseries.pipeline.fetch_futures",
            return_value={"TYZ25^2": frame(), "TYM26^2": frame()},
        ),
        patch.object(p, "_build_and_store_continuous") as build,
    ):
        results = p._extract_futures()
    assert not results[0].success
    assert "TYH26^2" in results[0].error
    build.assert_not_called()


def test_missing_optional_next_quarter_does_not_fail():
    p = pipeline(continuous=True)
    with (
        patch(
            "lseg_toolkit.timeseries.pipeline.get_bond_contract_chain",
            return_value=["TYZ25^2", "TYH26^2", "TYM26^2"],
        ),
        patch(
            "lseg_toolkit.timeseries.pipeline.fetch_futures",
            return_value={"TYZ25^2": frame(), "TYH26^2": frame()},
        ),
        patch.object(p, "_build_and_store_continuous", return_value=success()),
    ):
        results = p._extract_futures()
    assert results[0].success


def test_live_and_future_contracts_do_not_have_expired_suffix():
    assert get_bond_contract_chain(
        "ZN", date(2026, 9, 1), date(2026, 9, 9), as_of=date(2026, 9, 10)
    ) == ["TYU26", "TYZ26"]
