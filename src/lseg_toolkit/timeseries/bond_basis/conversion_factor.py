"""
CME Treasury Futures Conversion Factor utilities.

Provides:
1. Lookup from CME's official Excel tables (preferred)
2. CF calculation using CME's formula (fallback)
3. Parsing of CME Excel/CSV conversion factor files
4. Storage of CFs in the database

Note: CME publishes CFs at:
- Lookup tables: cmegroup.com/trading/interest-rates/us-treasury-futures-conversion-factor-lookup-tables.html
- Excel file stored in: imports/treasury-futures-conversion-factor-look-up-tables.xls
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import psycopg

# Default path to CME CF lookup table
DEFAULT_CF_FILE = (
    Path(__file__).parents[4]
    / "imports"
    / "treasury-futures-conversion-factor-look-up-tables.xls"
)

# Sheet names in CME Excel file
CME_SHEET_NAMES = {
    "TU": "2-Year Note Table",
    "ZT": "2-Year Note Table",
    "FV": "5-Year Note Table",
    "ZF": "5-Year Note Table",
    "TY": "10-Year Note Table",
    "ZN": "10-Year Note Table",
    "US": "Classic Bond & Ultra Bond Table",
    "ZB": "Classic Bond & Ultra Bond Table",
    "UB": "Classic Bond & Ultra Bond Table",
}


@dataclass
class ConversionFactorResult:
    """Result of a conversion factor calculation or lookup."""

    bond_cusip: str
    futures_contract: str
    conversion_factor: float
    source: str  # 'calculated', 'cme_lookup', 'cme_excel'
    coupon_rate: float
    maturity_date: date
    first_delivery_date: date


def load_cme_cf_table(
    filepath: str | Path | None = None,
    sheet_name: str = "10-Year Note Table",
) -> dict[float, dict[str, float]]:
    """
    Load CME conversion factor lookup table from Excel file.

    Args:
        filepath: Path to CME Excel file. Defaults to imports/ directory.
        sheet_name: Sheet to load (e.g., '10-Year Note Table').

    Returns:
        Nested dict: {coupon: {years_months: cf}}
        Example: {4.125: {'6—6': 0.9003, '7—0': 0.9153, ...}}
    """
    filepath = Path(filepath) if filepath else DEFAULT_CF_FILE

    if not filepath.exists():
        return {}

    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    # Row 4 has column headers (Years—Months format)
    cols = df.iloc[4, 1:].tolist()

    cf_dict: dict[float, dict[str, float]] = {}

    for i in range(5, len(df)):
        coupon_val = df.iloc[i, 0]
        if pd.isna(coupon_val):
            continue

        coupon_float = float(str(coupon_val))
        cf_dict[coupon_float] = {}

        for j, col in enumerate(cols):
            cf_val = df.iloc[i, j + 1]
            if pd.notna(col) and pd.notna(cf_val):
                cf_dict[coupon_float][str(col)] = float(str(cf_val))

    return cf_dict


def lookup_cf_from_table(
    coupon: float,
    maturity_date: date,
    first_delivery_date: date,
    cf_table: dict[float, dict[str, float]] | None = None,
    futures_root: str = "TY",
) -> float | None:
    """
    Look up conversion factor from CME table.

    Args:
        coupon: Annual coupon rate as percentage (e.g., 4.125).
        maturity_date: Bond maturity date.
        first_delivery_date: First delivery date of futures contract.
        cf_table: Pre-loaded CF table, or None to load default.
        futures_root: Futures root to determine which sheet to use.

    Returns:
        Conversion factor if found, None otherwise.
    """
    if cf_table is None:
        sheet = CME_SHEET_NAMES.get(futures_root, "10-Year Note Table")
        cf_table = load_cme_cf_table(sheet_name=sheet)

    if not cf_table:
        return None

    # Calculate months to maturity
    days = (maturity_date - first_delivery_date).days
    months = int(days / 30.4375)

    # Round DOWN to nearest quarter (CME convention)
    months_rounded = (months // 3) * 3

    years = months_rounded // 12
    remaining_months = months_rounded % 12

    # Build column key (e.g., "6—6" for 6 years 6 months)
    col_key = f"{years}—{remaining_months}"

    # Find matching coupon (may need to round)
    # CME table has coupons in 0.125 increments
    coupon_rounded = round(coupon * 8) / 8  # Round to nearest 0.125

    if coupon_rounded in cf_table and col_key in cf_table[coupon_rounded]:
        return cf_table[coupon_rounded][col_key]

    # Try exact coupon
    if coupon in cf_table and col_key in cf_table[coupon]:
        return cf_table[coupon][col_key]

    return None


def months_to_maturity(maturity_date: date, first_delivery_date: date) -> int:
    """
    Calculate months from first delivery to maturity.

    CME uses first day of delivery month for calculations.

    Args:
        maturity_date: Bond maturity date.
        first_delivery_date: First delivery date of futures contract.

    Returns:
        Whole months to maturity.
    """
    # Use first of delivery month
    delivery_start = first_delivery_date.replace(day=1)

    years = maturity_date.year - delivery_start.year
    months = maturity_date.month - delivery_start.month

    total_months = years * 12 + months

    # Adjust for day of month
    if maturity_date.day < delivery_start.day:
        total_months -= 1

    return max(0, total_months)


def calculate_conversion_factor(
    coupon_rate: float,
    maturity_date: date,
    first_delivery_date: date,
) -> float:
    """
    Calculate CME conversion factor using 6% yield assumption.

    The CF is the price at which $1 par would trade if it yielded exactly 6%.
    CME rounds maturity DOWN to the nearest quarter (3 months).

    Formula:
        CF = (c/2) * [1 - (1+y/2)^(-n)] / (y/2) + (1+y/2)^(-n) - accrued_adj

    Where:
        c = coupon rate (decimal)
        y = 0.06 (6% annual)
        n = number of semiannual periods
        z = months to maturity, rounded DOWN to nearest quarter
        accrued_adj = (c/2) * (6-v)/6 where v = z % 6

    Args:
        coupon_rate: Annual coupon rate as decimal (e.g., 0.04125 for 4.125%).
        maturity_date: Bond maturity date.
        first_delivery_date: First delivery date of the futures contract.

    Returns:
        Conversion factor rounded to 4 decimal places.

    Example:
        >>> calculate_conversion_factor(0.04125, date(2032, 11, 15), date(2026, 3, 1))
        0.9003
    """
    # Calculate months to maturity
    z_raw = months_to_maturity(maturity_date, first_delivery_date)

    # Round DOWN to nearest quarter (CME convention)
    z = (z_raw // 3) * 3

    # Edge case: very short maturity
    if z <= 0:
        return 1.0

    # CME uses 6% yield
    y = 0.06
    c = coupon_rate

    # Number of semiannual periods
    n = z / 6

    # v = remainder when z is divided by 6 (for accrued interest adjustment)
    v = z % 6

    # Calculate present value factor
    pv_factor = (1 + y / 2) ** (-n)

    # Annuity factor for coupon payments
    if y > 0:
        annuity = (1 - pv_factor) / (y / 2)
    else:
        annuity = n

    # Coupon PV
    coupon_pv = (c / 2) * annuity

    # Principal PV
    principal_pv = pv_factor

    # Accrued interest adjustment (subtract partial period accrual)
    accrued_adj = (c / 2) * (6 - v) / 6

    # Total CF
    cf = coupon_pv + principal_pv - accrued_adj

    # CME rounds to 4 decimal places
    return round(cf, 4)


class ConversionFactorFetcher:
    """
    Fetch and store conversion factors from various sources.

    Supports:
    - Manual calculation using CME formula
    - Parsing CME Excel/CSV exports
    - Database storage and retrieval
    """

    def __init__(self, conn: psycopg.Connection | None = None):
        """
        Initialize the fetcher.

        Args:
            conn: Optional database connection for storage/retrieval.
        """
        self.conn = conn

    def calculate(
        self,
        coupon_rate: float,
        maturity_date: date,
        first_delivery_date: date,
        bond_cusip: str = "",
        futures_contract: str = "",
    ) -> ConversionFactorResult:
        """
        Calculate CF using CME formula.

        Args:
            coupon_rate: Annual coupon as decimal (0.04125 for 4.125%).
            maturity_date: Bond maturity date.
            first_delivery_date: First delivery of futures contract.
            bond_cusip: Optional CUSIP for result tracking.
            futures_contract: Optional contract code (e.g., 'TYH26').

        Returns:
            ConversionFactorResult with calculated CF.
        """
        cf = calculate_conversion_factor(
            coupon_rate, maturity_date, first_delivery_date
        )

        return ConversionFactorResult(
            bond_cusip=bond_cusip,
            futures_contract=futures_contract,
            conversion_factor=cf,
            source="calculated",
            coupon_rate=coupon_rate,
            maturity_date=maturity_date,
            first_delivery_date=first_delivery_date,
        )

    def parse_csv(self, filepath: str | Path) -> list[ConversionFactorResult]:
        """
        Parse conversion factors from a CSV file.

        Expected columns: cusip, contract, coupon, maturity, cf
        Or CME format: Coupon, Maturity, [contract columns...]

        Args:
            filepath: Path to CSV file.

        Returns:
            List of ConversionFactorResult objects.
        """
        results = []
        filepath = Path(filepath)

        with filepath.open() as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Detect format
            if "cusip" in [h.lower() for h in headers]:
                # Simple format: cusip, contract, coupon, maturity, cf
                for row in reader:
                    cusip = row.get("cusip", row.get("CUSIP", ""))
                    contract = row.get("contract", row.get("Contract", ""))
                    coupon = float(row.get("coupon", row.get("Coupon", 0)))
                    maturity_str = row.get("maturity", row.get("Maturity", ""))
                    cf = float(row.get("cf", row.get("CF", 0)))

                    # Parse maturity date (try common formats)
                    maturity = self._parse_date(maturity_str)

                    results.append(
                        ConversionFactorResult(
                            bond_cusip=cusip,
                            futures_contract=contract,
                            conversion_factor=cf,
                            source="cme_csv",
                            coupon_rate=coupon / 100 if coupon > 1 else coupon,
                            maturity_date=maturity,
                            first_delivery_date=date.today(),  # Not in CSV
                        )
                    )

        return results

    def _parse_date(self, date_str: str) -> date:
        """Parse date from various formats."""
        from datetime import datetime

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%d-%b-%Y",
            "%d-%b-%y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Cannot parse date: {date_str}")

    def store(
        self,
        results: list[ConversionFactorResult],
        futures_contract_id: int,
    ) -> int:
        """
        Store conversion factors in the database.

        Args:
            results: List of CF results to store.
            futures_contract_id: FK to futures_contracts table.

        Returns:
            Number of rows inserted.
        """
        if not self.conn:
            raise RuntimeError("No database connection provided")

        inserted = 0
        with self.conn.cursor() as cur:
            for r in results:
                cur.execute(
                    """
                    INSERT INTO conversion_factors
                        (futures_contract_id, bond_cusip, conversion_factor, source, effective_date)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (futures_contract_id, bond_cusip) DO UPDATE SET
                        conversion_factor = EXCLUDED.conversion_factor,
                        source = EXCLUDED.source
                    """,
                    (
                        futures_contract_id,
                        r.bond_cusip,
                        r.conversion_factor,
                        r.source,
                        r.first_delivery_date,
                    ),
                )
                inserted += 1

        self.conn.commit()
        return inserted

    def get(
        self,
        futures_contract_id: int,
        bond_cusip: str | None = None,
    ) -> list[dict]:
        """
        Retrieve conversion factors from database.

        Args:
            futures_contract_id: FK to futures_contracts table.
            bond_cusip: Optional filter by CUSIP.

        Returns:
            List of CF records as dicts.
        """
        if not self.conn:
            raise RuntimeError("No database connection provided")

        with self.conn.cursor() as cur:
            if bond_cusip:
                cur.execute(
                    """
                    SELECT bond_cusip, conversion_factor, source, effective_date
                    FROM conversion_factors
                    WHERE futures_contract_id = %s AND bond_cusip = %s
                    """,
                    (futures_contract_id, bond_cusip),
                )
            else:
                cur.execute(
                    """
                    SELECT bond_cusip, conversion_factor, source, effective_date
                    FROM conversion_factors
                    WHERE futures_contract_id = %s
                    ORDER BY bond_cusip
                    """,
                    (futures_contract_id,),
                )

            rows = cur.fetchall()
            return [
                {
                    "bond_cusip": row[0],
                    "conversion_factor": row[1],
                    "source": row[2],
                    "effective_date": row[3],
                }
                for row in rows
            ]
