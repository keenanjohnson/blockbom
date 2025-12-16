"""Tests for hierarchy builder."""

from blockbom import parse_mermaid
from blockbom.hierarchy import HierarchyBuilder
from blockbom.models import PartMetadata


class TestHierarchyBuilder:
    """Tests for BOM hierarchy building."""

    def test_simple_bom(self):
        diagram = parse_mermaid('''flowchart LR
            A["Component 1"]
            B["Component 2"]
        ''')
        builder = HierarchyBuilder(diagram)
        bom = builder.build_bom()

        assert len(bom) == 2
        assert bom[0].description == "Component 1"
        assert bom[0].level == 0
        assert bom[0].quantity == 1

    def test_subgraph_hierarchy(self):
        diagram = parse_mermaid('''flowchart LR
            subgraph s1["Assembly"]
                A["Part 1"]
                B["Part 2"]
            end
        ''')
        builder = HierarchyBuilder(diagram)
        bom = builder.build_bom()

        # Subgraph should be level 0, children level 1
        assert bom[0].description == "Assembly"
        assert bom[0].level == 0

        # Find children
        children = [item for item in bom if item.level == 1]
        assert len(children) == 2

    def test_metadata_enrichment(self):
        diagram = parse_mermaid('''flowchart LR
            A["Resistor"]
        ''')
        metadata = {
            "A": PartMetadata(
                part_number="R1K-0805",
                link="https://example.com/resistor",
                cost=0.05,
            )
        }
        builder = HierarchyBuilder(diagram, metadata)
        bom = builder.build_bom()

        assert bom[0].part_number == "R1K-0805"
        assert bom[0].purchase_link == "https://example.com/resistor"
        assert bom[0].cost == 0.05

    def test_missing_metadata_gives_empty_fields(self):
        diagram = parse_mermaid('''flowchart LR
            A["Component"]
        ''')
        builder = HierarchyBuilder(diagram, {})
        bom = builder.build_bom()

        assert bom[0].part_number == ""
        assert bom[0].purchase_link == ""
        assert bom[0].cost is None

    def test_root_nodes_at_level_zero(self):
        diagram = parse_mermaid('''flowchart LR
            subgraph s1["Inside"]
                A["Part A"]
            end
            B["Part B"]
        ''')
        builder = HierarchyBuilder(diagram)
        bom = builder.build_bom()

        # Find Part B (root node)
        part_b = next(item for item in bom if item.description == "Part B")
        assert part_b.level == 0
