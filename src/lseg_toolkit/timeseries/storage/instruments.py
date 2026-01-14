"""
Instrument CRUD operations for PostgreSQL/TimescaleDB storage.

This module provides functions for saving, updating, and retrieving
instrument metadata, including type-specific details tables.
"""

from __future__ import annotations

import psycopg

from lseg_toolkit.exceptions import StorageError
from lseg_toolkit.timeseries.enums import AssetClass, DataShape

# =============================================================================
# Asset Class to Data Shape Mapping
# =============================================================================

ASSET_CLASS_TO_DATA_SHAPE: dict[AssetClass, DataShape] = {
    # OHLCV (exchange-traded)
    AssetClass.BOND_FUTURES: DataShape.OHLCV,
    AssetClass.STIR_FUTURES: DataShape.OHLCV,
    AssetClass.INDEX_FUTURES: DataShape.OHLCV,
    AssetClass.FX_FUTURES: DataShape.OHLCV,
    AssetClass.COMMODITY_FUTURES: DataShape.OHLCV,  # CLc1, GCc1, NGc1
    AssetClass.EQUITY: DataShape.OHLCV,
    AssetClass.ETF: DataShape.OHLCV,  # SPY.P, QQQ.O
    AssetClass.EQUITY_INDEX: DataShape.OHLCV,  # .SPX, .DJI, .VIX
    # Quote (dealer-quoted)
    AssetClass.FX_SPOT: DataShape.QUOTE,
    AssetClass.FX_FORWARD: DataShape.QUOTE,
    AssetClass.COMMODITY: DataShape.QUOTE,  # XAU=, XAG= (spot commodities are bid/ask)
    # Rate (IR derivatives)
    AssetClass.OIS: DataShape.RATE,
    AssetClass.IRS: DataShape.RATE,
    AssetClass.FRA: DataShape.RATE,
    AssetClass.DEPOSIT: DataShape.RATE,
    AssetClass.REPO: DataShape.RATE,
    AssetClass.CDS: DataShape.RATE,
    # Bond (govt/corp yields)
    AssetClass.GOVT_YIELD: DataShape.BOND,
    AssetClass.CORP_BOND: DataShape.BOND,
    # Fixing (daily benchmark rates)
    AssetClass.FIXING: DataShape.FIXING,
    # Options (use OHLCV for historical bars)
    AssetClass.OPTION: DataShape.OHLCV,
}


def get_data_shape(asset_class: AssetClass) -> DataShape:
    """Get the data shape for an asset class."""
    return ASSET_CLASS_TO_DATA_SHAPE.get(asset_class, DataShape.OHLCV)


# =============================================================================
# Detail Table Configuration
# =============================================================================

# Maps asset_class.value -> (table_name, list of valid field names)
# table_name is None for asset classes that don't have a detail table
DETAIL_TABLES: dict[str, tuple[str | None, list[str]]] = {
    # Futures (all types share same table)
    "bond_futures": (
        "instrument_futures",
        [
            "underlying",
            "exchange",
            "expiry_date",
            "contract_month",
            "continuous_type",
            "tick_size",
            "point_value",
        ],
    ),
    "stir_futures": (
        "instrument_futures",
        [
            "underlying",
            "exchange",
            "expiry_date",
            "contract_month",
            "continuous_type",
            "tick_size",
            "point_value",
        ],
    ),
    "index_futures": (
        "instrument_futures",
        [
            "underlying",
            "exchange",
            "expiry_date",
            "contract_month",
            "continuous_type",
            "tick_size",
            "point_value",
        ],
    ),
    "fx_futures": (
        "instrument_futures",
        [
            "underlying",
            "exchange",
            "expiry_date",
            "contract_month",
            "continuous_type",
            "tick_size",
            "point_value",
        ],
    ),
    "commodity_futures": (
        "instrument_futures",
        [
            "underlying",
            "exchange",
            "expiry_date",
            "contract_month",
            "continuous_type",
            "tick_size",
            "point_value",
        ],
    ),
    # FX
    "fx_spot": (
        "instrument_fx",
        ["base_currency", "quote_currency", "pip_size", "tenor"],
    ),
    "fx_forward": (
        "instrument_fx",
        ["base_currency", "quote_currency", "pip_size", "tenor"],
    ),
    # Rates
    "ois": (
        "instrument_rate",
        [
            "rate_type",
            "currency",
            "tenor",
            "reference_rate",
            "day_count",
            "payment_frequency",
            "business_day_conv",
            "calendar",
            "settlement_days",
            "paired_instrument_id",
        ],
    ),
    "irs": (
        "instrument_rate",
        [
            "rate_type",
            "currency",
            "tenor",
            "reference_rate",
            "day_count",
            "payment_frequency",
            "business_day_conv",
            "calendar",
            "settlement_days",
            "paired_instrument_id",
        ],
    ),
    "fra": (
        "instrument_rate",
        [
            "rate_type",
            "currency",
            "tenor",
            "reference_rate",
            "day_count",
            "payment_frequency",
            "business_day_conv",
            "calendar",
            "settlement_days",
            "paired_instrument_id",
        ],
    ),
    "deposit": (
        "instrument_rate",
        [
            "rate_type",
            "currency",
            "tenor",
            "reference_rate",
            "day_count",
            "payment_frequency",
            "business_day_conv",
            "calendar",
            "settlement_days",
            "paired_instrument_id",
        ],
    ),
    "repo": (
        "instrument_rate",
        [
            "rate_type",
            "currency",
            "tenor",
            "reference_rate",
            "day_count",
            "payment_frequency",
            "business_day_conv",
            "calendar",
            "settlement_days",
            "paired_instrument_id",
        ],
    ),
    "cds": (
        "instrument_cds",
        [
            "index_family",
            "series",
            "tenor",
            "currency",
            "restructuring_type",
            "reference_entity",
        ],
    ),
    # Bonds
    "govt_yield": (
        "instrument_bond",
        [
            "issuer_type",
            "country",
            "tenor",
            "coupon_rate",
            "coupon_frequency",
            "day_count",
            "maturity_date",
            "settlement_days",
            "credit_rating",
            "sector",
        ],
    ),
    "corp_bond": (
        "instrument_bond",
        [
            "issuer_type",
            "country",
            "tenor",
            "coupon_rate",
            "coupon_frequency",
            "day_count",
            "maturity_date",
            "settlement_days",
            "credit_rating",
            "sector",
        ],
    ),
    # Fixings
    "fixing": (
        "instrument_fixing",
        ["rate_name", "tenor", "fixing_time", "administrator"],
    ),
    # Equities
    "equity": (
        "instrument_equity",
        [
            "exchange",
            "country",
            "currency",
            "sector",
            "industry",
            "isin",
            "cusip",
            "sedol",
            "market_cap_category",
        ],
    ),
    # ETFs
    "etf": (
        "instrument_etf",
        [
            "exchange",
            "country",
            "currency",
            "asset_class_focus",
            "geography_focus",
            "benchmark_index",
            "expense_ratio",
            "isin",
            "cusip",
            "is_leveraged",
            "is_inverse",
        ],
    ),
    # Indices
    "equity_index": (
        "instrument_index",
        [
            "index_family",
            "country",
            "calculation_method",
            "currency",
            "num_constituents",
            "base_date",
            "base_value",
        ],
    ),
    # Commodities (spot)
    "commodity": (
        "instrument_commodity",
        ["commodity_type", "unit", "currency", "quote_convention"],
    ),
    # Options
    "option": (
        "instrument_option",
        [
            "underlying_symbol",
            "underlying_id",
            "option_type",
            "strike",
            "expiry_date",
            "exercise_style",
            "contract_size",
            "exchange",
            "root_symbol",
        ],
    ),
}


# =============================================================================
# Unified Instrument Details Upsert
# =============================================================================


# Default values for required fields by asset class
REQUIRED_FIELD_DEFAULTS: dict[str, dict[str, str | int]] = {
    "ois": {"rate_type": "OIS"},
    "irs": {"rate_type": "IRS"},
    "fra": {"rate_type": "FRA"},
    "deposit": {"rate_type": "DEPOSIT"},
    "repo": {"rate_type": "REPO"},
    "cds": {"rate_type": "CDS"},
    "govt_yield": {"issuer_type": "GOVT"},
    "corp_bond": {"issuer_type": "CORP"},
}


def _upsert_instrument_details(
    conn: psycopg.Connection,
    instrument_id: int,
    asset_class: str,
    **kwargs,
) -> None:
    """
    Upsert instrument details to the appropriate table.

    This replaces 7+ individual _save_*_details functions with a single
    unified function that routes to the correct table based on asset_class.

    Args:
        conn: Database connection.
        instrument_id: Instrument ID.
        asset_class: Asset class value (e.g., 'bond_futures', 'fx_spot').
        **kwargs: Detail fields for the asset class.
    """
    if asset_class not in DETAIL_TABLES:
        return  # No detail table for this asset class

    table, valid_fields = DETAIL_TABLES[asset_class]

    if table is None:
        return  # Asset class doesn't have a detail table

    # Add defaults for required fields if not provided
    if asset_class in REQUIRED_FIELD_DEFAULTS:
        for field, default in REQUIRED_FIELD_DEFAULTS[asset_class].items():
            if field not in kwargs or kwargs[field] is None:
                kwargs[field] = default

    # Filter to only valid fields that have values
    details = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}

    if not details:
        return

    # Check if exists
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {table} WHERE instrument_id = %s",  # noqa: S608
            [instrument_id],
        )
        exists = cur.fetchone()

        if exists:
            # UPDATE
            set_clause = ", ".join(f"{k} = %s" for k in details)
            cur.execute(
                f"UPDATE {table} SET {set_clause} WHERE instrument_id = %s",  # noqa: S608
                list(details.values()) + [instrument_id],
            )
        else:
            # INSERT
            cols = ["instrument_id", *list(details.keys())]
            placeholders = ", ".join("%s" for _ in cols)
            cur.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",  # noqa: S608
                [instrument_id, *list(details.values())],
            )


# =============================================================================
# Instrument CRUD
# =============================================================================


def save_instrument(
    conn: psycopg.Connection,
    symbol: str,
    name: str,
    asset_class: AssetClass,
    lseg_ric: str,
    data_shape: DataShape | None = None,
    **kwargs,
) -> int:
    """
    Save or update an instrument.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.
        name: Human-readable name.
        asset_class: Asset class.
        lseg_ric: LSEG RIC code.
        data_shape: Data shape (auto-inferred from asset_class if not provided).
        **kwargs: Additional fields for specific instrument types.

    Returns:
        Instrument ID.

    Raises:
        StorageError: If save fails.
    """
    # Auto-infer data_shape from asset_class if not provided
    if data_shape is None:
        data_shape = get_data_shape(asset_class)

    try:
        with conn.cursor() as cur:
            # Check if instrument exists
            cur.execute("SELECT id FROM instruments WHERE symbol = %s", [symbol])
            result = cur.fetchone()

            if result:
                # Update existing
                instrument_id = result[0]
                cur.execute(
                    """
                    UPDATE instruments SET
                        name = %s,
                        asset_class = %s,
                        data_shape = %s,
                        lseg_ric = %s,
                        updated_at = current_timestamp
                    WHERE id = %s
                    """,
                    [
                        name,
                        asset_class.value,
                        data_shape.value,
                        lseg_ric,
                        instrument_id,
                    ],
                )
            else:
                # Insert new and get ID using RETURNING
                cur.execute(
                    """
                    INSERT INTO instruments (symbol, name, asset_class, data_shape, lseg_ric, updated_at)
                    VALUES (%s, %s, %s, %s, %s, current_timestamp)
                    RETURNING id
                    """,
                    [
                        symbol,
                        name,
                        asset_class.value,
                        data_shape.value,
                        lseg_ric,
                    ],
                )
                instrument_id = cur.fetchone()["id"]

        # Save type-specific details using unified function
        if kwargs:
            _upsert_instrument_details(conn, instrument_id, asset_class.value, **kwargs)

        return instrument_id
    except psycopg.Error as e:
        raise StorageError(f"Failed to save instrument {symbol}: {e}") from e


def get_instrument(conn: psycopg.Connection, symbol: str) -> dict | None:
    """
    Get instrument by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument dict or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM instruments WHERE symbol = %s", [symbol])
        result = cur.fetchone()
        return dict(result) if result else None


def get_instrument_id(conn: psycopg.Connection, symbol: str) -> int | None:
    """
    Get instrument ID by symbol.

    Args:
        conn: Database connection.
        symbol: Instrument symbol.

    Returns:
        Instrument ID or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM instruments WHERE symbol = %s", [symbol])
        result = cur.fetchone()
    return result["id"] if result else None


def get_instrument_by_ric(conn: psycopg.Connection, lseg_ric: str) -> dict | None:
    """
    Get instrument by LSEG RIC.

    Args:
        conn: Database connection.
        lseg_ric: LSEG RIC code.

    Returns:
        Instrument dict or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM instruments WHERE lseg_ric = %s", [lseg_ric])
        result = cur.fetchone()
        return dict(result) if result else None


def get_instruments(
    conn: psycopg.Connection, asset_class: AssetClass | None = None
) -> list[dict]:
    """
    Get all instruments, optionally filtered by asset class.

    Args:
        conn: Database connection.
        asset_class: Optional asset class filter.

    Returns:
        List of instrument dicts.
    """
    with conn.cursor() as cur:
        if asset_class:
            cur.execute(
                "SELECT * FROM instruments WHERE asset_class = %s ORDER BY symbol",
                [asset_class.value],
            )
        else:
            cur.execute("SELECT * FROM instruments ORDER BY symbol")

        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
