"""Tests for Mermaid parser."""

import pytest

from blockbom import parse_mermaid
from blockbom.exceptions import InvalidDiagramError
from blockbom.models import NodeShape


class TestParseDirection:
    """Tests for diagram direction parsing."""

    def test_parse_flowchart_lr(self):
        diagram = parse_mermaid("flowchart LR\n    A --> B")
        assert diagram.direction == "LR"

    def test_parse_flowchart_td(self):
        diagram = parse_mermaid("flowchart TD\n    A --> B")
        assert diagram.direction == "TD"

    def test_parse_graph_tb(self):
        diagram = parse_mermaid("graph TB\n    A --> B")
        assert diagram.direction == "TB"

    def test_invalid_diagram_raises(self):
        with pytest.raises(InvalidDiagramError):
            parse_mermaid("not a valid diagram")


class TestParseNodes:
    """Tests for node parsing."""

    def test_simple_rectangle_node(self):
        diagram = parse_mermaid('flowchart LR\n    A["Test Node"]')
        assert "A" in diagram.nodes
        assert diagram.nodes["A"].label == "Test Node"
        assert diagram.nodes["A"].shape == NodeShape.RECTANGLE

    def test_rhombus_node(self):
        diagram = parse_mermaid('flowchart LR\n    A{"Decision"}')
        assert diagram.nodes["A"].label == "Decision"
        assert diagram.nodes["A"].shape == NodeShape.RHOMBUS

    def test_rounded_node(self):
        diagram = parse_mermaid('flowchart LR\n    A("Rounded")')
        assert diagram.nodes["A"].shape == NodeShape.ROUNDED

    def test_extended_syntax_with_label(self):
        content = 'flowchart LR\n    A@{ label: "Extended Node" }'
        diagram = parse_mermaid(content)
        assert diagram.nodes["A"].label == "Extended Node"

    def test_extended_syntax_strips_html(self):
        content = 'flowchart LR\n    A@{ label: "<span>Current Monitor </span>INA238" }'
        diagram = parse_mermaid(content)
        assert diagram.nodes["A"].label == "Current Monitor INA238"

    def test_extended_syntax_with_shape(self):
        content = 'flowchart LR\n    A@{ label: "Test", shape: rounded }'
        diagram = parse_mermaid(content)
        assert diagram.nodes["A"].shape == NodeShape.ROUNDED

    def test_node_without_quotes(self):
        diagram = parse_mermaid("flowchart LR\n    A[Simple Text]")
        assert diagram.nodes["A"].label == "Simple Text"


class TestParseEdges:
    """Tests for edge parsing."""

    def test_simple_edge(self):
        diagram = parse_mermaid("flowchart LR\n    A --> B")
        assert len(diagram.edges) == 1
        assert diagram.edges[0].source_id == "A"
        assert diagram.edges[0].target_id == "B"
        assert diagram.edges[0].label is None

    def test_edge_with_pipe_label(self):
        diagram = parse_mermaid("flowchart LR\n    A -->|label| B")
        assert diagram.edges[0].label == "label"

    def test_edge_with_text_label(self):
        diagram = parse_mermaid("flowchart LR\n    A -- 15 V --> B")
        assert diagram.edges[0].label == "15 V"

    def test_multiple_targets(self):
        diagram = parse_mermaid("flowchart LR\n    A --> B & C & D")
        assert len(diagram.edges) == 3
        targets = {e.target_id for e in diagram.edges}
        assert targets == {"B", "C", "D"}

    def test_inline_node_definition(self):
        diagram = parse_mermaid('flowchart LR\n    A --> B["New Node"]')
        assert "B" in diagram.nodes
        assert diagram.nodes["B"].label == "New Node"


class TestParseSubgraphs:
    """Tests for subgraph parsing."""

    def test_simple_subgraph(self):
        content = '''flowchart LR
            subgraph s1["Assembly"]
                A["Part 1"]
                B["Part 2"]
            end
        '''
        diagram = parse_mermaid(content)
        assert len(diagram.subgraphs) == 1
        assert diagram.subgraphs[0].title == "Assembly"
        assert diagram.subgraphs[0].id == "s1"

    def test_subgraph_contains_nodes(self):
        content = '''flowchart LR
            subgraph s1["Assembly"]
                A["Part 1"]
                B["Part 2"]
            end
        '''
        diagram = parse_mermaid(content)
        assert "A" in diagram.subgraphs[0].node_ids
        assert "B" in diagram.subgraphs[0].node_ids

    def test_nodes_outside_subgraph_are_root(self):
        content = '''flowchart LR
            subgraph s1["Assembly"]
                A["Part 1"]
            end
            C["External Part"]
        '''
        diagram = parse_mermaid(content)
        assert "C" in diagram.root_node_ids
        assert "A" not in diagram.root_node_ids


class TestYAMLFrontmatter:
    """Tests for YAML frontmatter handling."""

    def test_strips_frontmatter(self):
        content = '''---
config:
  theme: redux
---
flowchart LR
    A["Test"]
'''
        diagram = parse_mermaid(content)
        assert "A" in diagram.nodes
        assert diagram.direction == "LR"
