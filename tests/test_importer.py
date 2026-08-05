"""Tests for Mermaid -> project import."""

from pathlib import Path

from blockbom import generate_bom, parse_mermaid
from blockbom.importer import diagram_to_project
from blockbom.metadata import MetadataLoader
from blockbom.models import PartMetadata
from blockbom.project import Component, Project, validate_project

EXAMPLES = Path(__file__).parent.parent / "examples"


class TestImport:
    def test_flat_nodes_become_components(self):
        diagram = parse_mermaid('''flowchart LR
            A["Power Supply"]
            B["Controller"]
        ''')
        project = diagram_to_project(diagram)
        assert [c.id for c in project.components] == ["A", "B"]
        assert project.components[0].name == "Power Supply"

    def test_subgraph_becomes_parent_component(self):
        diagram = parse_mermaid('''flowchart LR
            subgraph s1["Assembly"]
                A["Part 1"]
                B["Part 2"]
            end
            C["Loose Part"]
        ''')
        project = diagram_to_project(diagram)
        assembly = project.components[0]
        assert assembly.id == "s1"
        assert assembly.name == "Assembly"
        assert {c.id for c in assembly.children} == {"A", "B"}
        assert project.components[1].id == "C"

    def test_nested_subgraphs_nest_components(self):
        diagram = parse_mermaid('''flowchart TD
            subgraph outer["Outer Assembly"]
                A["Outer Part"]
                subgraph inner["Inner Assembly"]
                    B["Inner Part"]
                end
            end
        ''')
        project = diagram_to_project(diagram)
        assert len(project.components) == 1
        outer = project.components[0]
        assert outer.id == "outer"
        child_ids = {c.id for c in outer.children}
        assert child_ids == {"A", "inner"}
        inner = next(c for c in outer.children if c.id == "inner")
        assert [c.id for c in inner.children] == ["B"]
        # Inner part must not be duplicated at the outer level
        all_ids = [c.id for c in project.all_components()]
        assert all_ids.count("B") == 1

    def test_edges_become_connections(self):
        diagram = parse_mermaid('''flowchart LR
            A["PSU"]
            B["MCU"]
            A -- 12V --> B
        ''')
        project = diagram_to_project(diagram)
        assert len(project.connections) == 1
        assert project.connections[0].source == "A"
        assert project.connections[0].target == "B"
        assert project.connections[0].label == "12V"

    def test_metadata_with_part_number_builds_parts_library(self):
        diagram = parse_mermaid('''flowchart LR
            A["Resistor"]
        ''')
        metadata = {"A": PartMetadata(part_number="R1K", link="https://x.com", cost=0.05)}
        project = diagram_to_project(diagram, metadata)
        assert project.components[0].part == "R1K"
        assert project.parts["R1K"].cost == 0.05
        assert project.parts["R1K"].link == "https://x.com"
        assert project.parts["R1K"].description == "Resistor"

    def test_metadata_without_part_number_becomes_inline_fields(self):
        diagram = parse_mermaid('''flowchart LR
            A["Bracket"]
        ''')
        metadata = {"A": PartMetadata(link="https://y.com", cost=3.50)}
        project = diagram_to_project(diagram, metadata)
        assert project.components[0].part is None
        assert project.components[0].cost == 3.50
        assert project.components[0].link == "https://y.com"
        assert project.parts == {}

    def test_shared_part_number_deduplicated(self):
        diagram = parse_mermaid('''flowchart LR
            A["Screw A"]
            B["Screw B"]
        ''')
        metadata = {
            "A": PartMetadata(part_number="M3-8MM", cost=0.08),
            "B": PartMetadata(part_number="M3-8MM", cost=0.08),
        }
        project = diagram_to_project(diagram, metadata)
        assert list(project.parts.keys()) == ["M3-8MM"]
        assert project.components[0].part == "M3-8MM"
        assert project.components[1].part == "M3-8MM"

    def test_undefined_edge_endpoint_gets_component(self):
        diagram = parse_mermaid('''flowchart LR
            A --> B
        ''')
        project = diagram_to_project(diagram)
        ids = {c.id for c in project.all_components()}
        assert {"A", "B"} <= ids
        assert validate_project(project) == []

    def test_imported_project_validates_clean(self):
        content = (EXAMPLES / "sample.mmd").read_text(encoding="utf-8")
        metadata = MetadataLoader().load(EXAMPLES / "sample.parts.yaml")
        project = diagram_to_project(parse_mermaid(content), metadata, name="sample")
        assert validate_project(project) == []


class TestV010Compat:
    """Importing sample.mmd must preserve v0.1.0 BOM structure and metadata."""

    def _indented_rows(self, project: Project) -> list[tuple[int, str, str, str, float | None]]:
        rows: list[tuple[int, str, str, str, float | None]] = []

        def visit(component: Component, level: int) -> None:
            part = project.parts.get(component.part) if component.part else None
            rows.append(
                (
                    level,
                    component.name,
                    component.part or "",
                    (part.link if part else component.link) or "",
                    part.cost if part else component.cost,
                )
            )
            for child in component.children:
                visit(child, level + 1)

        for component in project.components:
            visit(component, 0)
        return rows

    def test_sample_import_matches_generate_bom(self, tmp_path):
        items = generate_bom(
            EXAMPLES / "sample.mmd",
            tmp_path / "bom.csv",
            EXAMPLES / "sample.parts.yaml",
        )
        expected = [
            (i.level, i.description, i.part_number, i.purchase_link, i.cost) for i in items
        ]

        content = (EXAMPLES / "sample.mmd").read_text(encoding="utf-8")
        metadata = MetadataLoader().load(EXAMPLES / "sample.parts.yaml")
        project = diagram_to_project(parse_mermaid(content), metadata, name="sample")

        assert self._indented_rows(project) == expected
