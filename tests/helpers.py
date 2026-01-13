"""
Common test helper functions for DataFrame validation and assertions.

These helpers reduce boilerplate in tests and provide consistent error messages.
"""

from collections.abc import Sequence
from datetime import date, datetime

import pandas as pd


def assert_dataframe_columns(
    df: pd.DataFrame,
    expected_cols: Sequence[str],
    *,
    exact: bool = False,
) -> None:
    """Assert that a DataFrame has expected columns.

    Args:
        df: DataFrame to check
        expected_cols: Columns that must be present
        exact: If True, df must have exactly these columns (no extras)

    Raises:
        AssertionError: If columns are missing or (if exact) extra columns exist
    """
    actual = set(df.columns)
    expected = set(expected_cols)

    missing = expected - actual
    if missing:
        raise AssertionError(f"Missing columns: {sorted(missing)}")

    if exact:
        extra = actual - expected
        if extra:
            raise AssertionError(f"Unexpected columns: {sorted(extra)}")


def assert_no_nulls(
    df: pd.DataFrame,
    cols: Sequence[str] | None = None,
) -> None:
    """Assert that specified columns (or all) have no null values.

    Args:
        df: DataFrame to check
        cols: Columns to check. If None, checks all columns.

    Raises:
        AssertionError: If any null values are found
    """
    check_cols = cols if cols is not None else df.columns.tolist()

    for col in check_cols:
        if col not in df.columns:
            raise AssertionError(f"Column '{col}' not in DataFrame")

        null_count = df[col].isna().sum()
        if null_count > 0:
            raise AssertionError(
                f"Column '{col}' has {null_count} null values out of {len(df)} rows"
            )


def assert_date_range(
    df: pd.DataFrame,
    date_col: str,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
) -> None:
    """Assert that dates in a column fall within a range.

    Args:
        df: DataFrame to check
        date_col: Name of date column
        start: Minimum date (inclusive), or None for no lower bound
        end: Maximum date (inclusive), or None for no upper bound

    Raises:
        AssertionError: If any dates fall outside the range
    """
    if date_col not in df.columns:
        raise AssertionError(f"Column '{date_col}' not in DataFrame")

    dates = pd.to_datetime(df[date_col])

    if start is not None:
        start_dt = pd.to_datetime(start)
        min_date = dates.min()
        if min_date < start_dt:
            raise AssertionError(
                f"Minimum date {min_date} is before start date {start_dt}"
            )

    if end is not None:
        end_dt = pd.to_datetime(end)
        max_date = dates.max()
        if max_date > end_dt:
            raise AssertionError(f"Maximum date {max_date} is after end date {end_dt}")


def assert_dataframe_not_empty(df: pd.DataFrame, msg: str = "") -> None:
    """Assert that a DataFrame is not empty.

    Args:
        df: DataFrame to check
        msg: Optional message to include in error

    Raises:
        AssertionError: If DataFrame is empty
    """
    if df.empty:
        base_msg = "DataFrame is empty"
        raise AssertionError(f"{base_msg}: {msg}" if msg else base_msg)


def assert_column_numeric(
    df: pd.DataFrame,
    cols: Sequence[str],
) -> None:
    """Assert that specified columns contain numeric data.

    Args:
        df: DataFrame to check
        cols: Column names to verify

    Raises:
        AssertionError: If any column is not numeric
    """
    for col in cols:
        if col not in df.columns:
            raise AssertionError(f"Column '{col}' not in DataFrame")

        if not pd.api.types.is_numeric_dtype(df[col]):
            raise AssertionError(
                f"Column '{col}' has dtype {df[col].dtype}, expected numeric"
            )


def assert_column_values_in(
    df: pd.DataFrame,
    col: str,
    allowed_values: Sequence,
) -> None:
    """Assert that all values in a column are from an allowed set.

    Args:
        df: DataFrame to check
        col: Column name to verify
        allowed_values: Set of allowed values

    Raises:
        AssertionError: If any value is not in allowed set
    """
    if col not in df.columns:
        raise AssertionError(f"Column '{col}' not in DataFrame")

    actual = set(df[col].dropna().unique())
    allowed = set(allowed_values)
    invalid = actual - allowed

    if invalid:
        raise AssertionError(
            f"Column '{col}' contains invalid values: {sorted(invalid)}"
        )


def assert_unique_column(df: pd.DataFrame, col: str) -> None:
    """Assert that a column contains only unique values.

    Args:
        df: DataFrame to check
        col: Column name to verify

    Raises:
        AssertionError: If column contains duplicates
    """
    if col not in df.columns:
        raise AssertionError(f"Column '{col}' not in DataFrame")

    duplicates = df[col][df[col].duplicated()].unique()
    if len(duplicates) > 0:
        raise AssertionError(
            f"Column '{col}' has {len(duplicates)} duplicate values: {list(duplicates[:5])}"
        )
