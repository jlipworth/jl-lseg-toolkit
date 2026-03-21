"""Tests for Fed Funds extraction session-date and labeling behavior."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from lseg_toolkit.timeseries.calendars import get_lseg_cme_session_date
from lseg_toolkit.timeseries.enums import DataShape, Granularity
from lseg_toolkit.timeseries.fed_funds.extraction import (
    fetch_fed_funds_daily,
    fetch_fed_funds_hourly,
    fetch_fed_funds_strip,
    prepare_for_storage,
)
from lseg_toolkit.timeseries.fed_funds.roll_detection import (
    _get_expected_roll_date,
    get_expected_roll_dates,
)
from lseg_toolkit.timeseries.storage import writer
from lseg_toolkit.timeseries.storage.writer import save_timeseries


class TestFedFundsSessionDate:
    """Test observed CME/LSEG session-date boundaries."""

    def test_get_lseg_cme_session_date_boundary_cases(self):
        """Observed hard cuts should map to the next session date."""
        assert get_lseg_cme_session_date(pd.Timestamp("2025-09-30 21:00:00")) == date(
            2025, 9, 30
        )
        assert get_lseg_cme_session_date(pd.Timestamp("2025-09-30 23:00:00")) == date(
            2025, 10, 1
        )
        assert get_lseg_cme_session_date(pd.Timestamp("2025-11-02 22:00:00")) == date(
            2025, 11, 3
        )
        assert get_lseg_cme_session_date(pd.Timestamp("2026-01-01 22:00:00")) == date(
            2026, 1, 2
        )

    def test_roll_detection_uses_holiday_aware_roll_dates(self):
        """Roll detection should use CME holiday-aware session dates."""
        assert _get_expected_roll_date(date(2025, 9, 15)) == date(2025, 9, 1)
        assert _get_expected_roll_date(date(2026, 1, 15)) == date(2026, 1, 2)

        expected = get_expected_roll_dates(date(2025, 12, 1), date(2026, 1, 31))
        assert expected == [date(2025, 12, 1), date(2026, 1, 2)]


class TestFedFundsExtraction:
    """Test contract labeling and storage prep."""

    def test_fetch_fed_funds_daily_adds_session_date_and_contracts(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "SETTLE": [95.7750, 95.9225],
                "OPINT_1": [100, 110],
                "ACVOL_UNS": [10, 11],
            },
            index=pd.to_datetime(["2025-09-30", "2025-10-01"]),
        )

        df = fetch_fed_funds_daily(client, "2025-09-30", "2025-10-01")

        assert list(df["session_date"]) == [date(2025, 9, 30), date(2025, 10, 1)]
        assert list(df["source_contract"]) == ["FFU25", "FFV25"]
        assert list(df["close"]) == list(df["settle"])

    def test_fetch_fed_funds_hourly_labels_by_session_date_not_utc_date(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "BID": [95.7750, 95.9200],
                "ASK": [95.7775, 95.9225],
                "TRDPRC_1": [95.7750, 95.9225],
                "HIGH_1": [95.7800, 95.9300],
                "LOW_1": [95.7700, 95.9150],
            },
            index=pd.to_datetime(["2025-09-30 21:00:00", "2025-09-30 23:00:00"]),
        )

        df = fetch_fed_funds_hourly(client, "2025-09-30", "2025-10-01")

        assert list(df["session_date"]) == [date(2025, 9, 30), date(2025, 10, 1)]
        assert list(df["source_contract"]) == ["FFU25", "FFV25"]
        assert df.iloc[1]["source_contract"] != "FFU25"
        assert list(df["close"]) == list(df["mid"])

    def test_fetch_fed_funds_hourly_drops_rows_without_usable_close(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "BID": [pd.NA, 95.9200],
                "ASK": [pd.NA, 95.9225],
                "TRDPRC_1": [pd.NA, 95.9225],
                "HIGH_1": [pd.NA, 95.9300],
                "LOW_1": [pd.NA, 95.9150],
            },
            index=pd.to_datetime(["2025-09-30 21:00:00", "2025-09-30 23:00:00"]),
        )

        df = fetch_fed_funds_hourly(client, "2025-09-30", "2025-10-01")

        assert len(df) == 1
        assert list(df["source_contract"]) == ["FFV25"]
        assert list(df["close"]) == [95.92125]

    def test_fetch_fed_funds_daily_rank_two_labels_second_contract(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "SETTLE": [95.7750, 95.9225],
                "OPINT_1": [100, 110],
                "ACVOL_UNS": [10, 11],
            },
            index=pd.to_datetime(["2025-09-30", "2025-10-01"]),
        )

        df = fetch_fed_funds_daily(client, "2025-09-30", "2025-10-01", rank=2)

        client.get_history.assert_called_once()
        assert client.get_history.call_args.kwargs["rics"] == "FFc2"
        assert list(df["source_contract"]) == ["FFV25", "FFX25"]

    def test_fetch_fed_funds_strip_fetches_multiple_ranks(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "SETTLE": [95.7750],
                "OPINT_1": [100],
                "ACVOL_UNS": [10],
            },
            index=pd.to_datetime(["2025-09-30"]),
        )

        result = fetch_fed_funds_strip(
            client,
            "2025-09-30",
            "2025-09-30",
            ranks=[1, 2, 3],
        )

        assert list(result.keys()) == ["FFc1", "FFc2", "FFc3"]
        called_rics = [call.kwargs["rics"] for call in client.get_history.call_args_list]
        assert called_rics == ["FFc1", "FFc2", "FFc3"]
        assert result["FFc3"].iloc[0]["source_contract"] == "FFX25"

    def test_fetch_fed_funds_daily_preserves_december_contract_through_month_end(self):
        client = MagicMock()
        client.get_history.return_value = pd.DataFrame(
            {
                "SETTLE": [96.10, 96.12, 96.20],
                "OPINT_1": [100, 110, 120],
                "ACVOL_UNS": [10, 11, 12],
            },
            index=pd.to_datetime(["2025-12-01", "2025-12-31", "2026-01-02"]),
        )

        df = fetch_fed_funds_daily(client, "2025-12-01", "2026-01-02")

        assert list(df["source_contract"]) == ["FFZ25", "FFZ25", "FFF26"]

    def test_prepare_for_storage_keeps_session_date_and_localizes_ts(self):
        df = pd.DataFrame(
            {
                "mid": [95.92125],
                "close": [95.92125],
                "session_date": [date(2025, 10, 1)],
                "source_contract": ["FFX25"],
                "implied_rate": [4.07875],
            },
            index=pd.to_datetime(["2025-09-30 23:00:00"]),
        )

        result = prepare_for_storage(df, instrument_id=123, granularity="hourly")

        assert "session_date" in result.columns
        assert result.loc[0, "session_date"] == date(2025, 10, 1)
        assert result.loc[0, "ts"].tzinfo is not None
        assert result.loc[0, "close"] == result.loc[0, "mid"]


class TestFedFundsStorageWriter:
    """Test OHLCV writer support for session_date."""

    def test_save_timeseries_writes_session_date(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_copy_with_upsert(conn, table, columns, buffer, conflict_columns):
            captured["table"] = table
            captured["columns"] = columns
            captured["payload"] = buffer.getvalue()
            captured["conflict_columns"] = conflict_columns
            return buffer.getvalue().count("\n")

        monkeypatch.setattr(writer, "_copy_with_upsert", fake_copy_with_upsert)

        mock_conn = MagicMock()
        df = pd.DataFrame(
            {
                "close": [95.92125],
                "mid": [95.92125],
                "session_date": [date(2025, 10, 1)],
                "source_contract": ["FFX25"],
            },
            index=pd.to_datetime(["2025-09-30 23:00:00"]),
        )

        rows = save_timeseries(
            mock_conn,
            1,
            df,
            Granularity.HOURLY,
            data_shape=DataShape.OHLCV,
        )

        assert rows == 1
        assert captured["table"] == "timeseries_ohlcv"
        assert "session_date" in captured["columns"]
        assert "2025-10-01" in captured["payload"]
        assert "FFX25" in captured["payload"]
