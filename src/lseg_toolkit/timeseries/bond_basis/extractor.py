"""
Bond basis data extractor.

Extracts prerequisite data for bond basis analysis:
- Futures prices (continuous and discrete contracts)
- Deliverable bond prices (via CUSIP RICs)
- Repo rates
- Stores in TimescaleDB for downstream processing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import lseg.data as rd
import pandas as pd

if TYPE_CHECKING:
    import psycopg

logger = logging.getLogger(__name__)


# Treasury futures mapping: LSEG root -> CME symbol
TREASURY_FUTURES = {
    "TU": {"cme": "ZT", "name": "2-Year T-Note", "deliverable_chain": "0#TUc1=DLV"},
    "FV": {"cme": "ZF", "name": "5-Year T-Note", "deliverable_chain": "0#FVc1=DLV"},
    "TY": {"cme": "ZN", "name": "10-Year T-Note", "deliverable_chain": "0#TYc1=DLV"},
    "TN": {"cme": "TN", "name": "Ultra 10-Year", "deliverable_chain": "0#TNc1=DLV"},
    "US": {"cme": "ZB", "name": "T-Bond", "deliverable_chain": "0#USc1=DLV"},
    "UB": {"cme": "UB", "name": "Ultra T-Bond", "deliverable_chain": "0#UBc1=DLV"},
}

# Quarterly contract months for treasuries
CONTRACT_MONTHS = ["H", "M", "U", "Z"]  # Mar, Jun, Sep, Dec

# Month code to calendar month mapping
MONTH_CODE_MAP = {"H": 3, "M": 6, "U": 9, "Z": 12}


@dataclass
class ExtractionResult:
    """Result of a data extraction run."""

    futures_rows: int = 0
    bond_rows: int = 0
    repo_rows: int = 0
    errors: list[str] | None = None


class BondBasisExtractor:
    """
    Extracts bond basis prerequisite data from LSEG.

    Usage:
        extractor = BondBasisExtractor(conn)
        result = extractor.extract_futures("TY", start_date, end_date)
    """

    def __init__(self, conn: psycopg.Connection):
        """
        Initialize extractor.

        Args:
            conn: PostgreSQL/TimescaleDB connection.
        """
        self.conn = conn

    def get_continuous_futures_history(
        self,
        root: str,
        start_date: date,
        end_date: date,
        granularity: str = "daily",
    ) -> pd.DataFrame:
        """
        Get historical prices for continuous front-month contract.

        Args:
            root: LSEG futures root (e.g., 'TY' for 10Y T-Note).
            start_date: Start date.
            end_date: End date.
            granularity: 'daily', 'hourly', etc.

        Returns:
            DataFrame with OHLCV data.
        """
        ric = f"{root}c1"
        logger.info(f"Fetching {ric} from {start_date} to {end_date}")

        interval = "daily" if granularity == "daily" else granularity

        df = rd.get_history(
            ric,
            fields=[
                "OPEN_PRC",
                "HIGH_1",
                "LOW_1",
                "TRDPRC_1",
                "SETTLE",
                "ACVOL_1",
                "OPINT_1",
            ],
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=interval,
        )

        if df is not None and len(df) > 0:
            logger.info(f"Got {len(df)} rows for {ric}")
        else:
            logger.warning(f"No data for {ric}")

        return df if df is not None else pd.DataFrame()

    def get_discrete_contract_history(
        self,
        root: str,
        month_code: str,
        year: int,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Get historical prices for a specific futures contract.

        For expired contracts (pre-2024), uses decade suffix format:
        e.g., TYH3^2 for March 2023

        Args:
            root: LSEG futures root (e.g., 'TY').
            month_code: Contract month (H, M, U, Z).
            year: Full year (e.g., 2023).
            start_date: Start date.
            end_date: End date.

        Returns:
            DataFrame with OHLCV data.
        """
        # Build RIC based on year
        year_digit = year % 10
        current_year = date.today().year

        if year < 2020:
            # 2010s decade: ^1
            ric = f"{root}{month_code}{year_digit}^1"
        elif year < 2024:
            # 2020s decade, expired: ^2
            ric = f"{root}{month_code}{year_digit}^2"
        elif year == current_year - 1:
            # Last year, may or may not need caret
            # Try without first
            ric = f"{root}{month_code}{year_digit}"
        else:
            # Current/future: just the digit
            ric = f"{root}{month_code}{year_digit}"

        logger.info(f"Fetching discrete contract {ric}")

        try:
            df = rd.get_history(
                ric,
                fields=["OPEN_PRC", "HIGH_1", "LOW_1", "SETTLE", "ACVOL_1", "OPINT_1"],
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                interval="daily",
            )
            if df is not None and len(df) > 0:
                logger.info(f"Got {len(df)} rows for {ric}")
                return df
        except Exception as e:
            logger.warning(f"Failed to get {ric}: {e}")

        # If that failed for recent years, try with caret
        if year >= 2020:
            ric_caret = f"{root}{month_code}{year_digit}^2"
            if ric_caret != ric:
                logger.info(f"Retrying with {ric_caret}")
                try:
                    df = rd.get_history(
                        ric_caret,
                        fields=[
                            "OPEN_PRC",
                            "HIGH_1",
                            "LOW_1",
                            "SETTLE",
                            "ACVOL_1",
                            "OPINT_1",
                        ],
                        start=start_date.isoformat(),
                        end=end_date.isoformat(),
                        interval="daily",
                    )
                    if df is not None and len(df) > 0:
                        logger.info(f"Got {len(df)} rows for {ric_caret}")
                        return df
                except Exception as e:
                    logger.warning(f"Failed to get {ric_caret}: {e}")

        return pd.DataFrame()

    def get_current_deliverable_basket(self, root: str) -> list[dict]:
        """
        Get current deliverable bonds for a futures contract.

        Note: Historical deliverable baskets are not available via API.
        This returns the CURRENT basket only.

        Args:
            root: LSEG futures root (e.g., 'TY').

        Returns:
            List of bond info dicts with cusip, coupon, maturity, ric.
        """
        chain_ric = TREASURY_FUTURES.get(root, {}).get("deliverable_chain")
        if not chain_ric:
            logger.error(f"Unknown futures root: {root}")
            return []

        logger.info(f"Fetching deliverable basket from {chain_ric}")

        try:
            df = rd.get_data(
                chain_ric,
                fields=[
                    "DSPLY_NAME",
                    "CF_CLOSE",
                    "COUPN_DATE",
                    "MATUR_DATE",
                    "COUPN_RATE",
                ],
            )

            if df is None or len(df) == 0:
                logger.warning(f"No deliverable bonds found for {root}")
                return []

            bonds = []
            for _, row in df.iterrows():
                ric = row.get("Instrument", "")
                # Extract CUSIP from RIC (e.g., '91282CFV8=' -> '91282CFV8')
                cusip = ric.replace("=", "") if "=" in ric else ric

                bonds.append(
                    {
                        "ric": ric,
                        "cusip": cusip,
                        "name": row.get("DSPLY_NAME", ""),
                        "price": row.get("CF_CLOSE"),
                        "coupon_rate": row.get("COUPN_RATE"),
                        "maturity_date": row.get("MATUR_DATE"),
                    }
                )

            logger.info(f"Found {len(bonds)} deliverable bonds for {root}")
            return bonds

        except Exception as e:
            logger.error(f"Failed to get deliverable basket: {e}")
            return []

    def get_bond_price_history(
        self,
        cusip_or_ric: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Get historical prices for a bond via CUSIP or RIC.

        Args:
            cusip_or_ric: Bond CUSIP (e.g., '91282CFV8') or RIC ('91282CFV8=').
            start_date: Start date.
            end_date: End date.

        Returns:
            DataFrame with price history.
        """
        # Ensure RIC format
        ric = cusip_or_ric if "=" in cusip_or_ric else f"{cusip_or_ric}="

        logger.info(f"Fetching bond prices for {ric}")

        try:
            df = rd.get_history(
                ric,
                fields=["BID", "ASK", "MID_YLD_1", "ACCR_INT", "MOD_DURTN"],
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                interval="daily",
            )

            if df is not None and len(df) > 0:
                logger.info(f"Got {len(df)} rows for {ric}")
                return df

        except Exception as e:
            logger.warning(f"Failed to get bond prices for {ric}: {e}")

        return pd.DataFrame()

    def get_repo_rate_history(
        self,
        start_date: date,
        end_date: date,
        tenor: str = "ON",
    ) -> pd.DataFrame:
        """
        Get historical repo rates.

        Args:
            start_date: Start date.
            end_date: End date.
            tenor: 'ON' (overnight), '1W', '1M', '2M', '3M'.

        Returns:
            DataFrame with repo rate history.
        """
        repo_rics = {
            "ON": "USONRP=",
            "1W": "US1WRP=",
            "1M": "US1MRP=",
            "2M": "US2MRP=",
            "3M": "US3MRP=",
            "SOFR": "USDSOFR=",
        }

        ric = repo_rics.get(tenor)
        if not ric:
            logger.error(f"Unknown repo tenor: {tenor}")
            return pd.DataFrame()

        logger.info(f"Fetching repo rates for {tenor} ({ric})")

        try:
            df = rd.get_history(
                ric,
                fields=["BID", "ASK", "MID_PRICE"],
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                interval="daily",
            )

            if df is not None and len(df) > 0:
                logger.info(f"Got {len(df)} rows for {ric}")
                return df

        except Exception as e:
            logger.warning(f"Failed to get repo rates: {e}")

        return pd.DataFrame()

    def extract_all(
        self,
        root: str,
        start_date: date,
        end_date: date,
    ) -> ExtractionResult:
        """
        Extract all bond basis prerequisites for a futures root.

        This extracts:
        1. Continuous futures prices
        2. Current deliverable basket bonds
        3. Bond price history for each deliverable
        4. Repo rates (ON and term)

        Args:
            root: LSEG futures root (e.g., 'TY').
            start_date: Start date (up to 5 years back).
            end_date: End date.

        Returns:
            ExtractionResult with row counts.
        """
        result = ExtractionResult(errors=[])

        # 1. Get continuous futures
        logger.info(f"=== Extracting {root} bond basis data ===")
        futures_df = self.get_continuous_futures_history(root, start_date, end_date)
        result.futures_rows = len(futures_df)

        # 2. Get current deliverable basket
        basket = self.get_current_deliverable_basket(root)

        # 3. Get bond prices for each deliverable
        for bond in basket:
            cusip = bond.get("cusip", "")
            if not cusip:
                continue

            bond_df = self.get_bond_price_history(cusip, start_date, end_date)
            result.bond_rows += len(bond_df)

        # 4. Get repo rates
        for tenor in ["ON", "1M", "3M", "SOFR"]:
            repo_df = self.get_repo_rate_history(start_date, end_date, tenor)
            result.repo_rows += len(repo_df)

        logger.info(
            f"Extraction complete: {result.futures_rows} futures, "
            f"{result.bond_rows} bond, {result.repo_rows} repo rows"
        )

        return result


def get_first_delivery_date(month_code: str, year: int) -> date:
    """
    Get the first delivery date for a contract.

    Per CME specifications, bond eligibility is calculated from the first day
    of the delivery month (not the first business day).

    Args:
        month_code: Contract month code (H, M, U, Z).
        year: Full year (e.g., 2026).

    Returns:
        First day of the delivery month.
    """
    month = MONTH_CODE_MAP.get(month_code)
    if month is None:
        raise ValueError(f"Unknown month code: {month_code}")
    return date(year, month, 1)


def generate_contract_list(
    start_year: int,
    end_year: int,
) -> list[tuple[str, int, date]]:
    """
    Generate list of quarterly Treasury futures contracts for a date range.

    All Treasury futures use the same quarterly cycle (H, M, U, Z).

    Args:
        start_year: Start year (inclusive).
        end_year: End year (inclusive).

    Returns:
        List of (month_code, year, first_delivery_date) tuples.
    """
    contracts = []
    for year in range(start_year, end_year + 1):
        for month in CONTRACT_MONTHS:
            first_delivery = get_first_delivery_date(month, year)
            contracts.append((month, year, first_delivery))

    return contracts
