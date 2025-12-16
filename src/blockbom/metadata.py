"""YAML metadata loader for part information."""

from pathlib import Path
from typing import Any

import yaml

from .exceptions import MetadataError
from .models import PartMetadata


class MetadataLoader:
    """Loads part metadata from YAML file."""

    def load(self, yaml_path: Path) -> dict[str, PartMetadata]:
        """Load metadata from YAML file.

        Args:
            yaml_path: Path to the YAML metadata file.

        Returns:
            Dictionary mapping node IDs to PartMetadata objects.

        Raises:
            MetadataError: If the YAML file cannot be parsed.
        """
        if not yaml_path.exists():
            return {}

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise MetadataError(f"Failed to parse YAML metadata: {e}") from e

        metadata: dict[str, PartMetadata] = {}
        for node_id, props in data.items():
            if not isinstance(props, dict):
                continue

            metadata[str(node_id)] = PartMetadata(
                part_number=props.get("part_number"),
                link=props.get("link"),
                cost=self._parse_cost(props.get("cost")),
            )

        return metadata

    def _parse_cost(self, value: Any) -> float | None:
        """Parse cost value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
