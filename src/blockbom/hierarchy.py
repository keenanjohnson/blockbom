"""Hierarchy builder for generating BOM from parsed diagram."""

from collections import Counter

from .models import BOMItem, ParsedDiagram, PartMetadata, Subgraph


class HierarchyBuilder:
    """Builds hierarchical BOM from parsed diagram."""

    def __init__(
        self,
        diagram: ParsedDiagram,
        metadata: dict[str, PartMetadata] | None = None,
    ):
        self.diagram = diagram
        self.metadata = metadata or {}

    def build_bom(self) -> list[BOMItem]:
        """Generate flat BOM list with hierarchy levels.

        Returns:
            List of BOMItem objects representing the hierarchical BOM.
        """
        bom_items: list[BOMItem] = []

        # Count node references (for quantity)
        quantities = self._count_quantities()

        # Process subgraphs first (they become parent assemblies)
        for subgraph in self.diagram.subgraphs:
            bom_items.extend(self._process_subgraph(subgraph, 0, quantities))

        # Process root-level nodes (not in any subgraph)
        for node_id in self.diagram.root_node_ids:
            bom_items.append(self._create_bom_item(node_id, 0, quantities))

        return bom_items

    def _count_quantities(self) -> dict[str, int]:
        """Count how many times each node appears as a unique component.

        For now, each node is counted as quantity 1.
        Future enhancement: could track if same part appears multiple times.
        """
        quantities: dict[str, int] = Counter()

        # Default quantity is 1 for all nodes
        for node_id in self.diagram.nodes:
            quantities[node_id] = 1

        # Subgraphs also get quantity 1
        for subgraph in self.diagram.subgraphs:
            quantities[subgraph.id] = 1

        return quantities

    def _process_subgraph(
        self,
        subgraph: Subgraph,
        level: int,
        quantities: dict[str, int],
    ) -> list[BOMItem]:
        """Recursively process subgraph and its contents."""
        items: list[BOMItem] = []

        # Subgraph itself as a BOM item (assembly/grouping)
        meta = self.metadata.get(subgraph.id, PartMetadata())
        items.append(
            BOMItem(
                level=level,
                quantity=quantities.get(subgraph.id, 1),
                description=subgraph.title,
                part_number=meta.part_number or "",
                purchase_link=meta.link or "",
                cost=meta.cost,
            )
        )

        # Child nodes at level + 1
        for node_id in subgraph.node_ids:
            items.append(self._create_bom_item(node_id, level + 1, quantities))

        # Nested subgraphs at level + 1
        for child_subgraph in subgraph.children:
            items.extend(self._process_subgraph(child_subgraph, level + 1, quantities))

        return items

    def _create_bom_item(
        self,
        node_id: str,
        level: int,
        quantities: dict[str, int],
    ) -> BOMItem:
        """Create a BOM item from a node."""
        node = self.diagram.nodes.get(node_id)
        if node is None:
            # Node referenced but not defined - use ID as label
            label = node_id
        else:
            label = node.label

        meta = self.metadata.get(node_id, PartMetadata())

        return BOMItem(
            level=level,
            quantity=quantities.get(node_id, 1),
            description=label,
            part_number=meta.part_number or "",
            purchase_link=meta.link or "",
            cost=meta.cost,
        )
