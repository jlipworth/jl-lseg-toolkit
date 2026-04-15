"""
Bloomberg Desktop API connection helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from importlib import import_module
from typing import TYPE_CHECKING, Any

import pandas as pd

from lseg_toolkit.exceptions import ConfigurationError, DataRetrievalError

from .normalize import normalize_historical_rows, normalize_reference_rows

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


REF_DATA_SERVICE = "//blp/refdata"
BLOOMBERG_INSTALL_HINT = "Install Bloomberg support with `uv sync --group bloomberg`."


class BloombergError(DataRetrievalError):
    """Bloomberg Desktop API error."""


def _import_blpapi():
    try:
        return import_module("blpapi")
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ConfigurationError(
            f"blpapi is not installed. {BLOOMBERG_INSTALL_HINT}"
        ) from exc


def connection_diagnostics(host: str = "localhost", port: int = 8194) -> list[str]:
    """Return actionable Bloomberg runtime diagnostics."""
    return [
        "Ensure Bloomberg Terminal is running and logged in on the host machine.",
        f"Verify Bloomberg Desktop API connectivity on {host}:{port}.",
        f"WSL users can test the port with `nc -z {host} {port}` and may need mirrored networking enabled.",
    ]


def format_bloomberg_error(
    message: str,
    host: str = "localhost",
    port: int = 8194,
) -> str:
    """Append actionable diagnostics to a Bloomberg runtime error message."""
    diagnostics = connection_diagnostics(host=host, port=port)
    details = "\n".join(f"- {line}" for line in diagnostics)
    return f"{message}\n{details}"


class BloombergSession:
    """Minimal Bloomberg Desktop API session wrapper."""

    def __init__(self, host: str = "localhost", port: int = 8194) -> None:
        self.host = host
        self.port = port
        self._blpapi = _import_blpapi()
        self._session: Any = None
        self._ref_data_service: Any = None

    def connect(self) -> None:
        options = self._blpapi.SessionOptions()
        options.setServerHost(self.host)
        options.setServerPort(self.port)

        self._session = self._blpapi.Session(options)

        if not self._session.start():
            raise BloombergError(
                format_bloomberg_error(
                    f"Failed to start Bloomberg session on {self.host}:{self.port}.",
                    host=self.host,
                    port=self.port,
                )
            )

        if not self._session.openService(REF_DATA_SERVICE):
            self._session.stop()
            self._session = None
            raise BloombergError(
                format_bloomberg_error(
                    f"Failed to open Bloomberg service {REF_DATA_SERVICE}.",
                    host=self.host,
                    port=self.port,
                )
            )

        self._ref_data_service = self._session.getService(REF_DATA_SERVICE)

    def disconnect(self) -> None:
        if self._session is not None:
            self._session.stop()
        self._session = None
        self._ref_data_service = None

    def __enter__(self) -> BloombergSession:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def _ensure_connected(self) -> None:
        if self._session is None or self._ref_data_service is None:
            raise BloombergError("Bloomberg session is not connected.")

    @staticmethod
    def _element_value(element: Any, name: str) -> Any | None:
        if not element.hasElement(name):
            return None

        child = element.getElement(name)
        return child.getValue()

    def _raise_response_error(self, msg: Any) -> None:
        if not msg.hasElement("responseError"):
            return

        error = msg.getElement("responseError")
        details: list[str] = []
        for field in ("source", "code", "category", "subcategory", "message"):
            value = self._element_value(error, field)
            if value is not None:
                details.append(f"{field}={value}")

        detail_text = (
            ", ".join(details) if details else "unknown Bloomberg responseError"
        )
        raise BloombergError(
            format_bloomberg_error(
                f"Bloomberg request failed: {detail_text}",
                host=getattr(self, "host", "localhost"),
                port=getattr(self, "port", 8194),
            )
        )

    def get_reference_data(
        self,
        securities: Sequence[str],
        fields: Sequence[str],
    ) -> pd.DataFrame:
        """Fetch normalized reference data."""
        self._ensure_connected()

        request = self._ref_data_service.createRequest("ReferenceDataRequest")
        for security in securities:
            request.append("securities", security)
        for field in fields:
            request.append("fields", field)

        self._session.sendRequest(request)

        rows: list[dict[str, Any]] = []

        while True:
            event = self._session.nextEvent(5000)
            for msg in event:
                self._raise_response_error(msg)
                if not msg.hasElement("securityData"):
                    continue

                security_data = msg.getElement("securityData")
                for i in range(security_data.numValues()):
                    security = security_data.getValueAsElement(i)
                    row: dict[str, Any] = {
                        "security": security.getElementAsString("security"),
                    }

                    if security.hasElement("securityError"):
                        error = security.getElement("securityError")
                        row["_security_error"] = error.getElementAsString("message")

                    if security.hasElement("fieldData"):
                        field_data = security.getElement("fieldData")
                        for field in fields:
                            if field_data.hasElement(field):
                                row[field] = field_data.getElement(field).getValue()
                            else:
                                row[field] = None

                    rows.append(row)

            if event.eventType() == self._blpapi.Event.RESPONSE:
                break

        return normalize_reference_rows(rows, fields)

    def get_historical_data(
        self,
        securities: Sequence[str],
        fields: Sequence[str],
        start_date: date,
        end_date: date | None = None,
        periodicity: str = "DAILY",
    ) -> pd.DataFrame:
        """Fetch normalized historical data."""
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

        self._session.sendRequest(request)

        rows: list[dict[str, Any]] = []

        while True:
            event = self._session.nextEvent(5000)
            for msg in event:
                self._raise_response_error(msg)
                if not msg.hasElement("securityData"):
                    continue

                security_data = msg.getElement("securityData")
                ticker = security_data.getElementAsString("security")
                security_error = None

                if security_data.hasElement("securityError"):
                    error = security_data.getElement("securityError")
                    security_error = error.getElementAsString("message")

                if security_data.hasElement("fieldData"):
                    field_data = security_data.getElement("fieldData")
                    for i in range(field_data.numValues()):
                        row_element = field_data.getValueAsElement(i)
                        row: dict[str, Any] = {
                            "date": row_element.getElementAsDatetime("date").date(),
                            "security": ticker,
                            "_security_error": security_error,
                        }
                        for field in fields:
                            if row_element.hasElement(field):
                                row[field] = row_element.getElement(field).getValue()
                            else:
                                row[field] = None
                        rows.append(row)

            if event.eventType() == self._blpapi.Event.RESPONSE:
                break

        return normalize_historical_rows(rows, fields)


@contextmanager
def bloomberg_session(
    host: str = "localhost",
    port: int = 8194,
) -> Iterator[BloombergSession]:
    """Context manager wrapper for BloombergSession."""
    session = BloombergSession(host=host, port=port)
    session.connect()
    try:
        yield session
    finally:
        session.disconnect()
