"""Mermaid flowchart parser."""

import re
from typing import Optional

from .exceptions import InvalidDiagramError
from .models import Edge, Node, NodeShape, ParsedDiagram, Subgraph


class MermaidParser:
    """Parses Mermaid flowchart syntax into structured data."""

    # YAML frontmatter pattern
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)

    # Diagram type and direction
    DIAGRAM_PATTERN = re.compile(
        r"^\s*(?:graph|flowchart)\s+(TD|TB|BT|RL|LR)\s*$", re.MULTILINE
    )

    # Subgraph patterns
    SUBGRAPH_START = re.compile(
        r'^\s*subgraph\s+(\w+)(?:\s*\["([^"]+)"\])?\s*$', re.MULTILINE
    )
    SUBGRAPH_END = re.compile(r"^\s*end\s*$", re.MULTILINE)

    # HTML tag stripper
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

    # Edge patterns - order matters (more specific first)
    EDGE_PATTERNS = [
        # A -->|label| B
        re.compile(r"(\w+)\s*-->\|([^|]+)\|\s*(\w+(?:\s*&\s*\w+)*)"),
        # A -- label --> B
        re.compile(r"(\w+)\s*--\s*([^-][^>]*?)\s*-->\s*(\w+(?:\s*&\s*\w+)*)"),
        # A --> B (simple, no label)
        re.compile(r"(\w+)\s*-->\s*(\w+(?:\s*&\s*\w+)*)"),
    ]

    def parse(self, content: str) -> ParsedDiagram:
        """Parse Mermaid flowchart content into structured data."""
        # Strip YAML frontmatter
        content = self._strip_frontmatter(content)

        # Parse diagram direction
        direction = self._parse_direction(content)

        # Parse subgraphs first (to know which nodes belong where)
        subgraphs, subgraph_ranges = self._parse_subgraphs(content)

        # Parse all nodes
        nodes = self._parse_nodes(content)

        # Parse all edges
        edges = self._parse_edges(content, nodes)

        # Associate nodes with subgraphs
        self._associate_nodes_to_subgraphs(content, nodes, subgraphs, subgraph_ranges)

        # Find root-level nodes (not in any subgraph)
        nodes_in_subgraphs = set()
        for sg in subgraphs:
            nodes_in_subgraphs.update(sg.node_ids)
        root_node_ids = [nid for nid in nodes.keys() if nid not in nodes_in_subgraphs]

        return ParsedDiagram(
            direction=direction,
            nodes=nodes,
            edges=edges,
            subgraphs=subgraphs,
            root_node_ids=root_node_ids,
        )

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content."""
        return self.FRONTMATTER_PATTERN.sub("", content)

    def _parse_direction(self, content: str) -> str:
        """Extract diagram direction (TD, LR, etc.)."""
        match = self.DIAGRAM_PATTERN.search(content)
        if not match:
            raise InvalidDiagramError(
                "Could not find valid flowchart/graph declaration (e.g., 'flowchart LR')"
            )
        return match.group(1)

    def _parse_subgraphs(
        self, content: str
    ) -> tuple[list[Subgraph], list[tuple[int, int, str]]]:
        """Parse subgraph definitions and return their content ranges."""
        subgraphs: list[Subgraph] = []
        ranges: list[tuple[int, int, str]] = []  # (start, end, subgraph_id)

        # Find all subgraph starts and ends
        starts = list(self.SUBGRAPH_START.finditer(content))
        ends = list(self.SUBGRAPH_END.finditer(content))

        if not starts:
            return subgraphs, ranges

        # Match starts with ends using a stack
        stack: list[tuple[re.Match, Subgraph]] = []
        all_matches = []

        for m in starts:
            all_matches.append(("start", m.start(), m))
        for m in ends:
            all_matches.append(("end", m.start(), m))

        all_matches.sort(key=lambda x: x[1])

        for match_type, pos, match in all_matches:
            if match_type == "start":
                sg_id = match.group(1)
                sg_title = match.group(2) if match.group(2) else sg_id
                sg = Subgraph(id=sg_id, title=sg_title)
                stack.append((match, sg))
            elif match_type == "end" and stack:
                start_match, sg = stack.pop()
                subgraphs.append(sg)
                ranges.append((start_match.end(), match.start(), sg.id))

        return subgraphs, ranges

    def _parse_nodes(self, content: str) -> dict[str, Node]:
        """Parse all node definitions from content."""
        nodes: dict[str, Node] = {}

        # Process line by line for better control
        for line in content.split("\n"):
            line = line.strip()

            # Skip subgraph/end lines
            if line.startswith("subgraph") or line == "end":
                continue

            # Skip lines that are just comments
            if line.startswith("%%"):
                continue

            # Try to extract nodes from this line
            self._extract_nodes_from_line(line, nodes)

        return nodes

    def _extract_nodes_from_line(self, line: str, nodes: dict[str, Node]) -> None:
        """Extract node definitions from a single line."""
        # Extended syntax: A@{ label: "text", shape: rounded }
        extended_pattern = re.compile(r"(\w+)@\{\s*([^}]+)\s*\}")
        for match in extended_pattern.finditer(line):
            node_id = match.group(1)
            props = match.group(2)
            if node_id not in nodes:
                nodes[node_id] = self._parse_extended_node(node_id, props)

        # Standard node patterns (order matters - more specific first)
        node_patterns = [
            # Subroutine: A[["text"]]
            (re.compile(r'(\w+)\[\["([^"]+)"\]\]'), NodeShape.SUBROUTINE),
            (re.compile(r"(\w+)\[\[([^\]]+)\]\]"), NodeShape.SUBROUTINE),
            # Stadium: A(["text"])
            (re.compile(r'(\w+)\(\["([^"]+)"\]\)'), NodeShape.STADIUM),
            (re.compile(r"(\w+)\(\[([^\]]+)\]\)"), NodeShape.STADIUM),
            # Cylinder: A[("text")]
            (re.compile(r'(\w+)\[\("([^"]+)"\)\]'), NodeShape.CYLINDER),
            (re.compile(r"(\w+)\[\(([^\)]+)\)\]"), NodeShape.CYLINDER),
            # Double circle: A((("text")))
            (re.compile(r'(\w+)\(\(\("([^"]+)"\)\)\)'), NodeShape.DOUBLE_CIRCLE),
            (re.compile(r"(\w+)\(\(\(([^\)]+)\)\)\)"), NodeShape.DOUBLE_CIRCLE),
            # Circle: A(("text"))
            (re.compile(r'(\w+)\(\("([^"]+)"\)\)'), NodeShape.CIRCLE),
            (re.compile(r"(\w+)\(\(([^\)]+)\)\)"), NodeShape.CIRCLE),
            # Hexagon: A{{"text"}}
            (re.compile(r'(\w+)\{\{"([^"]+)"\}\}'), NodeShape.HEXAGON),
            (re.compile(r"(\w+)\{\{([^\}]+)\}\}"), NodeShape.HEXAGON),
            # Rhombus: A{"text"}
            (re.compile(r'(\w+)\{"([^"]+)"\}'), NodeShape.RHOMBUS),
            (re.compile(r"(\w+)\{([^\}]+)\}"), NodeShape.RHOMBUS),
            # Rounded: A("text")
            (re.compile(r'(\w+)\("([^"]+)"\)'), NodeShape.ROUNDED),
            (re.compile(r"(\w+)\(([^\)]+)\)"), NodeShape.ROUNDED),
            # Rectangle: A["text"] - most common
            (re.compile(r'(\w+)\["([^"]+)"\]'), NodeShape.RECTANGLE),
            (re.compile(r"(\w+)\[([^\]]+)\]"), NodeShape.RECTANGLE),
        ]

        for pattern, shape in node_patterns:
            for match in pattern.finditer(line):
                node_id = match.group(1)
                label = match.group(2)
                # Don't overwrite if already parsed (extended syntax takes priority)
                if node_id not in nodes:
                    # Strip HTML tags from label
                    clean_label = self._strip_html(label)
                    nodes[node_id] = Node(id=node_id, label=clean_label, shape=shape)

    def _parse_extended_node(self, node_id: str, props: str) -> Node:
        """Parse A@{ label: "text", shape: rounded } syntax."""
        # Extract label - handle escaped quotes within the label
        # Match label: " followed by content (including escaped quotes) until unescaped "
        label_match = re.search(r'label:\s*"((?:[^"\\]|\\.)*)"', props)
        if label_match:
            label = label_match.group(1)
            # Unescape any escaped quotes
            label = label.replace('\\"', '"')
        else:
            label = node_id

        # Strip HTML tags
        label = self._strip_html(label)

        # Extract shape
        shape = NodeShape.RECTANGLE
        shape_match = re.search(r"shape:\s*(\w+)", props)
        if shape_match:
            shape_name = shape_match.group(1).lower()
            try:
                shape = NodeShape(shape_name)
            except ValueError:
                shape = NodeShape.RECTANGLE

        return Node(id=node_id, label=label, shape=shape)

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        return self.HTML_TAG_PATTERN.sub("", text).strip()

    def _parse_edges(self, content: str, nodes: dict[str, Node]) -> list[Edge]:
        """Parse all edge definitions from content."""
        edges: list[Edge] = []
        seen_edges: set[tuple[str, str]] = set()

        for line in content.split("\n"):
            line = line.strip()

            # Skip non-edge lines
            if "-->" not in line:
                continue

            for pattern in self.EDGE_PATTERNS:
                for match in pattern.finditer(line):
                    groups = match.groups()

                    if len(groups) == 3:
                        # Pattern with label: source, label, targets
                        source = groups[0]
                        label = groups[1].strip()
                        targets_str = groups[2]
                    else:
                        # Pattern without label: source, targets
                        source = groups[0]
                        label = None
                        targets_str = groups[1]

                    # Handle multiple targets (A --> B & C & D)
                    targets = [t.strip() for t in targets_str.split("&")]

                    for target in targets:
                        if not target:
                            continue

                        # Also capture inline node definitions from edges
                        # e.g., n3 --> n7["LED 1"]
                        inline_match = re.match(r'(\w+)\["([^"]+)"\]', target)
                        if inline_match:
                            target_id = inline_match.group(1)
                            target_label = inline_match.group(2)
                            if target_id not in nodes:
                                nodes[target_id] = Node(
                                    id=target_id,
                                    label=self._strip_html(target_label),
                                    shape=NodeShape.RECTANGLE,
                                )
                            target = target_id
                        else:
                            # Check for other inline shapes
                            for shape_pattern, shape in [
                                (r'(\w+)\{"([^"]+)"\}', NodeShape.RHOMBUS),
                                (r'(\w+)\("([^"]+)"\)', NodeShape.ROUNDED),
                            ]:
                                inline = re.match(shape_pattern, target)
                                if inline:
                                    target_id = inline.group(1)
                                    target_label = inline.group(2)
                                    if target_id not in nodes:
                                        nodes[target_id] = Node(
                                            id=target_id,
                                            label=self._strip_html(target_label),
                                            shape=shape,
                                        )
                                    target = target_id
                                    break

                        edge_key = (source, target)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append(Edge(source_id=source, target_id=target, label=label))

        return edges

    def _associate_nodes_to_subgraphs(
        self,
        content: str,
        nodes: dict[str, Node],
        subgraphs: list[Subgraph],
        ranges: list[tuple[int, int, str]],
    ) -> None:
        """Associate nodes with their parent subgraphs based on content position."""
        # Create a map of subgraph_id to subgraph
        sg_map = {sg.id: sg for sg in subgraphs}

        for start, end, sg_id in ranges:
            subgraph_content = content[start:end]

            # Find node IDs mentioned in this subgraph's content
            for node_id in nodes.keys():
                # Check if this node is defined within the subgraph
                # Look for the node ID followed by node syntax or at line start
                pattern = re.compile(rf"^\s*{re.escape(node_id)}[\[@\[\(\{{]", re.MULTILINE)
                if pattern.search(subgraph_content):
                    if node_id not in sg_map[sg_id].node_ids:
                        sg_map[sg_id].node_ids.append(node_id)
