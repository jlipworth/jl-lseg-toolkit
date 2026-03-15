"""
Instrument universe builders.

Maps instrument group names to lists of InstrumentSpec from constants.py.
"""

from __future__ import annotations

from lseg_toolkit.timeseries.constants import (
    ASIAN_BOND_FUTURES_MAPPING,
    BENCHMARK_FIXINGS,
    COMMODITY_FUTURES_MAPPING,
    EQUITY_INDEX_RICS,
    EUR_FRA_TENORS,
    EUR_IRS_TENORS,
    EURIBOR_RICS,
    EUROPEAN_FUTURES_MAPPING,
    FX_FUTURES_MAPPING,
    FX_SPOT_RICS,
    G7_OIS_CURRENCIES,
    G7_OIS_TENORS,
    GBP_FRA_TENORS,
    GBP_IRS_TENORS,
    GBP_OIS_TENORS,
    INDEX_FUTURES_MAPPING,
    SOVEREIGN_YIELD_RICS,
    STIR_FUTURES_RICS,
    TREASURY_FUTURES_MAPPING,
    USD_FRA_TENORS,
    USD_IRS_TENORS,
    USD_OIS_TENORS,
    USD_REPO_RICS,
    VOLATILITY_INDEX_RICS,
    get_eur_irs_ric,
    get_fra_ric,
    get_g7_ois_ric,
    get_gbp_irs_ric,
    get_gbp_ois_ric,
    get_ois_ric,
    get_usd_irs_ric,
)
from lseg_toolkit.timeseries.enums import AssetClass, DataShape
from lseg_toolkit.timeseries.fed_funds import get_ff_continuous_symbol
from lseg_toolkit.timeseries.scheduler.models import InstrumentSpec
from lseg_toolkit.timeseries.stir_futures import get_continuous_ric


def build_universe(group: str) -> list[InstrumentSpec]:
    """
    Build instrument universe for a given group.

    Args:
        group: Instrument group name (e.g., 'treasury_futures', 'fx_spot')

    Returns:
        List of InstrumentSpec objects for the group.

    Raises:
        ValueError: If group is unknown.
    """
    builders = {
        # Futures
        "treasury_futures": _build_treasury_futures,
        "european_bond_futures": _build_european_bond_futures,
        "asian_bond_futures": _build_asian_bond_futures,
        "index_futures": _build_index_futures,
        "fx_futures": _build_fx_futures,
        "commodity_futures": _build_commodity_futures,
        "stir_futures": _build_stir_futures,
        "stir_ff": _build_stir_ff,
        # FX
        "fx_spot": _build_fx_spot,
        # Rates - OIS
        "ois_usd": _build_ois_usd,
        "ois_eur": _build_ois_eur,
        "ois_gbp": _build_ois_gbp,
        "ois_g7": _build_ois_g7,
        # Rates - IRS
        "irs_usd": _build_irs_usd,
        "irs_eur": _build_irs_eur,
        "irs_gbp": _build_irs_gbp,
        # Rates - FRA
        "fra_usd": _build_fra_usd,
        "fra_eur": _build_fra_eur,
        "fra_gbp": _build_fra_gbp,
        # Rates - Repo
        "repo_usd": _build_repo_usd,
        # Government Yields
        "ust_yields": _build_ust_yields,
        "de_yields": _build_de_yields,
        "gb_yields": _build_gb_yields,
        "sovereign_g7": _build_sovereign_g7,
        # Equity Indices
        "equity_indices": _build_equity_indices,
        "volatility_indices": _build_volatility_indices,
        # Fixings
        "benchmark_fixings": _build_benchmark_fixings,
        "euribor_fixings": _build_euribor_fixings,
    }

    builder = builders.get(group)
    if builder is None:
        available = ", ".join(sorted(builders.keys()))
        raise ValueError(f"Unknown instrument group: {group}. Available: {available}")

    return builder()


def get_available_groups() -> list[str]:
    """Get list of all available instrument groups."""
    return [
        "treasury_futures",
        "european_bond_futures",
        "asian_bond_futures",
        "index_futures",
        "fx_futures",
        "commodity_futures",
        "stir_futures",
        "stir_ff",
        "fx_spot",
        "ois_usd",
        "ois_eur",
        "ois_gbp",
        "ois_g7",
        "irs_usd",
        "irs_eur",
        "irs_gbp",
        "fra_usd",
        "fra_eur",
        "fra_gbp",
        "repo_usd",
        "ust_yields",
        "de_yields",
        "gb_yields",
        "sovereign_g7",
        "equity_indices",
        "volatility_indices",
        "benchmark_fixings",
        "euribor_fixings",
    ]


# =============================================================================
# Futures Builders
# =============================================================================


def _build_treasury_futures() -> list[InstrumentSpec]:
    """Build US Treasury futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.BOND_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} Treasury Future",
        )
        for cme, lseg in TREASURY_FUTURES_MAPPING.items()
    ]


def _build_european_bond_futures() -> list[InstrumentSpec]:
    """Build European bond futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.BOND_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} European Bond Future",
        )
        for cme, lseg in EUROPEAN_FUTURES_MAPPING.items()
    ]


def _build_asian_bond_futures() -> list[InstrumentSpec]:
    """Build Asian bond futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.BOND_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} Asian Bond Future",
        )
        for cme, lseg in ASIAN_BOND_FUTURES_MAPPING.items()
    ]


def _build_index_futures() -> list[InstrumentSpec]:
    """Build equity index futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.INDEX_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} Index Future",
        )
        for cme, lseg in INDEX_FUTURES_MAPPING.items()
    ]


def _build_fx_futures() -> list[InstrumentSpec]:
    """Build FX futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.FX_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} FX Future",
        )
        for cme, lseg in FX_FUTURES_MAPPING.items()
    ]


def _build_commodity_futures() -> list[InstrumentSpec]:
    """Build commodity futures universe."""
    return [
        InstrumentSpec(
            symbol=cme,
            ric=f"{lseg}c1",
            asset_class=AssetClass.COMMODITY_FUTURES,
            data_shape=DataShape.OHLCV,
            name=f"{cme} Commodity Future",
        )
        for cme, lseg in COMMODITY_FUTURES_MAPPING.items()
    ]


def _build_stir_futures() -> list[InstrumentSpec]:
    """Build STIR futures universe."""
    specs = []
    # Only include continuous contracts (not chains)
    for name, ric in STIR_FUTURES_RICS.items():
        if "CHAIN" not in name and ric.endswith("c1"):
            specs.append(
                InstrumentSpec(
                    symbol=name,
                    ric=ric,
                    asset_class=AssetClass.STIR_FUTURES,
                    data_shape=DataShape.OHLCV,
                    name=f"{name} STIR Future",
                )
            )
    return specs


def _build_stir_ff() -> list[InstrumentSpec]:
    """Build FF-only STIR universe for scheduler jobs."""
    return [
        InstrumentSpec(
            symbol=get_ff_continuous_symbol(rank),
            ric=get_continuous_ric("FF", month=rank),
            asset_class=AssetClass.STIR_FUTURES,
            data_shape=DataShape.OHLCV,
            name=(
                "30-Day Fed Funds Continuous"
                if rank == 1
                else f"30-Day Fed Funds Continuous Rank {rank}"
            ),
        )
        for rank in range(1, 13)
    ]


# =============================================================================
# FX Spot Builder
# =============================================================================


def _build_fx_spot() -> list[InstrumentSpec]:
    """Build FX spot universe."""
    return [
        InstrumentSpec(
            symbol=pair,
            ric=ric,
            asset_class=AssetClass.FX_SPOT,
            data_shape=DataShape.QUOTE,
            name=f"{pair} Spot",
        )
        for pair, ric in FX_SPOT_RICS.items()
    ]


# =============================================================================
# OIS Builders
# =============================================================================


def _build_ois_usd() -> list[InstrumentSpec]:
    """Build USD OIS universe."""
    return [
        InstrumentSpec(
            symbol=f"USD{tenor}OIS",
            ric=get_ois_ric("USD", tenor),
            asset_class=AssetClass.OIS,
            data_shape=DataShape.RATE,
            name=f"USD OIS {tenor}",
        )
        for tenor in USD_OIS_TENORS
    ]


def _build_ois_eur() -> list[InstrumentSpec]:
    """Build EUR OIS universe (same tenors as USD)."""
    return [
        InstrumentSpec(
            symbol=f"EUR{tenor}OIS",
            ric=get_ois_ric("EUR", tenor),
            asset_class=AssetClass.OIS,
            data_shape=DataShape.RATE,
            name=f"EUR OIS {tenor}",
        )
        for tenor in USD_OIS_TENORS  # EUR uses same tenors
    ]


def _build_ois_gbp() -> list[InstrumentSpec]:
    """Build GBP OIS universe."""
    return [
        InstrumentSpec(
            symbol=f"GBP{tenor}OIS",
            ric=get_gbp_ois_ric(tenor),
            asset_class=AssetClass.OIS,
            data_shape=DataShape.RATE,
            name=f"GBP OIS {tenor}",
        )
        for tenor in GBP_OIS_TENORS
    ]


def _build_ois_g7() -> list[InstrumentSpec]:
    """Build G7 OIS universe (all major currencies)."""
    specs = []
    for ccy in G7_OIS_CURRENCIES:
        for tenor in G7_OIS_TENORS:
            specs.append(
                InstrumentSpec(
                    symbol=f"{ccy}{tenor}OIS",
                    ric=get_g7_ois_ric(ccy, tenor),
                    asset_class=AssetClass.OIS,
                    data_shape=DataShape.RATE,
                    name=f"{ccy} OIS {tenor}",
                )
            )
    return specs


# =============================================================================
# IRS Builders
# =============================================================================


def _build_irs_usd() -> list[InstrumentSpec]:
    """Build USD IRS universe."""
    return [
        InstrumentSpec(
            symbol=f"USDIRS{tenor}",
            ric=get_usd_irs_ric(tenor),
            asset_class=AssetClass.IRS,
            data_shape=DataShape.RATE,
            name=f"USD IRS {tenor}",
        )
        for tenor in USD_IRS_TENORS
    ]


def _build_irs_eur() -> list[InstrumentSpec]:
    """Build EUR IRS universe."""
    return [
        InstrumentSpec(
            symbol=f"EURIRS{tenor}",
            ric=get_eur_irs_ric(tenor),
            asset_class=AssetClass.IRS,
            data_shape=DataShape.RATE,
            name=f"EUR IRS {tenor}",
        )
        for tenor in EUR_IRS_TENORS
    ]


def _build_irs_gbp() -> list[InstrumentSpec]:
    """Build GBP IRS universe."""
    return [
        InstrumentSpec(
            symbol=f"GBPIRS{tenor}",
            ric=get_gbp_irs_ric(tenor),
            asset_class=AssetClass.IRS,
            data_shape=DataShape.RATE,
            name=f"GBP IRS {tenor}",
        )
        for tenor in GBP_IRS_TENORS
    ]


# =============================================================================
# FRA Builders
# =============================================================================


def _build_fra_usd() -> list[InstrumentSpec]:
    """Build USD FRA universe."""
    return [
        InstrumentSpec(
            symbol=f"USD{tenor}FRA",
            ric=get_fra_ric("USD", tenor),
            asset_class=AssetClass.FRA,
            data_shape=DataShape.RATE,
            name=f"USD FRA {tenor}",
        )
        for tenor in USD_FRA_TENORS
    ]


def _build_fra_eur() -> list[InstrumentSpec]:
    """Build EUR FRA universe."""
    return [
        InstrumentSpec(
            symbol=f"EUR{tenor}FRA",
            ric=get_fra_ric("EUR", tenor),
            asset_class=AssetClass.FRA,
            data_shape=DataShape.RATE,
            name=f"EUR FRA {tenor}",
        )
        for tenor in EUR_FRA_TENORS
    ]


def _build_fra_gbp() -> list[InstrumentSpec]:
    """Build GBP FRA universe."""
    return [
        InstrumentSpec(
            symbol=f"GBP{tenor}FRA",
            ric=get_fra_ric("GBP", tenor),
            asset_class=AssetClass.FRA,
            data_shape=DataShape.RATE,
            name=f"GBP FRA {tenor}",
        )
        for tenor in GBP_FRA_TENORS
    ]


# =============================================================================
# Repo Builder
# =============================================================================


def _build_repo_usd() -> list[InstrumentSpec]:
    """Build USD repo universe."""
    return [
        InstrumentSpec(
            symbol=f"USREPO{tenor}",
            ric=ric,
            asset_class=AssetClass.REPO,
            data_shape=DataShape.RATE,
            name=f"USD Repo {tenor}",
        )
        for tenor, ric in USD_REPO_RICS.items()
    ]


# =============================================================================
# Government Yield Builders
# =============================================================================


def _build_ust_yields() -> list[InstrumentSpec]:
    """Build US Treasury yield universe."""
    return [
        InstrumentSpec(
            symbol=f"UST{tenor}",
            ric=ric,
            asset_class=AssetClass.GOVT_YIELD,
            data_shape=DataShape.BOND,
            name=f"US Treasury {tenor}",
        )
        for tenor, ric in SOVEREIGN_YIELD_RICS["US"].items()
    ]


def _build_de_yields() -> list[InstrumentSpec]:
    """Build German Bund yield universe."""
    return [
        InstrumentSpec(
            symbol=f"DE{tenor}",
            ric=ric,
            asset_class=AssetClass.GOVT_YIELD,
            data_shape=DataShape.BOND,
            name=f"German Bund {tenor}",
        )
        for tenor, ric in SOVEREIGN_YIELD_RICS["DE"].items()
    ]


def _build_gb_yields() -> list[InstrumentSpec]:
    """Build UK Gilt yield universe."""
    return [
        InstrumentSpec(
            symbol=f"GB{tenor}",
            ric=ric,
            asset_class=AssetClass.GOVT_YIELD,
            data_shape=DataShape.BOND,
            name=f"UK Gilt {tenor}",
        )
        for tenor, ric in SOVEREIGN_YIELD_RICS["GB"].items()
    ]


def _build_sovereign_g7() -> list[InstrumentSpec]:
    """Build G7 sovereign yield universe."""
    specs = []
    # Core G7 countries with available data
    countries = ["US", "DE", "GB", "FR", "IT", "CA", "AU", "CH"]
    for country in countries:
        if country in SOVEREIGN_YIELD_RICS:
            for tenor, ric in SOVEREIGN_YIELD_RICS[country].items():
                specs.append(
                    InstrumentSpec(
                        symbol=f"{country}{tenor}",
                        ric=ric,
                        asset_class=AssetClass.GOVT_YIELD,
                        data_shape=DataShape.BOND,
                        name=f"{country} Govt {tenor}",
                    )
                )
    return specs


# =============================================================================
# Equity Index Builders
# =============================================================================


def _build_equity_indices() -> list[InstrumentSpec]:
    """Build equity index universe."""
    return [
        InstrumentSpec(
            symbol=name,
            ric=ric,
            asset_class=AssetClass.EQUITY_INDEX,
            data_shape=DataShape.OHLCV,
            name=f"{name} Index",
        )
        for name, ric in EQUITY_INDEX_RICS.items()
    ]


def _build_volatility_indices() -> list[InstrumentSpec]:
    """Build volatility index universe."""
    return [
        InstrumentSpec(
            symbol=name,
            ric=ric,
            asset_class=AssetClass.EQUITY_INDEX,
            data_shape=DataShape.OHLCV,
            name=f"{name} Volatility",
        )
        for name, ric in VOLATILITY_INDEX_RICS.items()
    ]


# =============================================================================
# Fixing Builders
# =============================================================================


def _build_benchmark_fixings() -> list[InstrumentSpec]:
    """Build benchmark fixing universe (SOFR, ESTR, etc.)."""
    return [
        InstrumentSpec(
            symbol=name,
            ric=ric,
            asset_class=AssetClass.FIXING,
            data_shape=DataShape.FIXING,
            name=f"{name} Fixing",
        )
        for name, ric in BENCHMARK_FIXINGS.items()
    ]


def _build_euribor_fixings() -> list[InstrumentSpec]:
    """Build EURIBOR fixing universe."""
    return [
        InstrumentSpec(
            symbol=f"EURIBOR{tenor}",
            ric=ric,
            asset_class=AssetClass.FIXING,
            data_shape=DataShape.FIXING,
            name=f"EURIBOR {tenor} Fixing",
        )
        for tenor, ric in EURIBOR_RICS.items()
    ]
