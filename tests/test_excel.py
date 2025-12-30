"""Tests for Excel export utilities."""

import pandas as pd

from lseg_toolkit.excel import ExcelExporter


class TestExcelExporter:
    """Test cases for ExcelExporter."""

    def test_generate_filename_with_date(self):
        """Test filename generation with date stamp."""
        filename = ExcelExporter.generate_filename("test_report")
        assert filename.startswith("test_report_")
        assert filename.endswith(".xlsx")

    def test_generate_filename_without_date(self):
        """Test filename generation without date stamp."""
        filename = ExcelExporter.generate_filename("test_report", include_date=False)
        assert filename == "test_report.xlsx"

    def test_summary_sheet_basic(self, tmp_path):
        """Test basic summary sheet creation."""
        output_file = tmp_path / "test_summary.xlsx"

        params = {
            "Index": "SPX",
            "Start Date": "2025-10-27",
            "End Date": "2025-11-03",
            "Timezone": "US/Eastern",
        }

        stats = {
            "Total Companies": 50,
            "Total Sectors": 5,
            "Avg Market Cap (M)": 150000.0,
            "Median Market Cap (M)": 120000.0,
        }

        with ExcelExporter(output_file) as exporter:
            exporter.write_summary_sheet(
                sheet_name="Summary", params=params, statistics=stats
            )

        # Verify file was created
        assert output_file.exists()

        # Verify we can read it back
        df = pd.read_excel(output_file, sheet_name="Summary", header=None)
        assert len(df) > 0

    def test_summary_sheet_with_sector_breakdown(self, tmp_path):
        """Test summary sheet with sector breakdown."""
        output_file = tmp_path / "test_summary_sectors.xlsx"

        params = {"Index": "NDX", "Start Date": "2025-10-27", "End Date": "2025-11-03"}

        stats = {"Total Companies": 30, "Total Sectors": 3}

        sector_breakdown = {
            "Technology": {"count": 15, "percentage": 50.0},
            "Healthcare": {"count": 10, "percentage": 33.3},
            "Financials": {"count": 5, "percentage": 16.7},
        }

        with ExcelExporter(output_file) as exporter:
            exporter.write_summary_sheet(
                sheet_name="Summary",
                params=params,
                statistics=stats,
                sector_breakdown=sector_breakdown,
            )

        # Verify file was created
        assert output_file.exists()

        # Verify we can read it back
        df = pd.read_excel(output_file, sheet_name="Summary", header=None)
        assert len(df) > 0

        # Check that sector breakdown is present (should find "Technology" somewhere)
        content = df.to_string()
        assert "Technology" in content
        assert "Healthcare" in content

    def test_write_dataframe_basic(self, tmp_path):
        """Test basic DataFrame writing with formatting."""
        output_file = tmp_path / "test_dataframe.xlsx"

        # Create sample data
        data = {
            "Company": ["Apple Inc", "Microsoft Corp", "Alphabet Inc"],
            "Ticker": ["AAPL.O", "MSFT.O", "GOOGL.O"],
            "Market Cap (M)": [3000000.50, 2800000.75, 2000000.25],
            "P/E Ratio": [35.5, 38.2, 28.9],
        }
        df = pd.DataFrame(data)

        with ExcelExporter(output_file) as exporter:
            exporter.write_dataframe(
                df=df, sheet_name="Data", include_index=False, auto_width=True
            )

        # Verify file was created
        assert output_file.exists()

        # Read back and verify data
        result_df = pd.read_excel(output_file, sheet_name="Data")
        assert len(result_df) == 3
        assert list(result_df.columns) == [
            "Company",
            "Ticker",
            "Market Cap (M)",
            "P/E Ratio",
        ]
        assert result_df["Company"].iloc[0] == "Apple Inc"

    def test_write_dataframe_with_index(self, tmp_path):
        """Test DataFrame writing with index included."""
        output_file = tmp_path / "test_dataframe_index.xlsx"

        data = {"Value": [100, 200, 300]}
        df = pd.DataFrame(data, index=["A", "B", "C"])

        with ExcelExporter(output_file) as exporter:
            exporter.write_dataframe(df=df, sheet_name="WithIndex", include_index=True)

        # Verify file was created
        assert output_file.exists()

        # Read back with index
        result_df = pd.read_excel(output_file, sheet_name="WithIndex", index_col=0)
        assert len(result_df) == 3
        assert list(result_df.index) == ["A", "B", "C"]

    def test_write_multiple_sheets(self, tmp_path):
        """Test writing multiple DataFrames to different sheets."""
        output_file = tmp_path / "test_multi_sheet.xlsx"

        df1 = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df2 = pd.DataFrame({"X": [10, 20], "Y": [30, 40]})

        with ExcelExporter(output_file) as exporter:
            exporter.write_dataframe(df1, sheet_name="Sheet1")
            exporter.write_dataframe(df2, sheet_name="Sheet2")

        # Verify file was created
        assert output_file.exists()

        # Verify both sheets exist
        xl_file = pd.ExcelFile(output_file)
        assert "Sheet1" in xl_file.sheet_names
        assert "Sheet2" in xl_file.sheet_names

        # Verify data in each sheet
        result_df1 = pd.read_excel(output_file, sheet_name="Sheet1")
        result_df2 = pd.read_excel(output_file, sheet_name="Sheet2")
        assert len(result_df1) == 3
        assert len(result_df2) == 2
