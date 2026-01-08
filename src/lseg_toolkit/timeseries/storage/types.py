"""
Type definitions for storage module.

This module provides TypedDict definitions for type-safe instrument details,
enabling IDE autocomplete and static type checking for save_instrument() kwargs.
"""

from __future__ import annotations

from datetime import date
from typing import TypedDict


class FuturesDetails(TypedDict, total=False):
    """Details for futures contracts."""

    underlying: str
    exchange: str | None
    expiry_date: date | None
    contract_month: str | None
    continuous_type: str
    tick_size: float | None
    point_value: float | None


class FXDetails(TypedDict, total=False):
    """Details for FX spot and forward instruments."""

    base_currency: str
    quote_currency: str
    pip_size: float
    tenor: str | None


class RateDetails(TypedDict, total=False):
    """Details for rate instruments (OIS, IRS, FRA, repo, deposits)."""

    rate_type: str
    currency: str
    tenor: str
    reference_rate: str | None
    day_count: str | None
    payment_frequency: str | None
    business_day_conv: str | None
    calendar: str | None
    settlement_days: int
    paired_instrument_id: int | None


class BondDetails(TypedDict, total=False):
    """Details for bond instruments (govt yields, corp bonds)."""

    issuer_type: str
    country: str | None
    tenor: str
    coupon_rate: float | None
    coupon_frequency: str | None
    day_count: str | None
    maturity_date: date | None
    settlement_days: int
    credit_rating: str | None
    sector: str | None


class FixingDetails(TypedDict, total=False):
    """Details for fixing instruments (SOFR, ESTR, SONIA, EURIBOR)."""

    rate_name: str
    tenor: str | None
    fixing_time: str | None
    administrator: str | None


class EquityDetails(TypedDict, total=False):
    """Details for equity instruments."""

    exchange: str | None
    country: str
    currency: str
    sector: str | None
    industry: str | None
    isin: str | None
    cusip: str | None
    sedol: str | None
    market_cap_category: str | None


class ETFDetails(TypedDict, total=False):
    """Details for ETF instruments."""

    exchange: str | None
    country: str
    currency: str
    asset_class_focus: str | None
    geography_focus: str | None
    benchmark_index: str | None
    expense_ratio: float | None
    isin: str | None
    cusip: str | None
    is_leveraged: bool
    is_inverse: bool


class IndexDetails(TypedDict, total=False):
    """Details for equity index instruments."""

    index_family: str | None
    country: str | None
    calculation_method: str | None
    currency: str
    num_constituents: int | None
    base_date: date | None
    base_value: float | None


# Union type for any instrument details
InstrumentDetails = (
    FuturesDetails
    | FXDetails
    | RateDetails
    | BondDetails
    | FixingDetails
    | EquityDetails
    | ETFDetails
    | IndexDetails
)
