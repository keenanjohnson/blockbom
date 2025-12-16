"""
blockbom - Generate BOMs from Mermaid flowchart diagrams.

Example usage:
    from blockbom import generate_bom

    # Simple usage
    items = generate_bom("diagram.mmd", "output.csv")

    # With metadata
    items = generate_bom("diagram.mmd", "output.csv", "parts.yaml")
"""

from pathlib import Path
from typing import Optional

from .exceptions import BlockBomError, InvalidDiagramError, MetadataError, ParseError
from .exporter import CSVExporter
from .hierarchy import HierarchyBuilder
from .metadata import MetadataLoader
from .models import BOMItem, Edge, Node, ParsedDiagram, PartMetadata, Subgraph
from .parser import MermaidParser

__version__ = "0.1.0"

__all__ = [
    # Main functions
    "generate_bom",
    "parse_mermaid",
    # Models
    "BOMItem",
    "Edge",
    "Node",
    "ParsedDiagram",
    "PartMetadata",
    "Subgraph",
    # Exceptions
    "BlockBomError",
    "InvalidDiagramError",
    "MetadataError",
    "ParseError",
]


def generate_bom(
    mermaid_file: Path | str,
    output_file: Path | str,
    metadata_file: Optional[Path | str] = None,
) -> list[BOMItem]:
    """Generate a BOM CSV from a Mermaid flowchart file.

    Args:
        mermaid_file: Path to .mmd file containing the Mermaid flowchart.
        output_file: Path for the output CSV file.
        metadata_file: Optional path to .parts.yaml metadata file.

    Returns:
        List of BOMItem objects representing the generated BOM.

    Raises:
        FileNotFoundError: If the mermaid_file does not exist.
        ParseError: If the Mermaid diagram cannot be parsed.
        MetadataError: If the metadata file cannot be parsed.

    Example:
        >>> from blockbom import generate_bom
        >>> items = generate_bom("diagram.mmd", "bom.csv", "parts.yaml")
        >>> print(f"Generated BOM with {len(items)} items")
    """
    mermaid_path = Path(mermaid_file)
    output_path = Path(output_file)

    # Read and parse Mermaid diagram
    with open(mermaid_path, "r", encoding="utf-8") as f:
        content = f.read()

    diagram = parse_mermaid(content)

    # Load optional metadata
    metadata: dict[str, PartMetadata] = {}
    if metadata_file:
        loader = MetadataLoader()
        metadata = loader.load(Path(metadata_file))

    # Build hierarchy
    builder = HierarchyBuilder(diagram, metadata)
    bom_items = builder.build_bom()

    # Export to CSV
    exporter = CSVExporter()
    exporter.export(bom_items, output_path)

    return bom_items


def parse_mermaid(content: str) -> ParsedDiagram:
    """Parse Mermaid flowchart content into a structured format.

    Args:
        content: Mermaid flowchart string.

    Returns:
        ParsedDiagram object with nodes, edges, and subgraphs.

    Raises:
        ParseError: If the diagram cannot be parsed.
        InvalidDiagramError: If the diagram is not a valid flowchart.

    Example:
        >>> from blockbom import parse_mermaid
        >>> diagram = parse_mermaid('''
        ... flowchart LR
        ...     A["Component 1"] --> B["Component 2"]
        ... ''')
        >>> print(diagram.nodes["A"].label)
        Component 1
    """
    parser = MermaidParser()
    return parser.parse(content)
