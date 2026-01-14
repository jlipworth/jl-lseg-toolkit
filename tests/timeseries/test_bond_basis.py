"""
Unit tests for the bond_basis module.

Tests contract generation, date calculations, and constant derivations without requiring LSEG connection.
Uses mocks for any API calls.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lseg_toolkit.timeseries.bond_basis import (
    BondBasisExtractor,
    ExtractionResult,
    generate_contract_list,
    get_first_delivery_date,
)
from lseg_toolkit.timeseries.bond_basis.extractor import (
    CONTRACT_MONTHS,
    MONTH_CODE_MAP,
    TREASURY_FUTURES,
)


class TestConstants:
    """Test that constants are correctly derived from shared constants."""

    def test_contract_months_quarterly(self):
        """CONTRACT_MONTHS should be quarterly codes (H, M, U, Z)."""
        assert CONTRACT_MONTHS == ["H", "M", "U", "Z"]

    def test_month_code_map_complete(self):
        """MONTH_CODE_MAP should map all quarterly codes to month numbers."""
        assert MONTH_CODE_MAP["H"] == 3  # March
        assert MONTH_CODE_MAP["M"] == 6  # June
        assert MONTH_CODE_MAP["U"] == 9  # September
        assert MONTH_CODE_MAP["Z"] == 12  # December
        assert len(MONTH_CODE_MAP) == 4

    def test_treasury_futures_mapping(self):
        """TREASURY_FUTURES should contain all major Treasury futures."""
        assert "TU" in TREASURY_FUTURES  # 2-Year
        assert "FV" in TREASURY_FUTURES  # 5-Year
        assert "TY" in TREASURY_FUTURES  # 10-Year
        assert "TN" in TREASURY_FUTURES  # Ultra 10-Year
        assert "US" in TREASURY_FUTURES  # T-Bond
        assert "UB" in TREASURY_FUTURES  # Ultra T-Bond

    def test_treasury_futures_cme_symbols(self):
        """TREASURY_FUTURES should have correct CME symbols."""
        assert TREASURY_FUTURES["TU"]["cme"] == "ZT"
        assert TREASURY_FUTURES["FV"]["cme"] == "ZF"
        assert TREASURY_FUTURES["TY"]["cme"] == "ZN"
        assert TREASURY_FUTURES["US"]["cme"] == "ZB"

    def test_treasury_futures_deliverable_chains(self):
        """TREASURY_FUTURES should have deliverable chain RICs."""
        assert TREASURY_FUTURES["TY"]["deliverable_chain"] == "0#TYc1=DLV"
        assert TREASURY_FUTURES["US"]["deliverable_chain"] == "0#USc1=DLV"


class TestFirstDeliveryDate:
    """Test first delivery date calculation."""

    def test_get_first_delivery_march(self):
        """March contract (H) should have March 1st delivery."""
        delivery_date = get_first_delivery_date("H", 2024)

        assert delivery_date == date(2024, 3, 1)

    def test_get_first_delivery_june(self):
        """June contract (M) should have June 1st delivery."""
        delivery_date = get_first_delivery_date("M", 2024)

        assert delivery_date == date(2024, 6, 1)

    def test_get_first_delivery_september(self):
        """September contract (U) should have September 1st delivery."""
        delivery_date = get_first_delivery_date("U", 2024)

        assert delivery_date == date(2024, 9, 1)

    def test_get_first_delivery_december(self):
        """December contract (Z) should have December 1st delivery."""
        delivery_date = get_first_delivery_date("Z", 2024)

        assert delivery_date == date(2024, 12, 1)

    def test_get_first_delivery_different_years(self):
        """Should work for different years."""
        assert get_first_delivery_date("H", 2023) == date(2023, 3, 1)
        assert get_first_delivery_date("H", 2025) == date(2025, 3, 1)
        assert get_first_delivery_date("Z", 2026) == date(2026, 12, 1)

    def test_get_first_delivery_invalid_month_code_raises(self):
        """Invalid month code should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_first_delivery_date("X", 2024)

        assert "Unknown month code" in str(exc_info.value)

    def test_get_first_delivery_lowercase_fails(self):
        """Lowercase month codes should fail (expects uppercase)."""
        with pytest.raises(ValueError):
            get_first_delivery_date("h", 2024)


class TestGenerateContractList:
    """Test contract list generation."""

    def test_generate_single_year(self):
        """Should generate 4 quarterly contracts for single year."""
        contracts = generate_contract_list(2024, 2024)

        assert len(contracts) == 4
        assert contracts[0] == ("H", 2024, date(2024, 3, 1))
        assert contracts[1] == ("M", 2024, date(2024, 6, 1))
        assert contracts[2] == ("U", 2024, date(2024, 9, 1))
        assert contracts[3] == ("Z", 2024, date(2024, 12, 1))

    def test_generate_two_years(self):
        """Should generate 8 contracts across 2 years."""
        contracts = generate_contract_list(2023, 2024)

        assert len(contracts) == 8
        assert contracts[0] == ("H", 2023, date(2023, 3, 1))
        assert contracts[3] == ("Z", 2023, date(2023, 12, 1))
        assert contracts[4] == ("H", 2024, date(2024, 3, 1))
        assert contracts[7] == ("Z", 2024, date(2024, 12, 1))

    def test_generate_contract_list_structure(self):
        """Contract list should have (month_code, year, date) tuples."""
        contracts = generate_contract_list(2024, 2024)

        for month_code, year, delivery_date in contracts:
            assert month_code in ["H", "M", "U", "Z"]
            assert year == 2024
            assert isinstance(delivery_date, date)

    def test_generate_contract_list_chronological(self):
        """Contracts should be in chronological order."""
        contracts = generate_contract_list(2023, 2025)

        dates = [d for _, _, d in contracts]
        assert dates == sorted(dates)

    def test_generate_five_year_range(self):
        """Should handle multi-year ranges."""
        contracts = generate_contract_list(2020, 2024)

        assert len(contracts) == 20  # 5 years * 4 quarters


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_extraction_result_defaults(self):
        """Should have sensible defaults."""
        result = ExtractionResult()

        assert result.futures_rows == 0
        assert result.bond_rows == 0
        assert result.repo_rows == 0
        assert result.errors is None

    def test_extraction_result_with_values(self):
        """Should accept custom values."""
        result = ExtractionResult(
            futures_rows=100,
            bond_rows=500,
            repo_rows=200,
            errors=["error1", "error2"],
        )

        assert result.futures_rows == 100
        assert result.bond_rows == 500
        assert result.repo_rows == 200
        assert len(result.errors) == 2


class TestBondBasisExtractorInit:
    """Test BondBasisExtractor initialization."""

    def test_extractor_requires_connection(self):
        """Extractor should require a psycopg connection."""
        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        assert extractor.conn is mock_conn


class TestContinuousFuturesHistory:
    """Test continuous futures history fetching."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_continuous_futures_basic(self, mock_rd):
        """Should fetch continuous front contract (c1)."""
        mock_df = pd.DataFrame(
            {
                "OPEN_PRC": [110.0],
                "HIGH_1": [111.0],
                "LOW_1": [109.0],
                "SETTLE": [110.5],
            }
        )
        mock_rd.get_history.return_value = mock_df

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_continuous_futures_history(
            "TY",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert not result.empty
        mock_rd.get_history.assert_called_once()
        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "TYc1"

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_continuous_futures_fields(self, mock_rd):
        """Should request standard futures fields."""
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_continuous_futures_history(
            "TY",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        call_args = mock_rd.get_history.call_args.kwargs
        fields = call_args["fields"]
        assert "SETTLE" in fields
        assert "OPEN_PRC" in fields
        assert "HIGH_1" in fields
        assert "OPINT_1" in fields

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_continuous_futures_none_returns_empty(self, mock_rd):
        """None response should return empty DataFrame."""
        mock_rd.get_history.return_value = None

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_continuous_futures_history(
            "TY",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result.empty


class TestDiscreteContractHistory:
    """Test discrete contract history fetching."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_discrete_contract_current_year(self, mock_rd):
        """Current year contracts should use plain format (no caret)."""
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        with patch("lseg_toolkit.timeseries.bond_basis.extractor.date") as mock_date:
            mock_date.today.return_value = date(2024, 1, 15)

            extractor.get_discrete_contract_history(
                root="TY",
                month_code="H",
                year=2024,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

            # Should request TYH4 (no caret)
            call_args = mock_rd.get_history.call_args
            assert call_args.args[0] == "TYH4"

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_discrete_contract_2010s_decade(self, mock_rd):
        """2010s contracts should use ^1 suffix."""
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_discrete_contract_history(
            root="TY",
            month_code="H",
            year=2018,
            start_date=date(2018, 1, 1),
            end_date=date(2018, 3, 31),
        )

        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "TYH8^1"

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_discrete_contract_2020s_expired(self, mock_rd):
        """Expired 2020s contracts should use ^2 suffix."""
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_discrete_contract_history(
            root="TY",
            month_code="H",
            year=2022,
            start_date=date(2022, 1, 1),
            end_date=date(2022, 3, 31),
        )

        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "TYH2^2"

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_discrete_contract_retry_with_caret(self, mock_rd):
        """Should retry with caret if first attempt fails for last year contracts.

        Retry logic only applies when year == current_year - 1 (last year).
        For 2020-2023, it goes directly to ^2 without retry.
        """
        from datetime import date as date_type

        # Get current year dynamically to find "last year"
        current_year = date_type.today().year
        last_year = current_year - 1
        last_digit = last_year % 10

        # First call fails, second succeeds
        mock_rd.get_history.side_effect = [
            Exception("Not found"),
            pd.DataFrame({"SETTLE": [110.5]}),
        ]

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_discrete_contract_history(
            root="TY",
            month_code="H",
            year=last_year,
            start_date=date(last_year, 1, 1),
            end_date=date(last_year, 3, 31),
        )

        assert not result.empty
        assert mock_rd.get_history.call_count == 2
        # First call: without caret (TYH5 for 2025)
        assert mock_rd.get_history.call_args_list[0].args[0] == f"TYH{last_digit}"
        # Second call: with caret (TYH5^2 for 2025)
        assert mock_rd.get_history.call_args_list[1].args[0] == f"TYH{last_digit}^2"


class TestDeliverableBasket:
    """Test deliverable basket fetching."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_deliverable_basket_basic(self, mock_rd):
        """Should fetch current deliverable basket."""
        mock_df = pd.DataFrame(
            {
                "Instrument": ["91282CFV8=", "91282CGD5="],
                "DSPLY_NAME": ["T 2.5 05/15/24", "T 2.75 05/15/24"],
                "CF_CLOSE": [100.5, 101.2],
                "COUPN_RATE": [2.5, 2.75],
                "MATUR_DATE": ["2024-05-15", "2024-05-15"],
            }
        )
        mock_rd.get_data.return_value = mock_df

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        basket = extractor.get_current_deliverable_basket("TY")

        assert len(basket) == 2
        assert basket[0]["cusip"] == "91282CFV8"
        assert basket[0]["coupon_rate"] == 2.5
        mock_rd.get_data.assert_called_once()

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_deliverable_basket_unknown_root(self, mock_rd):
        """Unknown futures root should return empty list."""
        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        basket = extractor.get_current_deliverable_basket("INVALID")

        assert basket == []
        mock_rd.get_data.assert_not_called()

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_deliverable_basket_no_data(self, mock_rd):
        """No data should return empty list."""
        mock_rd.get_data.return_value = None

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        basket = extractor.get_current_deliverable_basket("TY")

        assert basket == []


class TestBondPriceHistory:
    """Test bond price history fetching."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_bond_price_history_cusip(self, mock_rd):
        """Should accept CUSIP and convert to RIC."""
        mock_df = pd.DataFrame(
            {
                "BID": [100.5],
                "ASK": [100.6],
                "MID_YLD_1": [2.5],
            }
        )
        mock_rd.get_history.return_value = mock_df

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_bond_price_history(
            "91282CFV8",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert not result.empty
        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "91282CFV8="

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_bond_price_history_ric(self, mock_rd):
        """Should accept RIC format as-is."""
        mock_rd.get_history.return_value = pd.DataFrame({"BID": [100.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_bond_price_history(
            "91282CFV8=",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "91282CFV8="

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_bond_price_history_fields(self, mock_rd):
        """Should request bond-specific fields."""
        mock_rd.get_history.return_value = pd.DataFrame({"BID": [100.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_bond_price_history(
            "91282CFV8",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        call_args = mock_rd.get_history.call_args.kwargs
        fields = call_args["fields"]
        assert "BID" in fields
        assert "ASK" in fields
        assert "MID_YLD_1" in fields
        assert "MOD_DURTN" in fields


class TestRepoRateHistory:
    """Test repo rate history fetching."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_repo_rate_overnight(self, mock_rd):
        """Should fetch overnight repo rates."""
        mock_df = pd.DataFrame(
            {
                "BID": [5.1],
                "ASK": [5.15],
                "MID_PRICE": [5.125],
            }
        )
        mock_rd.get_history.return_value = mock_df

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_repo_rate_history(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            tenor="ON",
        )

        assert not result.empty
        call_args = mock_rd.get_history.call_args
        assert call_args.args[0] == "USONRP="

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_repo_rate_term_tenors(self, mock_rd):
        """Should fetch term repo rates."""
        mock_rd.get_history.return_value = pd.DataFrame({"MID_PRICE": [5.125]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        # Test 1M, 3M
        extractor.get_repo_rate_history(date(2024, 1, 1), date(2024, 1, 31), "1M")
        assert mock_rd.get_history.call_args.args[0] == "US1MRP="

        extractor.get_repo_rate_history(date(2024, 1, 1), date(2024, 1, 31), "3M")
        assert mock_rd.get_history.call_args.args[0] == "US3MRP="

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_repo_rate_sofr(self, mock_rd):
        """Should fetch SOFR as repo benchmark."""
        mock_rd.get_history.return_value = pd.DataFrame({"MID_PRICE": [5.125]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_repo_rate_history(date(2024, 1, 1), date(2024, 1, 31), "SOFR")
        assert mock_rd.get_history.call_args.args[0] == "USDSOFR="

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_get_repo_rate_invalid_tenor(self, mock_rd):
        """Invalid tenor should return empty DataFrame."""
        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.get_repo_rate_history(
            date(2024, 1, 1), date(2024, 1, 31), "INVALID"
        )

        assert result.empty
        mock_rd.get_history.assert_not_called()


class TestExtractAll:
    """Test the extract_all orchestration method."""

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_extract_all_basic(self, mock_rd):
        """extract_all should orchestrate all data fetching."""
        # Mock continuous futures
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5] * 10})

        # Mock deliverable basket
        mock_rd.get_data.return_value = pd.DataFrame(
            {
                "Instrument": ["91282CFV8="],
                "DSPLY_NAME": ["T 2.5 05/15/24"],
                "CF_CLOSE": [100.5],
                "COUPN_RATE": [2.5],
                "MATUR_DATE": ["2024-05-15"],
            }
        )

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        result = extractor.extract_all(
            root="TY",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert isinstance(result, ExtractionResult)
        assert result.futures_rows == 10
        assert result.bond_rows > 0
        assert result.repo_rows > 0

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_extract_all_fetches_all_components(self, mock_rd):
        """extract_all should fetch futures, bonds, and repo rates."""
        mock_rd.get_history.return_value = pd.DataFrame({"SETTLE": [110.5]})
        mock_rd.get_data.return_value = pd.DataFrame(
            {
                "Instrument": ["91282CFV8="],
                "DSPLY_NAME": ["T 2.5 05/15/24"],
                "CF_CLOSE": [100.5],
                "COUPN_RATE": [2.5],
                "MATUR_DATE": ["2024-05-15"],
            }
        )

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.extract_all("TY", date(2024, 1, 1), date(2024, 1, 31))

        # Should call get_history for futures, bonds, and repo rates
        # Should call get_data for deliverable basket
        assert mock_rd.get_history.call_count > 0
        assert mock_rd.get_data.call_count == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_first_delivery_leap_year(self):
        """Should handle leap years correctly."""
        # March 1st should work the same in leap years
        delivery = get_first_delivery_date("H", 2024)  # Leap year
        assert delivery == date(2024, 3, 1)

    def test_generate_contract_list_same_year(self):
        """Start year == end year should work."""
        contracts = generate_contract_list(2024, 2024)
        assert len(contracts) == 4

    def test_generate_contract_list_reverse_years_empty(self):
        """Reversed years should generate empty list."""
        contracts = generate_contract_list(2024, 2023)
        assert len(contracts) == 0

    @patch("lseg_toolkit.timeseries.bond_basis.extractor.rd")
    def test_bond_price_cusip_with_trailing_equals(self, mock_rd):
        """CUSIP with trailing = should not double-up."""
        mock_rd.get_history.return_value = pd.DataFrame({"BID": [100.5]})

        mock_conn = MagicMock()
        extractor = BondBasisExtractor(mock_conn)

        extractor.get_bond_price_history(
            "91282CFV8=",  # Already has =
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        call_args = mock_rd.get_history.call_args
        # Should not be "91282CFV8=="
        assert call_args.args[0] == "91282CFV8="


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
