"""
Bond basis data extraction module.

Provides tools for fetching the prerequisite data needed for bond basis analysis:
- Conversion factors (from CME)
- Deliverable bond baskets
- Bond prices (via CUSIP RICs)
- Futures prices (continuous and discrete contracts)
- Repo rates

Note: Actual basis calculations happen downstream in another library.
This module focuses on data extraction and storage.
"""

from lseg_toolkit.bonds import (
    TreasuryNote,
    fetch_all_notes,
    get_deliverable_basket,
)
from lseg_toolkit.timeseries.bond_basis.conversion_factor import (
    ConversionFactorFetcher,
    ConversionFactorResult,
    calculate_conversion_factor,
    load_cme_cf_table,
    lookup_cf_from_table,
)
from lseg_toolkit.timeseries.bond_basis.extractor import (
    BondBasisExtractor,
    ExtractionResult,
    generate_contract_list,
    get_first_delivery_date,
)

__all__ = [
    # Conversion factors
    "ConversionFactorFetcher",
    "ConversionFactorResult",
    "calculate_conversion_factor",
    "load_cme_cf_table",
    "lookup_cf_from_table",
    # Treasury API
    "TreasuryNote",
    "fetch_all_notes",
    "get_deliverable_basket",
    # Extraction
    "BondBasisExtractor",
    "ExtractionResult",
    "generate_contract_list",
    "get_first_delivery_date",
]
