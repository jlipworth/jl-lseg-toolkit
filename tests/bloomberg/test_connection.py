from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from lseg_toolkit.bloomberg.connection import (
    BLOOMBERG_INSTALL_HINT,
    BloombergError,
    BloombergSession,
    connection_diagnostics,
    format_bloomberg_error,
)
from lseg_toolkit.exceptions import ConfigurationError


def test_init_raises_configuration_error_when_blpapi_missing():
    with patch(
        "lseg_toolkit.bloomberg.connection.import_module",
        side_effect=ImportError("missing blpapi"),
    ):
        with pytest.raises(ConfigurationError):
            BloombergSession()


def test_reference_data_normalizes_rows_without_live_session():
    session = object.__new__(BloombergSession)
    session._blpapi = SimpleNamespace(Event=SimpleNamespace(RESPONSE=1))
    session._ref_data_service = SimpleNamespace(
        createRequest=lambda name: SimpleNamespace(
            append=lambda *args, **kwargs: None
        )
    )

    class FakeFieldData:
        def __init__(self, values):
            self.values = values

        def hasElement(self, name):
            return name in self.values

        def getElement(self, name):
            return SimpleNamespace(getValue=lambda: self.values[name])

    class FakeSecurity:
        def __init__(self):
            self.values = {"security": "GJGB10 Index"}
            self.field_data = FakeFieldData({"PX_LAST": 2.19, "NAME": "JGB 10Y"})

        def getElementAsString(self, name):
            return self.values[name]

        def hasElement(self, name):
            return name == "fieldData"

        def getElement(self, name):
            if name == "fieldData":
                return self.field_data
            raise KeyError(name)

    class FakeSecurityArray:
        def numValues(self):
            return 1

        def getValueAsElement(self, index):
            return FakeSecurity()

    class FakeMessage:
        def hasElement(self, name):
            return name == "securityData"

        def getElement(self, name):
            return FakeSecurityArray()

    class FakeEvent:
        def __iter__(self):
            return iter([FakeMessage()])

        def eventType(self):
            return 1

    session._session = SimpleNamespace(
        sendRequest=lambda request: None,
        nextEvent=lambda timeout: FakeEvent(),
    )

    df = session.get_reference_data(["GJGB10 Index"], ["PX_LAST", "NAME"])

    assert isinstance(df, pd.DataFrame)
    assert df.loc[0, "security"] == "GJGB10 Index"
    assert df.loc[0, "PX_LAST"] == 2.19
    assert df.loc[0, "NAME"] == "JGB 10Y"


def test_historical_data_normalizes_rows_without_live_session():
    session = object.__new__(BloombergSession)
    session._blpapi = SimpleNamespace(Event=SimpleNamespace(RESPONSE=1))

    class FakeRequest:
        def append(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

    session._ref_data_service = SimpleNamespace(createRequest=lambda name: FakeRequest())

    class FakeRowElement:
        def hasElement(self, name):
            return name in {"date", "PX_LAST"}

        def getElementAsDatetime(self, name):
            return SimpleNamespace(date=lambda: date(2026, 3, 24))

        def getElement(self, name):
            return SimpleNamespace(getValue=lambda: 2.19)

    class FakeFieldData:
        def numValues(self):
            return 1

        def getValueAsElement(self, index):
            return FakeRowElement()

    class FakeSecurityData:
        def getElementAsString(self, name):
            return "GJGB10 Index"

        def hasElement(self, name):
            return name == "fieldData"

        def getElement(self, name):
            return FakeFieldData()

    class FakeMessage:
        def hasElement(self, name):
            return name == "securityData"

        def getElement(self, name):
            return FakeSecurityData()

    class FakeEvent:
        def __iter__(self):
            return iter([FakeMessage()])

        def eventType(self):
            return 1

    session._session = SimpleNamespace(
        sendRequest=lambda request: None,
        nextEvent=lambda timeout: FakeEvent(),
    )

    df = session.get_historical_data(
        ["GJGB10 Index"],
        ["PX_LAST"],
        start_date=date(2026, 3, 24),
        end_date=date(2026, 3, 24),
    )

    assert list(df.columns) == ["date", "security", "PX_LAST", "_security_error"]
    assert df.loc[0, "security"] == "GJGB10 Index"
    assert df.loc[0, "PX_LAST"] == 2.19


def test_reference_data_raises_on_top_level_response_error():
    session = object.__new__(BloombergSession)
    session.host = "localhost"
    session.port = 8194
    session._blpapi = SimpleNamespace(Event=SimpleNamespace(RESPONSE=1))
    session._ref_data_service = SimpleNamespace(
        createRequest=lambda name: SimpleNamespace(
            append=lambda *args, **kwargs: None
        )
    )

    class FakeValue:
        def __init__(self, value):
            self.value = value

        def getValue(self):
            return self.value

    class FakeResponseError:
        def __init__(self):
            self.values = {
                "source": "rsfrdsvc2",
                "code": -4002,
                "category": "LIMIT",
                "subcategory": "WORKFLOW_REVIEW_NEEDED",
                "message": "Workflow review needed. [nid:19533]",
            }

        def hasElement(self, name):
            return name in self.values

        def getElement(self, name):
            return FakeValue(self.values[name])

    class FakeMessage:
        def hasElement(self, name):
            return name == "responseError"

        def getElement(self, name):
            if name == "responseError":
                return FakeResponseError()
            raise KeyError(name)

    class FakeEvent:
        def __iter__(self):
            return iter([FakeMessage()])

        def eventType(self):
            return 1

    session._session = SimpleNamespace(
        sendRequest=lambda request: None,
        nextEvent=lambda timeout: FakeEvent(),
    )

    with pytest.raises(BloombergError, match="WORKFLOW_REVIEW_NEEDED"):
        session.get_reference_data(["EURUSD Curncy"], ["PX_LAST"])


def test_ensure_connected_raises_when_not_connected():
    session = object.__new__(BloombergSession)
    session._session = None
    session._ref_data_service = None

    with pytest.raises(BloombergError):
        session._ensure_connected()


def test_install_hint_mentions_uv_group():
    assert "uv sync --group bloomberg" in BLOOMBERG_INSTALL_HINT


def test_connection_diagnostics_include_port_check_hint():
    diagnostics = connection_diagnostics(host="localhost", port=8194)

    assert any("Bloomberg Terminal" in item for item in diagnostics)
    assert any("nc -z localhost 8194" in item for item in diagnostics)


def test_format_bloomberg_error_appends_diagnostics():
    message = format_bloomberg_error("Failed to start Bloomberg session.")

    assert "Failed to start Bloomberg session." in message
    assert "Bloomberg Terminal" in message
    assert "nc -z localhost 8194" in message
