"""
blockbom - Design block-diagram + BOM combos for hardware prototypes.

A project lives in a single project.yaml (hierarchy, connections, parts
library). Load it, compute rollups, and export BOMs:

    from blockbom import load_project, indented_bom, consolidated_bom

    project = load_project("project.yaml")
    for row in consolidated_bom(project):
        print(row.part_number, row.total_qty)

The original Mermaid -> CSV path still works:

    from blockbom import generate_bom
    items = generate_bom("diagram.mmd", "output.csv", "parts.yaml")
"""

from pathlib import Path

from .exceptions import BlockBomError, InvalidDiagramError, MetadataError, ParseError
from .export import (
    emit_mermaid,
    export_consolidated_csv,
    export_indented_csv,
    export_mermaid,
    export_xlsx,
)
from .exporter import CSVExporter
from .hierarchy import HierarchyBuilder
from .importer import diagram_to_project
from .metadata import MetadataLoader
from .models import BOMItem, Edge, Node, ParsedDiagram, PartMetadata, Subgraph
from .parser import MermaidParser
from .project import (
    Component,
    Connection,
    Part,
    Project,
    load_project,
    save_project,
    validate_project,
)
from .rollup import consolidated_bom, indented_bom, project_rollup

__version__ = "0.3.0"

__all__ = [
    # Project workflow
    "Project",
    "Component",
    "Connection",
    "Part",
    "load_project",
    "save_project",
    "validate_project",
    # Rollups
    "indented_bom",
    "consolidated_bom",
    "project_rollup",
    # Import / export
    "diagram_to_project",
    "export_indented_csv",
    "export_consolidated_csv",
    "export_xlsx",
    "export_mermaid",
    "emit_mermaid",
    # Mermaid -> CSV compatibility path
    "generate_bom",
    "parse_mermaid",
    # Legacy models
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
    metadata_file: Path | str | None = None,
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
    with open(mermaid_path, encoding="utf-8") as f:
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
