"""
Unit tests for the STIR futures module.

Tests contract generation, RIC parsing, and discovery without requiring LSEG connection.
"""

from datetime import date

import pytest

from lseg_toolkit.timeseries.stir_futures import (
    STIR_CONTRACT_SPECS,
    generate_contract_rics,
    get_active_contracts,
    get_chain_ric,
    get_continuous_ric,
    get_continuous_rank_contract,
    get_contract_expiry_month,
)


class TestContractGeneration:
    """Test contract RIC generation."""

    def test_generate_ff_monthly_contracts(self):
        """Fed Funds (FF) should generate monthly contracts (all 12 months)."""
        rics = generate_contract_rics("FF", 2023, 2023)

        assert len(rics) == 12  # All 12 months
        assert rics[0] == "FFF23"  # January (F)
        assert rics[1] == "FFG23"  # February (G)
        assert rics[11] == "FFZ23"  # December (Z)

    def test_generate_sra_quarterly_contracts(self):
        """3M SOFR (SRA) should generate quarterly contracts (H, M, U, Z)."""
        rics = generate_contract_rics("SRA", 2023, 2023)

        assert len(rics) == 4  # Quarterly: Mar, Jun, Sep, Dec
        assert rics[0] == "SRAH23"  # March (H)
        assert rics[1] == "SRAM23"  # June (M)
        assert rics[2] == "SRAU23"  # September (U)
        assert rics[3] == "SRAZ23"  # December (Z)

    def test_generate_fei_quarterly_contracts(self):
        """Euribor (FEI) should generate quarterly contracts."""
        rics = generate_contract_rics("FEI", 2023, 2023)

        assert len(rics) == 4
        assert rics[0] == "FEIH23"
        assert rics[3] == "FEIZ23"

    def test_generate_son_quarterly_contracts(self):
        """SONIA (SON) should generate quarterly contracts."""
        rics = generate_contract_rics("SON", 2023, 2023)

        assert len(rics) == 4
        assert rics[0] == "SONH23"
        assert rics[3] == "SONZ23"

    def test_generate_multi_year_range(self):
        """Should generate contracts across multiple years."""
        rics = generate_contract_rics("FF", 2023, 2024)

        assert len(rics) == 24  # 12 months * 2 years
        assert rics[0] == "FFF23"
        assert rics[11] == "FFZ23"
        assert rics[12] == "FFF24"
        assert rics[23] == "FFZ24"

    def test_generate_single_year(self):
        """Should work for single year (start == end)."""
        rics = generate_contract_rics("SRA", 2025, 2025)

        assert len(rics) == 4
        assert all("25" in ric for ric in rics)

    def test_invalid_product_raises_error(self):
        """Unknown product should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_contract_rics("INVALID", 2023, 2024)

        assert "Unknown product" in str(exc_info.value)

    def test_year_suffix_formatting(self):
        """Year suffix should be last 2 digits."""
        rics_2020 = generate_contract_rics("SRA", 2020, 2020)
        rics_2029 = generate_contract_rics("SRA", 2029, 2029)

        assert all("20" in ric for ric in rics_2020)
        assert all("29" in ric for ric in rics_2029)


class TestContractExpiryParsing:
    """Test contract RIC parsing."""

    def test_parse_ff_contract(self):
        """Should parse Fed Funds contract RIC."""
        year, month = get_contract_expiry_month("FFZ24")

        assert year == 2024
        assert month == 12  # Z = December

    def test_parse_sra_contract(self):
        """Should parse 3M SOFR contract RIC."""
        year, month = get_contract_expiry_month("SRAH25")

        assert year == 2025
        assert month == 3  # H = March

    def test_parse_fei_contract(self):
        """Should parse Euribor contract RIC."""
        year, month = get_contract_expiry_month("FEIM24")

        assert year == 2024
        assert month == 6  # M = June

    def test_parse_all_month_codes(self):
        """Should correctly parse all 12 month codes."""
        month_codes = "FGHJKMNQUVXZ"
        expected_months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

        for code, expected_month in zip(month_codes, expected_months, strict=True):
            ric = f"FF{code}24"
            year, month = get_contract_expiry_month(ric)

            assert year == 2024
            assert month == expected_month

    def test_parse_invalid_ric_returns_none(self):
        """Invalid RIC should return None."""
        result = get_contract_expiry_month("INVALID")

        assert result is None

    def test_parse_missing_year_returns_none(self):
        """RIC without year suffix should return None."""
        result = get_contract_expiry_month("FFZ")

        assert result is None

    def test_parse_ric_with_embedded_month_code(self):
        """RIC like FF24 has F=Jan month code at start - parses as Jan 2024."""
        # Note: FF24 contains 'F' which is a valid month code (January)
        # The regex looks for pattern [FGHJKMNQUVXZ]\d{2}$ at end
        result = get_contract_expiry_month("FF24")

        # 'F24' matches: F=January, 24=2024
        assert result == (2024, 1)


class TestActiveContracts:
    """Test active contract discovery."""

    def test_get_active_ff_from_january(self):
        """Fed Funds monthly contracts starting from January."""
        contracts = get_active_contracts("FF", as_of=date(2024, 1, 15), num_contracts=6)

        assert len(contracts) == 6
        assert contracts[0] == "FFF24"  # Jan 2024 (F)
        assert contracts[1] == "FFG24"  # Feb 2024 (G)
        assert contracts[5] == "FFM24"  # Jun 2024 (M) - 6th month from Jan

    def test_get_active_ff_wraps_year(self):
        """Fed Funds should wrap to next year correctly."""
        contracts = get_active_contracts("FF", as_of=date(2024, 10, 1), num_contracts=6)

        assert len(contracts) == 6
        assert contracts[0] == "FFV24"  # Oct 2024 (V)
        assert contracts[1] == "FFX24"  # Nov 2024 (X)
        assert contracts[2] == "FFZ24"  # Dec 2024 (Z)
        assert contracts[3] == "FFF25"  # Jan 2025 (F)
        assert contracts[4] == "FFG25"  # Feb 2025 (G)
        assert contracts[5] == "FFH25"  # Mar 2025 (H)

    def test_get_active_sra_quarterly_from_january(self):
        """3M SOFR quarterly contracts starting from January."""
        contracts = get_active_contracts(
            "SRA", as_of=date(2024, 1, 15), num_contracts=4
        )

        assert len(contracts) == 4
        assert contracts[0] == "SRAH24"  # Mar 2024
        assert contracts[1] == "SRAM24"  # Jun 2024
        assert contracts[2] == "SRAU24"  # Sep 2024
        assert contracts[3] == "SRAZ24"  # Dec 2024

    def test_get_active_sra_quarterly_from_march(self):
        """3M SOFR contracts from March should start with March."""
        contracts = get_active_contracts("SRA", as_of=date(2024, 3, 1), num_contracts=4)

        assert len(contracts) == 4
        assert contracts[0] == "SRAH24"  # Mar 2024 (H)
        assert contracts[1] == "SRAM24"  # Jun 2024 (M)

    def test_get_active_sra_quarterly_from_april(self):
        """3M SOFR contracts from April should skip to June."""
        contracts = get_active_contracts(
            "SRA", as_of=date(2024, 4, 15), num_contracts=4
        )

        assert len(contracts) == 4
        assert contracts[0] == "SRAM24"  # Jun 2024 (next quarterly)
        assert contracts[1] == "SRAU24"  # Sep 2024
        assert contracts[2] == "SRAZ24"  # Dec 2024
        assert contracts[3] == "SRAH25"  # Mar 2025

    def test_get_active_quarterly_wraps_year(self):
        """Quarterly contracts should wrap to next year correctly."""
        contracts = get_active_contracts(
            "SRA", as_of=date(2024, 10, 1), num_contracts=6
        )

        assert len(contracts) == 6
        assert contracts[0] == "SRAZ24"  # Dec 2024 (Oct is after Sep, next is Dec)
        assert contracts[1] == "SRAH25"  # Mar 2025
        assert contracts[2] == "SRAM25"  # Jun 2025
        assert contracts[3] == "SRAU25"  # Sep 2025
        assert contracts[4] == "SRAZ25"  # Dec 2025
        assert contracts[5] == "SRAH26"  # Mar 2026

    def test_get_active_defaults_to_today(self):
        """Should default to today if as_of not specified."""
        contracts = get_active_contracts("FF", num_contracts=3)

        assert len(contracts) == 3
        # Just verify we got 3 contracts with valid format
        for contract in contracts:
            assert contract.startswith("FF")
            assert len(contract) == 5  # FFX## format

    def test_get_active_fei_quarterly(self):
        """Euribor should behave like other quarterly products."""
        contracts = get_active_contracts(
            "FEI", as_of=date(2024, 1, 15), num_contracts=4
        )

        assert len(contracts) == 4
        assert contracts[0] == "FEIH24"
        assert contracts[1] == "FEIM24"
        assert contracts[2] == "FEIU24"
        assert contracts[3] == "FEIZ24"

    def test_get_active_son_quarterly(self):
        """SONIA should behave like other quarterly products."""
        contracts = get_active_contracts(
            "SON", as_of=date(2024, 1, 15), num_contracts=4
        )

        assert len(contracts) == 4
        assert contracts[0] == "SONH24"
        assert contracts[1] == "SONM24"
        assert contracts[2] == "SONU24"
        assert contracts[3] == "SONZ24"

    def test_get_active_large_num_contracts(self):
        """Should handle large num_contracts correctly."""
        contracts = get_active_contracts("FF", as_of=date(2024, 1, 1), num_contracts=36)

        assert len(contracts) == 36  # 3 full years of monthly contracts
        assert contracts[0] == "FFF24"
        assert contracts[12] == "FFF25"
        assert contracts[24] == "FFF26"
        assert contracts[35] == "FFZ26"


class TestChainRics:
    """Test chain RIC discovery."""

    def test_get_chain_ff(self):
        """Fed Funds chain RIC should use constant."""
        chain = get_chain_ric("FF")

        assert chain == "0#FF:"

    def test_get_chain_sra(self):
        """3M SOFR chain RIC should use constant."""
        chain = get_chain_ric("SRA")

        assert chain == "0#SRA:"

    def test_get_chain_fei(self):
        """Euribor chain RIC should use constant or fallback."""
        chain = get_chain_ric("FEI")

        # Either from constant or fallback pattern
        assert "FEI" in chain

    def test_get_chain_son(self):
        """SONIA chain RIC should use fallback pattern."""
        chain = get_chain_ric("SON")

        # Fallback pattern
        assert chain == "0#SON:"


class TestContinuousRics:
    """Test continuous contract RIC generation."""

    def test_get_continuous_ff_front(self):
        """Fed Funds front month continuous."""
        ric = get_continuous_ric("FF", month=1)

        assert ric == "FFc1"

    def test_get_continuous_ff_second(self):
        """Fed Funds second month continuous."""
        ric = get_continuous_ric("FF", month=2)

        assert ric == "FFc2"

    def test_get_continuous_sra_front(self):
        """3M SOFR front month continuous."""
        ric = get_continuous_ric("SRA", month=1)

        assert ric == "SRAc1"

    def test_get_continuous_default_month(self):
        """Should default to month=1 (front contract)."""
        ric = get_continuous_ric("FF")

        assert ric == "FFc1"

    def test_get_continuous_all_products(self):
        """Should work for all STIR products."""
        products = ["FF", "SRA", "FEI", "SON"]

        for product in products:
            ric = get_continuous_ric(product, month=1)
            assert ric == f"{product}c1"

    def test_get_continuous_rank_contract_ff(self):
        """Fed Funds rank contracts should step through monthly contracts."""
        assert get_continuous_rank_contract("FF", date(2025, 9, 30), rank=1) == "FFV25"
        assert get_continuous_rank_contract("FF", date(2025, 9, 30), rank=2) == "FFX25"
        assert get_continuous_rank_contract("FF", date(2025, 9, 30), rank=3) == "FFZ25"

    def test_get_continuous_rank_contract_ff_wraps_year(self):
        """Fed Funds rank contracts should wrap year boundaries."""
        assert get_continuous_rank_contract("FF", date(2025, 10, 1), rank=1) == "FFX25"
        assert get_continuous_rank_contract("FF", date(2025, 10, 1), rank=2) == "FFZ25"
        assert get_continuous_rank_contract("FF", date(2025, 10, 1), rank=3) == "FFF26"


class TestContractSpecs:
    """Test STIR_CONTRACT_SPECS metadata."""

    def test_specs_contain_all_products(self):
        """Specs should contain all supported products."""
        products = ["FF", "SRA", "FEI", "SON"]

        for product in products:
            assert product in STIR_CONTRACT_SPECS

    def test_ff_spec_monthly(self):
        """Fed Funds spec should indicate monthly contracts."""
        spec = STIR_CONTRACT_SPECS["FF"]

        assert spec["months"] == "monthly"
        assert spec["name"] == "30-Day Fed Funds"
        assert spec["cme_symbol"] == "ZQ"
        assert spec["first_year"] == 1988

    def test_sra_spec_quarterly(self):
        """3M SOFR spec should indicate quarterly contracts."""
        spec = STIR_CONTRACT_SPECS["SRA"]

        assert spec["months"] == "quarterly"
        assert spec["name"] == "3-Month SOFR"
        assert spec["cme_symbol"] == "SR3"
        assert spec["first_year"] == 2018

    def test_fei_spec_quarterly(self):
        """Euribor spec should indicate quarterly contracts."""
        spec = STIR_CONTRACT_SPECS["FEI"]

        assert spec["months"] == "quarterly"
        assert spec["name"] == "3-Month Euribor"
        assert spec["exchange"] == "EUREX"
        assert spec["first_year"] == 1999

    def test_son_spec_quarterly(self):
        """SONIA spec should indicate quarterly contracts."""
        spec = STIR_CONTRACT_SPECS["SON"]

        assert spec["months"] == "quarterly"
        assert spec["name"] == "3-Month SONIA"
        assert spec["exchange"] == "ICE"
        assert spec["first_year"] == 2018


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_generate_year_2000_rollover(self):
        """Should handle 2000s decade correctly."""
        rics = generate_contract_rics("FF", 1999, 2000)

        assert "99" in rics[0]  # 1999
        assert "00" in rics[12]  # 2000

    def test_parse_year_2000s(self):
        """Should parse 2000s decade correctly (assumes 20xx)."""
        year, month = get_contract_expiry_month("FFZ00")

        assert year == 2000
        assert month == 12

    def test_active_contracts_from_december(self):
        """Should correctly roll from December to January."""
        contracts = get_active_contracts(
            "FF", as_of=date(2024, 12, 15), num_contracts=3
        )

        assert contracts[0] == "FFZ24"  # Dec 2024
        assert contracts[1] == "FFF25"  # Jan 2025
        assert contracts[2] == "FFG25"  # Feb 2025

    def test_active_quarterly_from_december(self):
        """Quarterly contracts should roll correctly from December."""
        contracts = get_active_contracts(
            "SRA", as_of=date(2024, 12, 15), num_contracts=4
        )

        assert contracts[0] == "SRAZ24"  # Dec 2024
        assert contracts[1] == "SRAH25"  # Mar 2025
        assert contracts[2] == "SRAM25"  # Jun 2025
        assert contracts[3] == "SRAU25"  # Sep 2025


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
