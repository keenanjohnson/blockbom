"""Data structures for blockbom."""

from dataclasses import dataclass, field
from enum import Enum


class NodeShape(Enum):
    """Mermaid node shape types."""

    RECTANGLE = "rectangle"  # A[text]
    ROUNDED = "rounded"  # A(text)
    STADIUM = "stadium"  # A([text])
    SUBROUTINE = "subroutine"  # A[[text]]
    CYLINDER = "cylinder"  # A[(text)]
    CIRCLE = "circle"  # A((text))
    RHOMBUS = "rhombus"  # A{text}
    HEXAGON = "hexagon"  # A{{text}}
    PARALLELOGRAM = "parallelogram"  # A[/text/]
    TRAPEZOID = "trapezoid"  # A[/text\]
    DOUBLE_CIRCLE = "double_circle"  # A(((text)))


@dataclass
class Node:
    """Represents a node in the Mermaid diagram."""

    id: str
    label: str
    shape: NodeShape = NodeShape.RECTANGLE


@dataclass
class Edge:
    """Represents a connection between nodes."""

    source_id: str
    target_id: str
    label: str | None = None


@dataclass
class Subgraph:
    """Represents a subgraph container."""

    id: str
    title: str
    node_ids: list[str] = field(default_factory=list)
    children: list["Subgraph"] = field(default_factory=list)
    parent_id: str | None = None


@dataclass
class PartMetadata:
    """Metadata for a part from YAML file."""

    part_number: str | None = None
    link: str | None = None
    cost: float | None = None


@dataclass
class BOMItem:
    """A single item in the BOM output."""

    level: int
    quantity: int
    description: str
    part_number: str = ""
    purchase_link: str = ""
    cost: float | None = None


@dataclass
class ParsedDiagram:
    """Complete parsed Mermaid diagram."""

    direction: str  # "TD", "LR", etc.
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    subgraphs: list[Subgraph] = field(default_factory=list)
    root_node_ids: list[str] = field(default_factory=list)  # Nodes not in any subgraph
