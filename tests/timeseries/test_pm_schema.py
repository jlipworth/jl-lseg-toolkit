"""Tests for prediction market database schema."""

from unittest.mock import MagicMock

from lseg_toolkit.timeseries.prediction_markets.schema import (
    PM_COMPRESSION_SQL,
    PM_HYPERTABLE_SQL,
    PM_SCHEMA_SQL,
    init_pm_schema,
    seed_kalshi_platform,
)


class TestSchemaSQL:
    """Verify DDL strings contain required table definitions."""

    def test_schema_creates_pm_platforms(self):
        assert "CREATE TABLE IF NOT EXISTS pm_platforms" in PM_SCHEMA_SQL

    def test_schema_creates_pm_series(self):
        assert "CREATE TABLE IF NOT EXISTS pm_series" in PM_SCHEMA_SQL

    def test_schema_creates_pm_markets(self):
        assert "CREATE TABLE IF NOT EXISTS pm_markets" in PM_SCHEMA_SQL

    def test_schema_creates_pm_candlesticks(self):
        assert "CREATE TABLE IF NOT EXISTS pm_candlesticks" in PM_SCHEMA_SQL

    def test_pm_markets_has_fomc_fk(self):
        """pm_markets should reference fomc_meetings(id)."""
        assert "REFERENCES fomc_meetings(id)" in PM_SCHEMA_SQL

    def test_pm_candlesticks_has_market_fk(self):
        """pm_candlesticks should reference pm_markets(id)."""
        assert "REFERENCES pm_markets(id)" in PM_SCHEMA_SQL

    def test_pm_markets_has_event_ticker_index(self):
        assert "idx_pm_markets_event_ticker" in PM_SCHEMA_SQL

    def test_pm_markets_has_status_index(self):
        assert "idx_pm_markets_status" in PM_SCHEMA_SQL

    def test_hypertable_creates_candlesticks(self):
        assert "pm_candlesticks" in PM_HYPERTABLE_SQL

    def test_compression_policy(self):
        assert "compress_segmentby" in PM_COMPRESSION_SQL
        assert "market_id" in PM_COMPRESSION_SQL


class TestInitPMSchema:
    """Tests for schema initialization function."""

    def test_init_executes_sql(self):
        """init_pm_schema should execute DDL statements."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        init_pm_schema(mock_conn)

        # Should execute schema, hypertable, and compression SQL
        assert mock_cursor.execute.call_count >= 3
        mock_conn.commit.assert_called()


class TestSeedKalshiPlatform:
    """Tests for Kalshi platform seeding."""

    def test_seed_inserts_kalshi(self):
        """Should insert Kalshi platform row."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {"id": 1}

        platform_id = seed_kalshi_platform(mock_conn)

        assert platform_id == 1
        mock_cursor.execute.assert_called_once()
        # Verify it's an upsert
        sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql
