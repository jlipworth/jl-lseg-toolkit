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

    return DataCache(
        CacheConfig(
            validate_instruments=False,
            auto_register_instruments=False,
            max_concurrent_fetches=2,
        )
    )


@pytest.mark.anyio
async def test_async_get_or_fetch_returns_dataframe(cache, monkeypatch):
    expected = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))

    async def fake_async_get_or_fetch_single(self, ric, start, end, granularity):
        return FetchResult(
            ric=ric,
            status=FetchStatus.SUCCESS,
            data=expected,
            rows_fetched=len(expected),
        )

    monkeypatch.setattr(DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single)

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

    monkeypatch.setattr(DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single)

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

    monkeypatch.setattr(DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single)

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
        return FetchResult(ric=ric, status=FetchStatus.SUCCESS, data=frames[ric], rows_fetched=1)

    monkeypatch.setattr(DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single)

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

    monkeypatch.setattr(DataCache, "_async_get_or_fetch_single", fake_async_get_or_fetch_single)

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
