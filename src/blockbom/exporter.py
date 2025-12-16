"""CSV exporter for BOM data."""

import csv
import io
from pathlib import Path

from .models import BOMItem


class CSVExporter:
    """Exports BOM to CSV format."""

    HEADERS = ["Level", "Qty", "Description", "Part Number", "Purchase Link", "Cost"]

    def export(self, bom_items: list[BOMItem], output_path: Path) -> None:
        """Export BOM items to CSV file.

        Args:
            bom_items: List of BOMItem objects to export.
            output_path: Path for the output CSV file.
        """
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.HEADERS)

            for item in bom_items:
                writer.writerow(self._item_to_row(item))

    def to_string(self, bom_items: list[BOMItem]) -> str:
        """Export BOM items to CSV string.

        Args:
            bom_items: List of BOMItem objects to export.

        Returns:
            CSV formatted string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.HEADERS)

        for item in bom_items:
            writer.writerow(self._item_to_row(item))

        return output.getvalue()

    def _item_to_row(self, item: BOMItem) -> list[str]:
        """Convert a BOMItem to a CSV row."""
        return [
            str(item.level),
            str(item.quantity),
            item.description,
            item.part_number,
            item.purchase_link,
            f"{item.cost:.2f}" if item.cost is not None else "",
        ]
