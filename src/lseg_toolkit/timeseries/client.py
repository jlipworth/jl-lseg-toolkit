"""
LSEG Data Client with batching, retry logic, and input validation.

Provides a guarded wrapper for LSEG Data Library API calls with:
- Batch requests (multiple RICs in single API call)
- Retry logic with exponential backoff
- Rate limiting between requests
- Input validation
- Consistent error handling
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TypeVar

import lseg.data as rd
import pandas as pd

from lseg_toolkit.exceptions import (
    DataRetrievalError,
    DataValidationError,
    SessionError,
)
from lseg_toolkit.timeseries.constants import VALID_INTERVALS

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ClientConfig:
    """Configuration for LSEGDataClient."""

    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 0.1
    max_rics_per_request: int = 50  # LSEG typically handles 50-100 RICs per call
    validate_inputs: bool = True


@dataclass
class LSEGDataClient:
    """
    Guarded wrapper for LSEG Data Library API calls.

    Provides:
    - Batch requests for multiple RICs (reduces API calls)
    - Retry logic with exponential backoff
    - Rate limiting between requests
    - Input validation
    - Consistent error handling

    Example:
        >>> client = LSEGDataClient()
        >>> df = client.get_history(
        ...     rics=["TYc1", "USc1", "TUc1"],
        ...     start="2024-01-01",
        ...     end="2024-12-31",
        ...     fields=["OPEN_PRC", "HIGH_1", "LOW_1", "TRDPRC_1", "SETTLE"],
        ... )
    """

    config: ClientConfig = field(default_factory=ClientConfig)
    _last_request_time: float = field(default=0.0, init=False, repr=False)

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _retry_with_backoff(
        self,
        func: Callable[[], T],
        operation: str,
    ) -> T:
        """
        Execute function with retry logic and exponential backoff.

        Args:
            func: Function to execute.
            operation: Description for error messages.

        Returns:
            Result from function.

        Raises:
            DataRetrievalError: If all retries fail.
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()

                # Don't retry on permanent failures
                permanent_errors = ["invalid", "not found", "unknown", "access denied"]
                if any(x in error_str for x in permanent_errors):
                    raise DataRetrievalError(
                        f"Permanent failure in {operation}: {e}"
                    ) from e

                # Retry on transient failures
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries} failed "
                        f"for {operation}: {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for {operation}")

        raise DataRetrievalError(
            f"Failed to {operation} after {self.config.max_retries} attempts: "
            f"{last_exception}"
        ) from last_exception

    def _validate_date_range(self, start: str, end: str) -> None:
        """
        Validate date range inputs.

        Raises:
            DataValidationError: If dates are invalid.
        """
        try:
            start_date = datetime.fromisoformat(start)
            end_date = datetime.fromisoformat(end)
        except ValueError as e:
            raise DataValidationError(
                f"Invalid date format. Use ISO format (YYYY-MM-DD): {e}"
            ) from e

        if start_date > end_date:
            raise DataValidationError(
                f"Start date ({start}) cannot be after end date ({end})"
            )

        # Warn about future dates
        now = datetime.now()
        if start_date > now:
            logger.warning(
                f"Start date {start} is in the future. "
                f"LSEG may not return data for future dates."
            )

    def _validate_interval(self, interval: str) -> None:
        """
        Validate interval string.

        Raises:
            DataValidationError: If interval is invalid.
        """
        if interval not in VALID_INTERVALS:
            raise DataValidationError(
                f"Invalid interval '{interval}'. Valid options: {VALID_INTERVALS}"
            )

    def _check_session(self) -> None:
        """
        Check if LSEG session is available.

        Note: LSEG library doesn't expose session state directly,
        so we attempt a lightweight call to verify connectivity.

        Raises:
            SessionError: If session is not open.
        """
        try:
            # Attempt to fetch metadata for a known test RIC
            # This will fail fast if session isn't open
            rd.get_data("EUR=", fields=["DSPLY_NAME"])
        except Exception as e:
            error_str = str(e).lower()
            if "session" in error_str or "not opened" in error_str:
                raise SessionError(
                    "LSEG session is not open. Ensure LSEG Workspace Desktop "
                    "is running and call rd.open_session() first."
                ) from e
            # If it's another error (like network), the RIC exists but failed
            # That's OK - we just wanted to check session connectivity

    def get_history(
        self,
        rics: str | list[str],
        start: str | date,
        end: str | date,
        fields: list[str] | None = None,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        Fetch historical time series data with batching.

        This is the primary method for fetching time series data.
        Automatically batches large RIC lists into multiple requests.

        Args:
            rics: Single RIC or list of RICs.
            start: Start date (ISO format or date object).
            end: End date (ISO format or date object).
            fields: List of fields to retrieve.
            interval: Data interval (daily, hourly, etc).

        Returns:
            DataFrame with time series data. For multiple RICs, returns
            a MultiIndex DataFrame with (date, ric) or stacked format
            depending on LSEG response.

        Raises:
            DataRetrievalError: If fetch fails after retries.
            DataValidationError: If inputs are invalid.
            SessionError: If LSEG session is not open.
        """
        # Normalize inputs
        if isinstance(rics, str):
            rics = [rics]
        if isinstance(start, date):
            start = start.isoformat()
        if isinstance(end, date):
            end = end.isoformat()

        if not rics:
            return pd.DataFrame()

        # Validate inputs
        if self.config.validate_inputs:
            self._validate_date_range(start, end)
            self._validate_interval(interval)

        # Batch large RIC lists
        if len(rics) > self.config.max_rics_per_request:
            return self._batch_get_history(rics, start, end, fields, interval)

        # Rate limit
        self._rate_limit()

        # Execute with retry
        def _fetch() -> pd.DataFrame:
            df = rd.get_history(
                universe=rics,
                fields=fields,
                start=start,
                end=end,
                interval=interval,
            )

            if df is None:
                logger.warning(
                    f"rd.get_history returned None for {len(rics)} RICs. "
                    f"This may indicate invalid RICs or no data available."
                )
                return pd.DataFrame()

            if df.empty:
                logger.info(
                    f"No data returned for {len(rics)} RICs from {start} to {end}. "
                    f"RICs may be valid but no data exists for this period."
                )

            return df

        ric_summary = rics[:3] if len(rics) > 3 else rics
        return self._retry_with_backoff(
            _fetch,
            f"get_history({ric_summary}..., {start} to {end}, {interval})",
        )

    def _batch_get_history(
        self,
        rics: list[str],
        start: str,
        end: str,
        fields: list[str] | None,
        interval: str,
    ) -> pd.DataFrame:
        """
        Fetch history in batches for large RIC lists.

        Args:
            rics: List of RICs (can be large).
            start: Start date string.
            end: End date string.
            fields: Fields to retrieve.
            interval: Data interval.

        Returns:
            Combined DataFrame from all batches.
        """
        batch_size = self.config.max_rics_per_request
        all_results: list[pd.DataFrame] = []

        for i in range(0, len(rics), batch_size):
            batch = rics[i : i + batch_size]
            logger.info(
                f"Fetching batch {i // batch_size + 1}/{(len(rics) + batch_size - 1) // batch_size}: "
                f"{len(batch)} RICs"
            )

            df = self.get_history(
                rics=batch,
                start=start,
                end=end,
                fields=fields,
                interval=interval,
            )

            if not df.empty:
                all_results.append(df)

        if not all_results:
            return pd.DataFrame()

        # Combine results
        return pd.concat(all_results)

    def get_data(
        self,
        rics: str | list[str],
        fields: list[str],
    ) -> pd.DataFrame:
        """
        Fetch current snapshot data with batching.

        Args:
            rics: Single RIC or list of RICs.
            fields: List of fields to retrieve.

        Returns:
            DataFrame with snapshot data, one row per RIC.

        Raises:
            DataRetrievalError: If fetch fails after retries.
            DataValidationError: If inputs are invalid.
            SessionError: If LSEG session is not open.
        """
        # Normalize
        if isinstance(rics, str):
            rics = [rics]

        if not rics:
            raise DataValidationError("RICs list cannot be empty")
        if not fields:
            raise DataValidationError("Fields list cannot be empty")

        # Batch large RIC lists
        if len(rics) > self.config.max_rics_per_request:
            return self._batch_get_data(rics, fields)

        # Rate limit
        self._rate_limit()

        # Execute with retry
        def _fetch() -> pd.DataFrame:
            df = rd.get_data(universe=rics, fields=fields)

            if df is None:
                logger.warning(
                    f"rd.get_data returned None for {len(rics)} RICs. "
                    f"This may indicate invalid RICs."
                )
                return pd.DataFrame()

            return df

        ric_summary = rics[:3] if len(rics) > 3 else rics
        return self._retry_with_backoff(
            _fetch,
            f"get_data({ric_summary}..., {fields[:3]}...)",
        )

    def _batch_get_data(
        self,
        rics: list[str],
        fields: list[str],
    ) -> pd.DataFrame:
        """
        Fetch snapshot data in batches for large RIC lists.

        Args:
            rics: List of RICs.
            fields: Fields to retrieve.

        Returns:
            Combined DataFrame from all batches.
        """
        batch_size = self.config.max_rics_per_request
        all_results: list[pd.DataFrame] = []

        for i in range(0, len(rics), batch_size):
            batch = rics[i : i + batch_size]
            logger.info(
                f"Fetching snapshot batch {i // batch_size + 1}/{(len(rics) + batch_size - 1) // batch_size}"
            )

            df = self.get_data(rics=batch, fields=fields)
            if not df.empty:
                all_results.append(df)

        if not all_results:
            return pd.DataFrame()

        return pd.concat(all_results, ignore_index=True)


# Module-level singleton
_default_client: LSEGDataClient | None = None


def get_client(config: ClientConfig | None = None) -> LSEGDataClient:
    """
    Get the default LSEG data client (singleton).

    Args:
        config: Optional custom configuration. If provided on first call,
                this configuration is used for the singleton.

    Returns:
        The default LSEGDataClient instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = LSEGDataClient(config or ClientConfig())
    return _default_client


def reset_client() -> None:
    """Reset the singleton client (useful for testing)."""
    global _default_client
    _default_client = None
