from datetime import date

from lseg_toolkit.bloomberg.normalize import (
    add_extraction_metadata,
    normalize_historical_rows,
    normalize_reference_rows,
)


def test_normalize_reference_rows_preserves_security_and_fields():
    df = normalize_reference_rows(
        [
            {"security": "GJGB10 Index", "PX_LAST": 2.19, "NAME": "JGB 10Y"},
        ],
        ["PX_LAST", "NAME"],
    )

    assert list(df.columns) == ["security", "PX_LAST", "NAME", "_security_error"]
    assert df.loc[0, "security"] == "GJGB10 Index"
    assert df.loc[0, "PX_LAST"] == 2.19


def test_normalize_historical_rows_sorts_by_date_then_security():
    df = normalize_historical_rows(
        [
            {"date": date(2026, 1, 2), "security": "B", "PX_LAST": 2.0},
            {"date": date(2026, 1, 1), "security": "A", "PX_LAST": 1.0},
        ],
        ["PX_LAST"],
    )

    assert list(df["security"]) == ["A", "B"]


def test_add_extraction_metadata_adds_iso_date():
    df = add_extraction_metadata(
        normalize_reference_rows(
            [{"security": "GJGB2 Index", "PX_LAST": 1.2}],
            ["PX_LAST"],
        ),
        extraction_date=date(2026, 3, 24),
    )

    assert df.loc[0, "extract_date"] == "2026-03-24"
