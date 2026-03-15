"""Load manually downloaded CME FedWatch probability exports."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BUCKET_COLUMN_ALIASES = {
    "as_of_date": {"as_of_date", "date", "trade_date", "observation_date"},
    "meeting_date": {"meeting_date", "meeting", "fomc_meeting_date", "meeting_dt"},
    "rate_bucket": {"rate_bucket", "bucket", "target_range", "range"},
    "probability": {"probability", "prob", "pct", "percentage"},
}


def _canonical_column_name(column: str) -> str:
    if re.search(r"\d", column) and ("-" in column or "–" in column or "—" in column):
        return column.strip()
    normalized = column.strip().lower().replace(" ", "_")
    normalized = normalized.replace("%", "pct")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized).strip("_")
    for canonical, aliases in BUCKET_COLUMN_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized


def _normalize_bucket_label(label: str) -> str:
    cleaned = str(label).strip()
    cleaned = cleaned.replace("%", "").replace("Target Rate", "").strip()
    cleaned = cleaned.replace("to", "-").replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"\s+", "", cleaned)

    match = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", cleaned)
    if not match:
        raise ValueError(f"Unsupported FedWatch bucket label: {label!r}")

    low = float(match.group(1))
    high = float(match.group(2))
    return f"{low:.2f}-{high:.2f}"


def _read_frame(path: str | Path, sheet_name: str | int | None = 0) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(f"Unsupported FedWatch file type: {path.suffix}")


def normalize_fedwatch_frame(
    df: pd.DataFrame,
    *,
    meeting_date: str | None = None,
    probability_scale: str = "percent",
) -> pd.DataFrame:
    """
    Normalize a FedWatch export into a long probability frame.

    Supported input shapes:
    - long format with columns like date/meeting_date/rate_bucket/probability
    - wide format with one date column and many bucket columns
    """
    renamed = df.rename(columns={column: _canonical_column_name(column) for column in df.columns})

    if {"as_of_date", "rate_bucket", "probability"}.issubset(renamed.columns):
        normalized = renamed.copy()
        if "meeting_date" not in normalized.columns:
            if meeting_date is None:
                raise ValueError("meeting_date is required when the FedWatch file omits it")
            normalized["meeting_date"] = meeting_date
        normalized = normalized[["as_of_date", "meeting_date", "rate_bucket", "probability"]]
    else:
        as_of_candidates = [
            column for column in renamed.columns if column == "as_of_date"
        ]
        if len(as_of_candidates) != 1:
            raise ValueError(
                "Could not identify a single as_of_date column in FedWatch export"
            )
        as_of_column = as_of_candidates[0]
        if meeting_date is None and "meeting_date" not in renamed.columns:
            raise ValueError("meeting_date is required for wide FedWatch exports")

        id_columns = [as_of_column]
        if "meeting_date" in renamed.columns:
            id_columns.append("meeting_date")

        value_columns = [column for column in renamed.columns if column not in id_columns]
        normalized = renamed.melt(
            id_vars=id_columns,
            value_vars=value_columns,
            var_name="rate_bucket",
            value_name="probability",
        )
        if "meeting_date" not in normalized.columns:
            normalized["meeting_date"] = meeting_date

    normalized = normalized.dropna(subset=["probability"]).copy()
    normalized["as_of_date"] = pd.to_datetime(normalized["as_of_date"]).dt.date
    normalized["meeting_date"] = pd.to_datetime(normalized["meeting_date"]).dt.date
    normalized["rate_bucket"] = normalized["rate_bucket"].map(_normalize_bucket_label)
    normalized["probability"] = pd.to_numeric(normalized["probability"], errors="coerce")
    normalized = normalized.dropna(subset=["probability"])

    if probability_scale == "percent":
        normalized["probability"] = normalized["probability"] / 100.0
    elif probability_scale != "decimal":
        raise ValueError("probability_scale must be 'percent' or 'decimal'")

    normalized = normalized[
        (normalized["probability"] >= 0.0) & (normalized["probability"] <= 1.0)
    ].copy()
    normalized = normalized.sort_values(
        ["meeting_date", "as_of_date", "rate_bucket"]
    ).reset_index(drop=True)
    return normalized


def load_fedwatch_probabilities(
    path: str | Path,
    *,
    meeting_date: str | None = None,
    probability_scale: str = "percent",
    sheet_name: str | int | None = 0,
) -> pd.DataFrame:
    """Load and normalize a FedWatch CSV/XLS/XLSX export."""
    df = _read_frame(path, sheet_name=sheet_name)
    return normalize_fedwatch_frame(
        df,
        meeting_date=meeting_date,
        probability_scale=probability_scale,
    )


def build_distribution(
    df: pd.DataFrame,
    *,
    meeting_date: str | None = None,
    as_of_date: str | None = None,
) -> dict[str, float]:
    """Build a bucket->probability mapping from a normalized FedWatch frame."""
    working = df.copy()
    if meeting_date is not None:
        meeting_date_value = pd.to_datetime(meeting_date).date()
        working = working[working["meeting_date"] == meeting_date_value]
    if as_of_date is not None:
        as_of_date_value = pd.to_datetime(as_of_date).date()
        working = working[working["as_of_date"] == as_of_date_value]
    if working.empty:
        return {}

    grouped = (
        working.groupby("rate_bucket", as_index=False)["probability"]
        .last()
        .sort_values("rate_bucket")
    )
    total = float(grouped["probability"].sum())
    if total <= 0:
        return {}
    return {
        row["rate_bucket"]: float(row["probability"]) / total
        for _, row in grouped.iterrows()
    }
