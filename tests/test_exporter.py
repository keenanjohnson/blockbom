"""Tests for CSV exporter."""

from blockbom.exporter import CSVExporter
from blockbom.models import BOMItem


class TestCSVExporter:
    """Tests for CSV export functionality."""

    def test_export_to_string(self):
        items = [
            BOMItem(level=0, quantity=1, description="Assembly"),
            BOMItem(level=1, quantity=2, description="Part A", part_number="P001"),
        ]
        exporter = CSVExporter()
        csv_string = exporter.to_string(items)

        lines = csv_string.strip().split("\n")
        assert len(lines) == 3  # Header + 2 items

        # Check header
        assert "Level" in lines[0]
        assert "Qty" in lines[0]
        assert "Description" in lines[0]

    def test_export_with_cost(self):
        items = [
            BOMItem(
                level=0,
                quantity=1,
                description="Part",
                part_number="P001",
                cost=5.99,
            )
        ]
        exporter = CSVExporter()
        csv_string = exporter.to_string(items)

        assert "5.99" in csv_string

    def test_export_without_cost(self):
        items = [
            BOMItem(
                level=0,
                quantity=1,
                description="Part",
                cost=None,
            )
        ]
        exporter = CSVExporter()
        csv_string = exporter.to_string(items)

        # Last field should be empty, not "None"
        lines = csv_string.strip().split("\n")
        # Data row should end with empty cost
        assert "None" not in lines[1]

    def test_headers_order(self):
        exporter = CSVExporter()
        assert exporter.HEADERS == [
            "Level",
            "Qty",
            "Description",
            "Part Number",
            "Purchase Link",
            "Cost",
        ]
