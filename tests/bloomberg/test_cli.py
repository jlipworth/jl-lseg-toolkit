import argparse

import pytest

from lseg_toolkit.bloomberg.cli import create_parser, main, parse_date
from lseg_toolkit.bloomberg.connection import BloombergError, format_bloomberg_error
from lseg_toolkit.exceptions import ConfigurationError


def test_parse_date():
    result = parse_date("2026-03-24")
    assert result.isoformat() == "2026-03-24"


def test_parse_date_rejects_invalid_format():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_date("03/24/2026")


def test_cli_supports_only_jgb_and_fx_atm_vol():
    parser = create_parser()
    choices = parser._subparsers._group_actions[0].choices

    assert set(choices.keys()) == {"jgb", "fx-atm-vol"}


def test_main_reports_configuration_error(monkeypatch, capsys):
    def raise_error(*args, **kwargs):
        raise ConfigurationError(
            "blpapi is not installed. Install Bloomberg support with `uv sync --group bloomberg`."
        )

    monkeypatch.setattr("lseg_toolkit.bloomberg.cli.extract_jgb_snapshot", raise_error)

    exit_code = main(["jgb"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Bloomberg configuration error:" in captured.err
    assert "uv sync --group bloomberg" in captured.err


def test_main_reports_runtime_error(monkeypatch, capsys):
    def raise_error(*args, **kwargs):
        raise BloombergError(
            format_bloomberg_error("Failed to start Bloomberg session.")
        )

    monkeypatch.setattr(
        "lseg_toolkit.bloomberg.cli.extract_fx_atm_vol_snapshot",
        raise_error,
    )

    exit_code = main(["fx-atm-vol"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Bloomberg runtime error:" in captured.err
    assert "nc -z localhost 8194" in captured.err
