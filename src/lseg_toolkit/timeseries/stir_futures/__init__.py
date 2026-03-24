"""
STIR (Short-Term Interest Rate) futures extraction module.

Provides tools for fetching historical STIR futures data:
- 3M SOFR futures (CME SR3 → LSEG SRA)
- Fed Funds futures (CME ZQ → LSEG FF)
- Euribor futures (LSEG FEI)
- SONIA futures (LSEG SON)

Note: 1M SOFR (SR1/SOFR) is access-denied and not supported.

RIC Mappings:
    CME SR3  → LSEG SRAc1, SRAc2, ... (3M SOFR)
    CME ZQ   → LSEG FFc1, FFc2, ...   (Fed Funds)
    --       → LSEG FEIc1, FEIc2, ... (Euribor)
    --       → LSEG SONc1, SONc2, ... (SONIA)
"""

from lseg_toolkit.timeseries.stir_futures.contracts import (
    STIR_CONTRACT_SPECS,
    StirProduct,
    generate_contract_rics,
    get_active_contracts,
    get_chain_ric,
    get_continuous_rank_contract,
    get_continuous_ric,
    get_contract_expiry_month,
    get_front_month_contract,
    get_futures_month_code,
)

__all__ = [
    "STIR_CONTRACT_SPECS",
    "StirProduct",
    "generate_contract_rics",
    "get_active_contracts",
    "get_chain_ric",
    "get_continuous_ric",
    "get_continuous_rank_contract",
    "get_contract_expiry_month",
    "get_front_month_contract",
    "get_futures_month_code",
]
