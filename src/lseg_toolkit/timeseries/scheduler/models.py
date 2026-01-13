"""
Scheduler data models.

Pydantic models for job definitions, instrument specifications, and results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from lseg_toolkit.timeseries.enums import AssetClass, DataShape, Granularity


class InstrumentGroup(str, Enum):
    """Predefined instrument groups from constants.py."""

    # Futures - Bond
    TREASURY_FUTURES = "treasury_futures"
    EUROPEAN_BOND_FUTURES = "european_bond_futures"
    ASIAN_BOND_FUTURES = "asian_bond_futures"

    # Futures - Equity Index
    INDEX_FUTURES = "index_futures"

    # Futures - FX
    FX_FUTURES = "fx_futures"

    # Futures - Commodity
    COMMODITY_FUTURES = "commodity_futures"

    # Futures - STIR
    STIR_FUTURES = "stir_futures"

    # FX Spot
    FX_SPOT = "fx_spot"

    # Rates - OIS
    OIS_USD = "ois_usd"
    OIS_EUR = "ois_eur"
    OIS_GBP = "ois_gbp"
    OIS_G7 = "ois_g7"

    # Rates - IRS
    IRS_USD = "irs_usd"
    IRS_EUR = "irs_eur"
    IRS_GBP = "irs_gbp"

    # Rates - FRA
    FRA_USD = "fra_usd"
    FRA_EUR = "fra_eur"
    FRA_GBP = "fra_gbp"

    # Rates - Repo
    REPO_USD = "repo_usd"

    # Government Yields
    UST_YIELDS = "ust_yields"
    DE_YIELDS = "de_yields"
    GB_YIELDS = "gb_yields"
    SOVEREIGN_G7 = "sovereign_g7"

    # Equity Indices (Spot)
    EQUITY_INDICES = "equity_indices"
    VOLATILITY_INDICES = "volatility_indices"

    # Fixings
    BENCHMARK_FIXINGS = "benchmark_fixings"
    EURIBOR_FIXINGS = "euribor_fixings"


class JobSchedule(BaseModel):
    """Schedule definition for an extraction job."""

    cron: str = Field(..., description="Cron expression (e.g., '0 18 * * 1-5')")
    timezone: str = Field(default="America/New_York", description="Timezone for cron")


class JobDefinition(BaseModel):
    """Definition of an extraction job."""

    name: str = Field(..., description="Unique job name")
    description: str | None = Field(default=None, description="Job description")
    instrument_group: str = Field(..., description="Instrument group to extract")
    granularity: Granularity = Field(
        default=Granularity.DAILY, description="Data granularity"
    )
    schedule: JobSchedule = Field(..., description="Cron schedule")
    priority: int = Field(
        default=50, ge=1, le=100, description="Job priority (1=highest)"
    )
    enabled: bool = Field(default=True, description="Whether job is active")
    lookback_days: int = Field(
        default=5, ge=1, description="Days to look back for gaps"
    )
    max_chunk_days: int = Field(
        default=30, ge=1, description="Max days per extraction chunk"
    )

    model_config = {"use_enum_values": True}  # Serialize enum as string value


@dataclass
class InstrumentSpec:
    """Specification for an instrument to extract."""

    symbol: str
    ric: str
    asset_class: AssetClass
    data_shape: DataShape
    name: str | None = None


@dataclass
class ExtractionResult:
    """Result of extracting data for a single instrument."""

    instrument_id: int
    symbol: str
    success: bool
    rows_extracted: int = 0
    start_date: date | None = None
    end_date: date | None = None
    error: str | None = None


@dataclass
class JobRunResult:
    """Result of a complete job run."""

    job_id: int
    run_id: int
    status: str  # 'completed', 'failed', 'partial'
    instruments_total: int
    instruments_success: int
    instruments_failed: int
    rows_extracted: int
    errors: list[str]
