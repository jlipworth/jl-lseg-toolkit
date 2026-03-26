"""Legacy / research Bloomberg session manager.

This connection layer is retained for exploratory scripts and older modular extractors.
The supported Bloomberg connection layer lives in `src/lseg_toolkit/bloomberg/connection.py`.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import date
from typing import TYPE_CHECKING

import blpapi
import pandas as pd

from .._legacy import warn_legacy_surface

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

logger = logging.getLogger(__name__)

# Bloomberg service names
REF_DATA_SERVICE = "//blp/refdata"


class BloombergError(Exception):
    """Bloomberg API error."""


class BloombergSession:
    """Bloomberg session manager with reference and historical data retrieval.

    Usage:
        with BloombergSession() as session:
            df = session.get_reference_data(["USSV1Y10Y BGN Curncy"], ["PX_LAST"])
    """

    def __init__(self, host: str = "localhost", port: int = 8194) -> None:
        """Initialize Bloomberg session.

        Args:
            host: Bloomberg Terminal host (default: localhost)
            port: Bloomberg Terminal port (default: 8194)
        """
        warn_legacy_surface(
            "bloomberg_scripts.common.BloombergSession",
            replacement="bbg-extract",
            note=(
                "This older connection wrapper backs quarantined legacy extractors and "
                "does not match the supported Bloomberg normalization layer."
            ),
            stacklevel=3,
        )
        self.host = host
        self.port = port
        self._session: blpapi.Session | None = None
        self._ref_data_service: blpapi.Service | None = None

    def connect(self) -> None:
        """Connect to Bloomberg Terminal."""
        session_options = blpapi.SessionOptions()
        session_options.setServerHost(self.host)
        session_options.setServerPort(self.port)

        self._session = blpapi.Session(session_options)

        if not self._session.start():
            raise BloombergError(
                f"Failed to start Bloomberg session. "
                f"Ensure Terminal is running on {self.host}:{self.port}"
            )

        if not self._session.openService(REF_DATA_SERVICE):
            raise BloombergError(f"Failed to open service: {REF_DATA_SERVICE}")

        self._ref_data_service = self._session.getService(REF_DATA_SERVICE)
        logger.info("Connected to Bloomberg Terminal at %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        """Disconnect from Bloomberg Terminal."""
        if self._session:
            self._session.stop()
            self._session = None
            self._ref_data_service = None
            logger.info("Disconnected from Bloomberg Terminal")

    def __enter__(self) -> BloombergSession:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()

    def _ensure_connected(self) -> None:
        """Ensure session is connected."""
        if not self._session or not self._ref_data_service:
            raise BloombergError("Not connected. Use 'with BloombergSession() as session:'")

    def get_reference_data(
        self,
        securities: Sequence[str],
        fields: Sequence[str],
    ) -> pd.DataFrame:
        """Get reference (snapshot) data for securities.

        Args:
            securities: List of Bloomberg tickers
            fields: List of Bloomberg fields

        Returns:
            DataFrame with securities as index and fields as columns
        """
        self._ensure_connected()

        request = self._ref_data_service.createRequest("ReferenceDataRequest")

        for security in securities:
            request.append("securities", security)

        for field in fields:
            request.append("fields", field)

        logger.debug("Sending reference data request for %d securities", len(securities))
        self._session.sendRequest(request)

        data: dict[str, dict[str, any]] = {}

        while True:
            event = self._session.nextEvent(500)

            for msg in event:
                if msg.hasElement("securityData"):
                    security_data = msg.getElement("securityData")

                    for i in range(security_data.numValues()):
                        security = security_data.getValueAsElement(i)
                        ticker = security.getElementAsString("security")
                        data[ticker] = {}

                        if security.hasElement("fieldData"):
                            field_data = security.getElement("fieldData")

                            for field in fields:
                                if field_data.hasElement(field):
                                    value = field_data.getElement(field).getValue()
                                    data[ticker][field] = value
                                else:
                                    data[ticker][field] = None

                        if security.hasElement("securityError"):
                            error = security.getElement("securityError")
                            error_msg = error.getElementAsString("message")
                            logger.warning("Security error for %s: %s", ticker, error_msg)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        df = pd.DataFrame.from_dict(data, orient="index")
        df.index.name = "security"
        return df

    def get_historical_data(
        self,
        securities: Sequence[str],
        fields: Sequence[str],
        start_date: date,
        end_date: date | None = None,
        periodicity: str = "DAILY",
    ) -> pd.DataFrame:
        """Get historical data for securities.

        Args:
            securities: List of Bloomberg tickers
            fields: List of Bloomberg fields
            start_date: Start date for historical data
            end_date: End date (default: today)
            periodicity: Data frequency (DAILY, WEEKLY, MONTHLY)

        Returns:
            DataFrame with MultiIndex (date, security) and fields as columns
        """
        self._ensure_connected()

        if end_date is None:
            end_date = date.today()

        request = self._ref_data_service.createRequest("HistoricalDataRequest")

        for security in securities:
            request.append("securities", security)

        for field in fields:
            request.append("fields", field)

        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", periodicity)

        logger.debug(
            "Sending historical data request for %d securities from %s to %s",
            len(securities),
            start_date,
            end_date,
        )
        self._session.sendRequest(request)

        records: list[dict] = []

        while True:
            event = self._session.nextEvent(500)

            for msg in event:
                if msg.hasElement("securityData"):
                    security_data = msg.getElement("securityData")
                    ticker = security_data.getElementAsString("security")

                    if security_data.hasElement("fieldData"):
                        field_data = security_data.getElement("fieldData")

                        for i in range(field_data.numValues()):
                            row = field_data.getValueAsElement(i)
                            record = {
                                "security": ticker,
                                "date": row.getElementAsDatetime("date").date(),
                            }

                            for field in fields:
                                if row.hasElement(field):
                                    record[field] = row.getElement(field).getValue()
                                else:
                                    record[field] = None

                            records.append(record)

                    if security_data.hasElement("securityError"):
                        error = security_data.getElement("securityError")
                        error_msg = error.getElementAsString("message")
                        logger.warning("Security error for %s: %s", ticker, error_msg)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.set_index(["date", "security"]).sort_index()
        return df


@contextmanager
def bloomberg_session(
    host: str = "localhost",
    port: int = 8194,
) -> Iterator[BloombergSession]:
    """Context manager for Bloomberg session.

    Args:
        host: Bloomberg Terminal host
        port: Bloomberg Terminal port

    Yields:
        Connected BloombergSession instance
    """
    session = BloombergSession(host, port)
    session.connect()
    try:
        yield session
    finally:
        session.disconnect()
