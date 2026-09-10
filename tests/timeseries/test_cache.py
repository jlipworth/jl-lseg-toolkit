from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
import pytest

from lseg_toolkit.exceptions import DataRetrievalError
from lseg_toolkit.timeseries.cache import (
    CacheConfig,
    DataCache,
    FetchResult,
    FetchStatus,
    InstrumentNotFoundError,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def cache(monkeypatch):
    @contextmanager
    def fake_connection(*args, **kwargs):
        yield object()

    import lseg_toolkit.timeseries.cache as cache_module

    monkeypatch.setattr(cache_module.storage, "get_connection", fake_connection)
    monkeypatch.setattr(cache_module, "get_client", lambda: object())
    monkeypatch.setattr(cache_module, "get_registry", lambda: object())
    coverage = []
    monkeypatch.setattr(
        cache_module, "load_fetch_coverage", lambda *args: list(coverage)
    )
    monkeypatch.setattr(
        cache_module,
        "save_fetch_coverage",
        lambda conn, inst, gran, start, end: coverage.append((start, end)),
    )

    return DataCache(
        CacheConfig(
            validate_instruments=False,
            auto_register_instruments=False,
            max_concurrent_fetches=2,
        )
    )


@pytest.mark.anyio
async def test_async_get_or_fetch_returns_dataframe(cache, monkeypatch):
    expected = pd.DataFrame(
        {"close": [1.0, 2.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"])
    )

    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        return FetchResult(
            ric=ric,
            status=FetchStatus.SUCCESS,
            data=expected,
            rows_fetched=len(expected),
        )

    monkeypatch.setattr(
        DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single
    )

    result = await cache.async_get_or_fetch("TYc1", "2026-01-01", "2026-01-02")

    pd.testing.assert_frame_equal(result, expected)


@pytest.mark.anyio
async def test_async_get_or_fetch_raises_not_found(cache, monkeypatch):
    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        return FetchResult(
            ric=ric,
            status=FetchStatus.NOT_FOUND,
            error=f"Unknown instrument: {ric}",
        )

    monkeypatch.setattr(
        DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single
    )

    with pytest.raises(InstrumentNotFoundError, match="Unknown instrument: BADRIC"):
        await cache.async_get_or_fetch("BADRIC", "2026-01-01", "2026-01-02")


@pytest.mark.anyio
async def test_async_get_or_fetch_raises_data_retrieval_error(cache, monkeypatch):
    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        return FetchResult(
            ric=ric,
            status=FetchStatus.FAILED,
            error="LSEG fetch failed",
        )

    monkeypatch.setattr(
        DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single
    )

    with pytest.raises(DataRetrievalError, match="LSEG fetch failed"):
        await cache.async_get_or_fetch("TYc1", "2026-01-01", "2026-01-02")


@pytest.mark.anyio
async def test_async_get_or_fetch_many_returns_results_and_progress(cache, monkeypatch):
    frames = {
        "TYc1": pd.DataFrame({"close": [111.0]}),
        "USc1": pd.DataFrame({"close": [112.0]}),
    }
    progress_calls: list[tuple[str, int, int]] = []

    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        if ric == "BADRIC":
            return FetchResult(
                ric=ric,
                status=FetchStatus.NOT_FOUND,
                error="Unknown instrument: BADRIC",
            )
        return FetchResult(
            ric=ric, status=FetchStatus.SUCCESS, data=frames[ric], rows_fetched=1
        )

    monkeypatch.setattr(
        DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single
    )

    result = await cache.async_get_or_fetch_many(
        ["TYc1", "BADRIC", "USc1"],
        "2026-01-01",
        "2026-01-02",
        progress_callback=lambda ric, completed, total: progress_calls.append(
            (ric, completed, total)
        ),
    )

    pd.testing.assert_frame_equal(result["TYc1"], frames["TYc1"])
    pd.testing.assert_frame_equal(result["USc1"], frames["USc1"])
    assert result["BADRIC"].empty
    assert len(progress_calls) == 3
    assert progress_calls[-1][1:] == (3, 3)
    assert {ric for ric, _, _ in progress_calls} == {"TYc1", "BADRIC", "USc1"}


@pytest.mark.anyio
async def test_async_iter_fetch_yields_results(cache, monkeypatch):
    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        return FetchResult(
            ric=ric,
            status=FetchStatus.SUCCESS,
            data=pd.DataFrame({"close": [1.0]}),
            rows_fetched=1,
        )

    monkeypatch.setattr(
        DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single
    )

    results = []
    async for result in cache.async_iter_fetch(
        ["TYc1", "USc1"],
        "2026-01-01",
        "2026-01-02",
    ):
        results.append(result)

    assert len(results) == 2
    assert {result.ric for result in results} == {"TYc1", "USc1"}
    assert all(result.success for result in results)


def test_daily_gaps_include_interior_session_but_not_holiday():
    from datetime import date

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    # CME is closed Christmas; Dec 29 is a genuine missing session.
    cached = pd.DataFrame(
        {"close": [1, 2, 3]},
        index=pd.to_datetime(["2025-12-24", "2025-12-26", "2025-12-30"]),
    )
    assert detect_gaps(
        object(),
        "TYc1",
        date(2025, 12, 24),
        date(2025, 12, 30),
        Granularity.DAILY,
        cached_data=cached,
    ) == [DateGap(date(2025, 12, 29), date(2025, 12, 29))]


def test_intraday_expected_bars_detect_missing_hour():
    from datetime import date

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    expected = pd.date_range("2026-01-05 10:00", periods=3, freq="h", tz="UTC")
    cached = pd.DataFrame({"close": [1, 3]}, index=expected[[0, 2]])
    assert detect_gaps(
        object(),
        "EUR=",
        date(2026, 1, 5),
        date(2026, 1, 5),
        Granularity.HOURLY,
        cached_data=cached,
        expected_timestamps=expected,
    ) == [DateGap(date(2026, 1, 5), date(2026, 1, 5))]


def test_unknown_calendar_does_not_claim_interior_coverage():
    from datetime import date

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    cached = pd.DataFrame(
        {"close": [1, 3]}, index=pd.to_datetime(["2026-01-05", "2026-01-07"])
    )
    assert detect_gaps(
        object(),
        "EUR=",
        date(2026, 1, 5),
        date(2026, 1, 7),
        Granularity.DAILY,
        cached_data=cached,
        covered_ranges=[],
    ) == [DateGap(date(2026, 1, 5), date(2026, 1, 7))]


def _mock_cache_storage(monkeypatch, cached):
    import lseg_toolkit.timeseries.cache as module

    monkeypatch.setattr(module, "get_instrument_id", lambda *args: 1)
    monkeypatch.setattr(module, "load_timeseries", lambda *args: cached)
    saved = []
    monkeypatch.setattr(
        module, "save_timeseries", lambda conn, inst, df, gran: saved.append(df.copy())
    )
    return saved


def test_failed_gap_fetch_preserves_error_even_with_cached_rows(cache, monkeypatch):
    from lseg_toolkit.timeseries.enums import Granularity

    cached = pd.DataFrame({"close": [1]}, index=pd.to_datetime(["2026-01-05"]))
    _mock_cache_storage(monkeypatch, cached)

    def fail(*args):
        raise DataRetrievalError("provider unavailable")

    monkeypatch.setattr(cache, "_fetch_from_lseg", fail)
    result = cache._get_or_fetch_single(
        "EUR=", "2026-01-05", "2026-01-07", Granularity.DAILY
    )
    assert not result.success
    assert not result.complete
    assert "provider unavailable" in result.error
    assert len(result.data) == 1
    with pytest.raises(DataRetrievalError, match="provider unavailable"):
        cache.get_or_fetch("EUR=", "2026-01-05", "2026-01-07")


def test_successful_empty_fetch_is_not_provider_failure(cache, monkeypatch):
    from lseg_toolkit.timeseries.enums import Granularity

    _mock_cache_storage(monkeypatch, pd.DataFrame())
    monkeypatch.setattr(cache, "_fetch_from_lseg", lambda *args: pd.DataFrame())
    result = cache._get_or_fetch_single(
        "EUR=", "2026-01-03", "2026-01-04", Granularity.DAILY
    )
    assert result.success
    assert not result.coverage_verified  # Unknown market calendar, not inferred.
    assert result.data.empty


def test_fetched_and_cached_rows_are_clamped_to_request(cache, monkeypatch):
    cached = pd.DataFrame(
        {"close": [1, 2, 3]},
        index=pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-20"]),
    )
    saved = _mock_cache_storage(monkeypatch, cached)
    fetched = pd.DataFrame(
        {"close": [4, 5, 6]},
        index=pd.to_datetime(["2026-01-02", "2026-01-06", "2026-01-21"]),
    )
    monkeypatch.setattr(cache, "_fetch_from_lseg", lambda *args: fetched)
    result = cache.get_or_fetch("EUR=", "2026-01-05", "2026-01-07")
    assert result.index.tolist() == list(pd.to_datetime(["2026-01-05", "2026-01-06"]))
    assert saved[0].index.tolist() == [pd.Timestamp("2026-01-06")]


def test_known_schedule_incomplete_provider_response_raises(cache, monkeypatch):
    _mock_cache_storage(monkeypatch, pd.DataFrame())
    monkeypatch.setattr(cache, "_fetch_from_lseg", lambda *args: pd.DataFrame())
    with pytest.raises(DataRetrievalError, match="coverage remains incomplete"):
        cache.get_or_fetch("TYc1", "2026-01-05", "2026-01-07")


def test_disjoint_persisted_coverage_leaves_interior_gap():
    from datetime import date

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    assert detect_gaps(
        object(),
        "EUR=",
        date(2026, 1, 1),
        date(2026, 1, 10),
        Granularity.DAILY,
        covered_ranges=[
            (date(2025, 12, 20), date(2026, 1, 3)),
            (date(2026, 1, 7), date(2026, 1, 20)),
        ],
    ) == [DateGap(date(2026, 1, 4), date(2026, 1, 6))]


def test_successful_empty_interval_is_cached(cache, monkeypatch):
    from unittest.mock import Mock

    _mock_cache_storage(monkeypatch, pd.DataFrame())
    fetch = Mock(return_value=pd.DataFrame())
    monkeypatch.setattr(cache, "_fetch_from_lseg", fetch)
    assert cache.get_or_fetch("EUR=", "2026-01-03", "2026-01-04").empty
    assert cache.get_or_fetch("EUR=", "2026-01-03", "2026-01-04").empty
    fetch.assert_called_once()


def test_failed_interval_is_not_cached(cache, monkeypatch):
    from unittest.mock import Mock

    _mock_cache_storage(monkeypatch, pd.DataFrame())
    fetch = Mock(side_effect=DataRetrievalError("provider unavailable"))
    monkeypatch.setattr(cache, "_fetch_from_lseg", fetch)
    for _ in range(2):
        with pytest.raises(DataRetrievalError):
            cache.get_or_fetch("EUR=", "2026-01-03", "2026-01-04")
    assert fetch.call_count == 2


def test_adjacent_overlapping_coverage_is_merged():
    from datetime import date

    from lseg_toolkit.timeseries.cache import detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    assert (
        detect_gaps(
            object(),
            "EUR=",
            date(2026, 1, 1),
            date(2026, 1, 10),
            Granularity.HOURLY,
            covered_ranges=[
                (date(2026, 1, 1), date(2026, 1, 5)),
                (date(2026, 1, 4), date(2026, 1, 7)),
                (date(2026, 1, 8), date(2026, 1, 10)),
            ],
        )
        == []
    )


def test_today_and_future_coverage_are_refetched():
    from datetime import UTC, datetime, timedelta

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    today = datetime.now(UTC).date()
    tomorrow = today + timedelta(days=1)
    assert detect_gaps(
        object(),
        "EUR=",
        today,
        tomorrow,
        Granularity.HOURLY,
        covered_ranges=[(today, tomorrow)],
    ) == [DateGap(today, tomorrow)]


def test_public_detect_gaps_loads_persisted_coverage(monkeypatch):
    from datetime import date

    import lseg_toolkit.timeseries.cache as module
    from lseg_toolkit.timeseries.enums import Granularity

    monkeypatch.setattr(module, "get_instrument_id", lambda *args: 7)
    monkeypatch.setattr(
        module,
        "load_fetch_coverage",
        lambda *args: [(date(2026, 1, 1), date(2026, 1, 10))],
    )
    assert (
        module.detect_gaps(
            object(), "EUR=", date(2026, 1, 3), date(2026, 1, 4), Granularity.HOURLY
        )
        == []
    )


def test_known_schedule_refreshes_today_without_requiring_future_bars():
    from datetime import UTC, datetime, timedelta

    from lseg_toolkit.timeseries.cache import DateGap, detect_gaps
    from lseg_toolkit.timeseries.enums import Granularity

    today = datetime.now(UTC).date()
    tomorrow = today + timedelta(days=1)
    expected = pd.date_range(today, tomorrow, tz="UTC")
    cached = pd.DataFrame({"close": [1]}, index=expected[:1])
    assert detect_gaps(
        object(),
        "TYc1",
        today,
        tomorrow,
        Granularity.DAILY,
        cached_data=cached,
        expected_timestamps=expected,
    ) == [DateGap(today, tomorrow)]
    assert (
        detect_gaps(
            object(),
            "TYc1",
            today,
            tomorrow,
            Granularity.DAILY,
            cached_data=cached,
            expected_timestamps=expected,
            refresh_mutable=False,
        )
        == []
    )
