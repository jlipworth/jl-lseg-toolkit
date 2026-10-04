"""
Unit tests for the LSEGDataClient.

Tests batching, retry logic, validation, and error handling.
These tests use mocks and don't require LSEG Workspace.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.exceptions import DataRetrievalError, DataValidationError
from lseg_toolkit.timeseries.client import (
    ClientConfig,
    LSEGDataClient,
    get_client,
    reset_client,
)


@pytest.fixture(autouse=True)
def mock_session_lifecycle():
    # Mock the actual session boundary as well as the data methods. Patching
    # client.rd alone does not patch client.session.rd and could contact Workspace.
    with patch("lseg_toolkit.timeseries.client.SessionManager"):
        reset_client()
        yield
        reset_client()


class TestClientConfig:
    """Test ClientConfig defaults and customization."""

    def test_default_values(self):
        """Default config should have sensible values."""
        config = ClientConfig()

        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.rate_limit_delay == 0.05  # Reduced for faster batching
        assert config.max_rics_per_request == 100
        assert config.validate_inputs is True

    def test_custom_values(self):
        """Config should accept custom values."""
        config = ClientConfig(
            max_retries=5,
            retry_delay=2.0,
            max_rics_per_request=100,
        )

        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.max_rics_per_request == 100


class TestLSEGDataClientValidation:
    """Test input validation."""

    def test_validate_date_range_valid(self):
        """Valid date range should pass."""
        client = LSEGDataClient()
        # Should not raise
        client._validate_date_range("2024-01-01", "2024-12-31")

    def test_validate_date_range_invalid_format(self):
        """Invalid date format should raise DataValidationError."""
        client = LSEGDataClient()

        with pytest.raises(DataValidationError) as exc_info:
            client._validate_date_range("01-01-2024", "2024-12-31")

        assert "Invalid date format" in str(exc_info.value)

    def test_validate_date_range_start_after_end(self):
        """Start date after end date should raise DataValidationError."""
        client = LSEGDataClient()

        with pytest.raises(DataValidationError) as exc_info:
            client._validate_date_range("2024-12-31", "2024-01-01")

        assert "cannot be after" in str(exc_info.value)

    def test_validate_interval_valid(self):
        """Valid intervals should pass."""
        client = LSEGDataClient()
        # Should not raise
        client._validate_interval("daily")
        client._validate_interval("hourly")
        client._validate_interval("5min")

    def test_validate_interval_invalid(self):
        """Invalid interval should raise DataValidationError."""
        client = LSEGDataClient()

        with pytest.raises(DataValidationError) as exc_info:
            client._validate_interval("invalid_interval")

        assert "Invalid interval" in str(exc_info.value)


class TestRetryLogic:
    """Test retry with exponential backoff."""

    def test_retry_succeeds_on_first_try(self):
        """Successful call should return immediately."""
        client = LSEGDataClient()

        mock_func = MagicMock(return_value="success")
        result = client._retry_with_backoff(mock_func, "test operation")

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_succeeds_after_transient_failure(self):
        """Should retry on transient errors."""
        config = ClientConfig(max_retries=3, retry_delay=0.01)
        client = LSEGDataClient(config)

        # Fail twice, then succeed
        mock_func = MagicMock(
            side_effect=[Exception("timeout"), Exception("timeout"), "success"]
        )
        result = client._retry_with_backoff(mock_func, "test operation")

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_fails_after_max_attempts(self):
        """Should raise after max retries exhausted."""
        config = ClientConfig(max_retries=3, retry_delay=0.01)
        client = LSEGDataClient(config)

        mock_func = MagicMock(side_effect=Exception("persistent error"))

        with pytest.raises(DataRetrievalError) as exc_info:
            client._retry_with_backoff(mock_func, "test operation")

        assert "after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3

    def test_permanent_failure_no_retry(self):
        """Permanent errors should not retry."""
        config = ClientConfig(max_retries=3, retry_delay=0.01)
        client = LSEGDataClient(config)

        # Access denied is a permanent error
        mock_func = MagicMock(side_effect=Exception("Access denied"))

        with pytest.raises(DataRetrievalError) as exc_info:
            client._retry_with_backoff(mock_func, "test operation")

        assert "Permanent failure" in str(exc_info.value)
        assert mock_func.call_count == 1  # No retry


class TestBatching:
    """Test RIC batching for large requests."""

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_single_batch_no_splitting(self, mock_rd):
        """Small RIC list should use single request."""
        mock_rd.get_history.return_value = pd.DataFrame({"close": [100.0]})

        config = ClientConfig(max_rics_per_request=50, validate_inputs=False)
        client = LSEGDataClient(config)

        rics = [f"RIC{i}" for i in range(10)]  # 10 RICs, below threshold
        client.get_history(rics, "2024-01-01", "2024-01-31")

        assert mock_rd.get_history.call_count == 1

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_large_list_splits_into_batches(self, mock_rd):
        """Large RIC list should be split into multiple batches."""
        mock_rd.get_history.return_value = pd.DataFrame({"close": [100.0]})

        config = ClientConfig(max_rics_per_request=10, validate_inputs=False)
        client = LSEGDataClient(config)

        rics = [f"RIC{i}" for i in range(25)]  # 25 RICs, 3 batches of 10, 10, 5
        client.get_history(rics, "2024-01-01", "2024-01-31")

        assert mock_rd.get_history.call_count == 3

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_empty_rics_returns_empty(self, mock_rd):
        """Empty RIC list should return empty DataFrame."""
        config = ClientConfig(validate_inputs=False)
        client = LSEGDataClient(config)

        result = client.get_history([], "2024-01-01", "2024-01-31")

        assert result.empty
        assert mock_rd.get_history.call_count == 0


class TestGetHistory:
    """Test get_history method."""

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_get_history_with_date_objects(self, mock_rd):
        """Should accept date objects as well as strings."""
        mock_rd.get_history.return_value = pd.DataFrame({"close": [100.0]})

        config = ClientConfig(validate_inputs=False)
        client = LSEGDataClient(config)

        # Pass date objects
        client.get_history(
            "TYc1",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )

        # Verify dates were converted to strings
        call_args = mock_rd.get_history.call_args
        assert call_args.kwargs["start"] == "2024-01-01"
        assert call_args.kwargs["end"] == "2024-12-31"

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_get_history_single_ric_string(self, mock_rd):
        """Single RIC string should be converted to list."""
        mock_rd.get_history.return_value = pd.DataFrame({"close": [100.0]})

        config = ClientConfig(validate_inputs=False)
        client = LSEGDataClient(config)

        client.get_history("TYc1", "2024-01-01", "2024-12-31")

        call_args = mock_rd.get_history.call_args
        assert call_args.kwargs["universe"] == ["TYc1"]

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_get_history_none_returns_empty(self, mock_rd):
        """None response should return empty DataFrame."""
        mock_rd.get_history.return_value = None

        config = ClientConfig(validate_inputs=False)
        client = LSEGDataClient(config)

        result = client.get_history("TYc1", "2024-01-01", "2024-12-31")

        assert result.empty


class TestGetData:
    """Test get_data method (snapshot data)."""

    @patch("lseg_toolkit.timeseries.client.rd")
    def test_get_data_basic(self, mock_rd):
        """Should fetch snapshot data."""
        mock_rd.get_data.return_value = pd.DataFrame(
            {
                "Instrument": ["TYc1"],
                "DSPLY_NAME": ["10Y T-Note"],
            }
        )

        config = ClientConfig(validate_inputs=False)
        client = LSEGDataClient(config)

        result = client.get_data("TYc1", ["DSPLY_NAME"])

        assert not result.empty
        mock_rd.get_data.assert_called_once()

    def test_get_data_empty_rics_raises(self):
        """Empty RICs should raise validation error."""
        client = LSEGDataClient()

        with pytest.raises(DataValidationError) as exc_info:
            client.get_data([], ["DSPLY_NAME"])

        assert "cannot be empty" in str(exc_info.value)

    def test_get_data_empty_fields_raises(self):
        """Empty fields should raise validation error."""
        client = LSEGDataClient()

        with pytest.raises(DataValidationError) as exc_info:
            client.get_data("TYc1", [])

        assert "cannot be empty" in str(exc_info.value)


class TestSingleton:
    """Test get_client singleton pattern."""

    def test_get_client_returns_same_instance(self):
        """get_client should return same instance."""
        reset_client()  # Start fresh

        client1 = get_client()
        client2 = get_client()

        assert client1 is client2

    def test_reset_client_clears_singleton(self):
        """reset_client should clear the singleton."""
        reset_client()

        client1 = get_client()
        reset_client()
        client2 = get_client()

        assert client1 is not client2

    def test_get_client_with_custom_config(self):
        """First call with config should use that config."""
        reset_client()

        config = ClientConfig(max_retries=10)
        client = get_client(config)

        assert client.config.max_retries == 10

        reset_client()  # Cleanup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_concurrent_requests_initialize_session_once():
    from concurrent.futures import ThreadPoolExecutor

    with (
        patch("lseg_toolkit.timeseries.client.SessionManager") as sessions,
        patch(
            "lseg_toolkit.timeseries.client.rd.get_history",
            return_value=pd.DataFrame({"close": [1]}),
        ),
    ):
        client = LSEGDataClient(ClientConfig(rate_limit_delay=0))
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(
                pool.map(
                    lambda _: client.get_history("TYc1", "2026-01-05", "2026-01-06"),
                    range(20),
                )
            )
        assert sessions.call_count == 1
        client.close()
        client.get_history("TYc1", "2026-01-05", "2026-01-06")
        assert sessions.call_count == 2
        client.close()


def test_concurrent_singleton_access():
    from concurrent.futures import ThreadPoolExecutor

    reset_client()
    with ThreadPoolExecutor(max_workers=8) as pool:
        clients = list(pool.map(lambda _: get_client(), range(32)))
    assert all(client is clients[0] for client in clients)


def test_rate_limit_shared_across_clients(monkeypatch):
    import lseg_toolkit.timeseries.client as module

    clock = [100.0]
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        clock[0] += delay

    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.time, "sleep", sleep)
    monkeypatch.setattr(module, "_last_request_time", 0.0)
    LSEGDataClient(ClientConfig(rate_limit_delay=1))._rate_limit()
    LSEGDataClient(ClientConfig(rate_limit_delay=1))._rate_limit()
    assert sleeps == [1.0]


def test_session_owners_do_not_close_each_others_default_session():
    import lseg_toolkit.client.session as module

    with (
        patch.object(module, "rd") as sdk,
        patch.object(module, "load_app_key", return_value=None),
    ):
        first = module.SessionManager()
        second = module.SessionManager()
        try:
            assert sdk.open_session.call_count == 1
            first.close_session()
            sdk.close_session.assert_not_called()
            assert second.is_open
            second.close_session()
            sdk.close_session.assert_called_once()
        finally:
            first.close_session()
            second.close_session()


def test_direct_client_reopens_after_pipeline_cleanup():
    from lseg_toolkit.timeseries.config import TimeSeriesConfig
    from lseg_toolkit.timeseries.enums import AssetClass
    from lseg_toolkit.timeseries.pipeline import TimeSeriesExtractionPipeline

    with (
        patch("lseg_toolkit.timeseries.client.SessionManager") as sessions,
        patch(
            "lseg_toolkit.timeseries.client.rd.get_history",
            return_value=pd.DataFrame({"close": [1]}),
        ),
        patch.object(TimeSeriesExtractionPipeline, "_extract_fx", return_value=[]),
    ):
        client = get_client()
        client.get_history("EUR=", "2026-01-05", "2026-01-06")
        config = TimeSeriesConfig(
            symbols=["EURUSD"], asset_class=AssetClass.FX_SPOT, export_parquet=False
        )
        TimeSeriesExtractionPipeline(config, verbose=False).run()
        client.get_history("EUR=", "2026-01-05", "2026-01-06")
        assert sessions.call_count == 2
