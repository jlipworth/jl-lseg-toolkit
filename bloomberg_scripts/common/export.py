"""Export utilities for Parquet and CSV output."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _add_timestamp_suffix(base_path: Path, timestamp: date | None = None) -> Path:
    """Add timestamp suffix to filename.

    Args:
        base_path: Base file path
        timestamp: Date to use (default: today)

    Returns:
        Path with timestamp suffix before extension
    """
    if timestamp is None:
        timestamp = date.today()

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    return parent / f"{stem}_{timestamp.isoformat()}{suffix}"


def export_to_parquet(
    df: pd.DataFrame,
    output_path: str | Path,
    *,
    add_timestamp: bool = True,
    compression: str = "snappy",
) -> Path:
    """Export DataFrame to Parquet file.

    Args:
        df: DataFrame to export
        output_path: Output file path (without timestamp)
        add_timestamp: Add date suffix to filename
        compression: Compression algorithm (snappy, gzip, zstd)

    Returns:
        Path to written file
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    output_path = Path(output_path)

    if add_timestamp:
        output_path = _add_timestamp_suffix(output_path)

    _ensure_dir(output_path)

    # Convert to PyArrow table
    table = pa.Table.from_pandas(df)

    pq.write_table(
        table,
        output_path,
        compression=compression,
    )

    logger.info("Exported %d rows to %s", len(df), output_path)
    return output_path


def export_to_csv(
    df: pd.DataFrame,
    output_path: str | Path,
    *,
    add_timestamp: bool = True,
) -> Path:
    """Export DataFrame to CSV file.

    Args:
        df: DataFrame to export
        output_path: Output file path (without timestamp)
        add_timestamp: Add date suffix to filename

    Returns:
        Path to written file
    """
    output_path = Path(output_path)

    if add_timestamp:
        output_path = _add_timestamp_suffix(output_path)

    _ensure_dir(output_path)

    df.to_csv(output_path)

    logger.info("Exported %d rows to %s", len(df), output_path)
    return output_path


def get_default_output_dir() -> Path:
    """Get default output directory for Bloomberg data.

    Returns:
        Path to data/bloomberg directory
    """
    return Path("data/bloomberg")


def build_output_path(
    instrument_type: str,
    name: str,
    output_dir: Path | None = None,
    extension: str = ".parquet",
) -> Path:
    """Build standard output path for instrument data.

    Args:
        instrument_type: Type of instrument (swaptions, caps_floors, etc.)
        name: Base filename without extension
        output_dir: Output directory (default: data/bloomberg)
        extension: File extension

    Returns:
        Path like data/bloomberg/swaptions/usd_swaption_vol.parquet
    """
    if output_dir is None:
        output_dir = get_default_output_dir()

    return output_dir / instrument_type / f"{name}{extension}"
