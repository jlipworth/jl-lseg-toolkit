"""
Normalization helpers for Bloomberg responses.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def normalize_reference_rows(
    rows: Iterable[dict[str, Any]],
    field_names: Sequence[str],
) -> pd.DataFrame:
    """Normalize Bloomberg reference-data rows into a stable DataFrame."""
    normalized_rows: list[dict[str, Any]] = []

    for row in rows:
        normalized = {"security": row.get("security")}
        for field_name in field_names:
            normalized[field_name] = row.get(field_name)
        normalized["_security_error"] = row.get("_security_error")
        normalized_rows.append(normalized)

    return pd.DataFrame(normalized_rows)


def normalize_historical_rows(
    rows: Iterable[dict[str, Any]],
    field_names: Sequence[str],
) -> pd.DataFrame:
    """Normalize Bloomberg historical-data rows into a stable DataFrame."""
    normalized_rows: list[dict[str, Any]] = []

    for row in rows:
        normalized = {
            "date": row.get("date"),
            "security": row.get("security"),
        }
        for field_name in field_names:
            normalized[field_name] = row.get(field_name)
        normalized["_security_error"] = row.get("_security_error")
        normalized_rows.append(normalized)

    df = pd.DataFrame(normalized_rows)
    if not df.empty and {"date", "security"}.issubset(df.columns):
        df = df.sort_values(["date", "security"]).reset_index(drop=True)
    return df


def add_extraction_metadata(
    df: pd.DataFrame,
    extraction_date: date | None = None,
) -> pd.DataFrame:
    """Add a stable extraction date column."""
    if extraction_date is None:
        extraction_date = date.today()

    result = df.copy()
    result["extract_date"] = extraction_date.isoformat()
    return result
