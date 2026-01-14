"""
STIR futures contract generation and discovery.

Generates RIC patterns for historical STIR futures contracts.
Fed Funds (FF) is monthly. SOFR, Euribor, SONIA are quarterly (H, M, U, Z).
"""

from datetime import date
from typing import Literal

from lseg_toolkit.timeseries.constants import (
    FUTURES_MONTH_CODES,
    FUTURES_MONTH_TO_INT,
    QUARTERLY_MONTH_CODES,
    STIR_FUTURES_RICS,
)

# Product type for type hints
StirProduct = Literal["FF", "SRA", "FEI", "SON"]

# Contract specifications (extends constants.py with metadata)
STIR_CONTRACT_SPECS: dict[str, dict] = {
    "FF": {
        "name": "30-Day Fed Funds",
        "exchange": "CME",
        "cme_symbol": "ZQ",
        "months": "monthly",
        "first_year": 1988,
    },
    "SRA": {
        "name": "3-Month SOFR",
        "exchange": "CME",
        "cme_symbol": "SR3",
        "months": "quarterly",
        "first_year": 2018,
    },
    "FEI": {
        "name": "3-Month Euribor",
        "exchange": "EUREX",
        "cme_symbol": None,
        "months": "quarterly",
        "first_year": 1999,
    },
    "SON": {
        "name": "3-Month SONIA",
        "exchange": "ICE",
        "cme_symbol": None,
        "months": "quarterly",
        "first_year": 2018,
    },
}


def generate_contract_rics(
    product: StirProduct,
    start_year: int,
    end_year: int,
) -> list[str]:
    """
    Generate LSEG RICs for historical contracts.

    Args:
        product: One of FF, SRA, FEI, SON
        start_year: First year (e.g., 2020)
        end_year: Last year (e.g., 2025)

    Returns:
        List of RICs like ['FFZ20', 'FFF21', 'FFG21', ...]

    Example:
        >>> generate_contract_rics("FF", 2023, 2024)
        ['FFF23', 'FFG23', ..., 'FFZ23', 'FFF24', ..., 'FFZ24']
    """
    spec = STIR_CONTRACT_SPECS.get(product)
    if not spec:
        raise ValueError(
            f"Unknown product: {product}. Use one of {list(STIR_CONTRACT_SPECS.keys())}"
        )

    months = (
        QUARTERLY_MONTH_CODES if spec["months"] == "quarterly" else FUTURES_MONTH_CODES
    )

    rics = []
    for year in range(start_year, end_year + 1):
        year_suffix = str(year)[-2:]
        for month_code in months:
            rics.append(f"{product}{month_code}{year_suffix}")

    return rics


def get_contract_expiry_month(ric: str) -> tuple[int, int] | None:
    """
    Extract year and month from a contract RIC.

    Args:
        ric: Contract RIC like 'FFZ24' or 'SRAH25'

    Returns:
        (year, month) tuple or None if unparseable

    Example:
        >>> get_contract_expiry_month("FFZ24")
        (2024, 12)
        >>> get_contract_expiry_month("SRAH25")
        (2025, 3)
    """
    import re

    # Pattern: product prefix + month code + 2-digit year
    # e.g., FFZ24, SRAH25, FEIM24
    match = re.search(r"([FGHJKMNQUVXZ])(\d{2})$", ric)
    if match:
        month_code = match.group(1)
        year_suffix = int(match.group(2))
        month = FUTURES_MONTH_TO_INT[month_code]
        year = 2000 + year_suffix
        return (year, month)
    return None


def get_active_contracts(
    product: StirProduct,
    as_of: date | None = None,
    num_contracts: int = 12,
) -> list[str]:
    """
    Get the N front-month contracts as of a given date.

    Args:
        product: Product code
        as_of: Reference date (default: today)
        num_contracts: Number of contracts to return

    Returns:
        List of RICs for front N contracts
    """
    if as_of is None:
        as_of = date.today()

    spec = STIR_CONTRACT_SPECS[product]
    is_quarterly = spec["months"] == "quarterly"

    contracts: list[str] = []
    year = as_of.year
    month = as_of.month

    while len(contracts) < num_contracts:
        if is_quarterly:
            quarterly_months = [3, 6, 9, 12]
            for qm in quarterly_months:
                if qm >= month:
                    month = qm
                    break
            else:
                year += 1
                month = 3

        month_code = FUTURES_MONTH_CODES[month - 1]
        year_suffix = str(year)[-2:]
        contracts.append(f"{product}{month_code}{year_suffix}")

        if is_quarterly:
            month += 3
            if month > 12:
                month = 3
                year += 1
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1

    return contracts


def get_chain_ric(product: StirProduct) -> str:
    """Get the chain RIC for discovering all contracts."""
    # Use existing constants where available
    chain_key = {
        "FF": "FF_CHAIN",
        "SRA": "SOFR_3M_CHAIN",
        "FEI": "EURIBOR_CHAIN",
    }.get(product)

    if chain_key and chain_key in STIR_FUTURES_RICS:
        return STIR_FUTURES_RICS[chain_key]

    return f"0#{product}:"


def get_continuous_ric(product: StirProduct, month: int = 1) -> str:
    """Get continuous contract RIC (e.g., FFc1, SRAc2)."""
    return f"{product}c{month}"
