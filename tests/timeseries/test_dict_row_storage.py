"""Storage readers must use the dictionary rows supplied by get_connection."""

from datetime import date
from unittest.mock import MagicMock

from lseg_toolkit.timeseries.bond_basis.conversion_factor import ConversionFactorFetcher
from lseg_toolkit.timeseries.storage.progress import get_extraction_progress
from lseg_toolkit.timeseries.storage.resolver import SymbolResolver


def connection_with_rows(rows):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchall.return_value = rows
    return conn


def test_symbol_preload_reads_dict_rows():
    resolver = SymbolResolver(connection_with_rows([{"symbol": "ZN", "id": 42}]))
    assert resolver.preload() == 1
    assert resolver._cache == {"ZN": 42}


def test_conversion_factor_get_reads_dict_rows():
    record = {
        "bond_cusip": "91282CLW9",
        "conversion_factor": 0.875,
        "source": "manual",
        "effective_date": date(2026, 9, 1),
    }
    assert ConversionFactorFetcher(connection_with_rows([record])).get(1) == [record]


def test_progress_returns_values_not_column_names():
    record = {"id": 7, "instrument": "ZN", "status": "completed"}
    conn = connection_with_rows([record])
    assert get_extraction_progress(conn) == [record]
