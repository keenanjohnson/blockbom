"""Tests for project.yaml schema, load/save round-trip, and validation."""

import pytest

from blockbom.exceptions import MetadataError
from blockbom.project import (
    Component,
    Part,
    Project,
    load_project,
    save_project,
    validate_project,
)

SAMPLE_YAML = '''\
blockbom: 1
name: "Widget Prototype"

components:
  - id: enclosure
    name: "Main Enclosure"
    part: "ENC-100"
    children:
      - id: psu
        name: "Power Supply"
        part: "PS-12V-5A"
      - id: screws
        name: "Lid Screws"
        part: "M3-8MM"
        qty: 4
  - id: display
    name: "External Display"

connections:
  - {from: psu, to: display, label: "12V"}

parts:
  "ENC-100":
    description: "Enclosure"
    cost: 40.00
  "PS-12V-5A":
    description: "12V 5A power supply"
    supplier: "Digi-Key"
    cost: 25.99
    weight_g: 180
  "M3-8MM":
    description: "M3x8 socket head screw"
    cost: 0.08
    weight_g: 1.2
'''


@pytest.fixture
def sample_path(tmp_path):
    path = tmp_path / "project.yaml"
    path.write_text(SAMPLE_YAML, encoding="utf-8")
    return path


class TestLoad:
    def test_loads_hierarchy(self, sample_path):
        project = load_project(sample_path)
        assert project.name == "Widget Prototype"
        assert len(project.components) == 2
        enclosure = project.components[0]
        assert enclosure.id == "enclosure"
        assert len(enclosure.children) == 2
        assert enclosure.children[1].qty == 4

    def test_loads_connections_with_from_alias(self, sample_path):
        project = load_project(sample_path)
        assert project.connections[0].source == "psu"
        assert project.connections[0].target == "display"
        assert project.connections[0].label == "12V"

    def test_loads_parts_library(self, sample_path):
        project = load_project(sample_path)
        assert project.parts["PS-12V-5A"].cost == 25.99
        assert project.parts["M3-8MM"].weight_g == 1.2

    def test_extra_part_fields_preserved(self, tmp_path):
        path = tmp_path / "p.yaml"
        path.write_text(
            'blockbom: 1\nname: "P"\nparts:\n  "X-1":\n    cost: 1.0\n    mfr: "Acme"\n',
            encoding="utf-8",
        )
        project = load_project(path)
        assert project.parts["X-1"].extra_fields() == {"mfr": "Acme"}

    def test_unquoted_numeric_part_ref_rejected(self, tmp_path):
        path = tmp_path / "p.yaml"
        path.write_text(
            'blockbom: 1\nname: "P"\ncomponents:\n  - id: a\n    name: "A"\n    part: 1.10\n',
            encoding="utf-8",
        )
        with pytest.raises(MetadataError, match="quoted"):
            load_project(path)

    def test_unknown_component_field_rejected(self, tmp_path):
        path = tmp_path / "p.yaml"
        path.write_text(
            'blockbom: 1\nname: "P"\ncomponents:\n  - id: a\n    name: "A"\n    quantity: 2\n',
            encoding="utf-8",
        )
        with pytest.raises(MetadataError):
            load_project(path)

    def test_zero_qty_rejected(self, tmp_path):
        path = tmp_path / "p.yaml"
        path.write_text(
            'blockbom: 1\nname: "P"\ncomponents:\n  - id: a\n    name: "A"\n    qty: 0\n',
            encoding="utf-8",
        )
        with pytest.raises(MetadataError):
            load_project(path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_project(tmp_path / "nope.yaml")

    def test_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")
        with pytest.raises(MetadataError, match="empty"):
            load_project(path)


class TestRoundTrip:
    def test_load_save_load_is_stable(self, sample_path, tmp_path):
        project = load_project(sample_path)
        out = tmp_path / "out.yaml"
        save_project(project, out)
        reloaded = load_project(out)
        assert reloaded == project

    def test_save_is_idempotent(self, sample_path, tmp_path):
        project = load_project(sample_path)
        first = tmp_path / "first.yaml"
        save_project(project, first)
        second = tmp_path / "second.yaml"
        save_project(load_project(first), second)
        assert first.read_text() == second.read_text()

    def test_numeric_looking_part_number_survives_round_trip(self, tmp_path):
        project = Project(
            name="P",
            components=[Component(id="c", name="Cap", part="0402")],
            parts={"0402": Part(description="Capacitor"), "1.10": Part(), "NO": Part()},
        )
        path = tmp_path / "p.yaml"
        save_project(project, path)
        reloaded = load_project(path)
        assert set(reloaded.parts.keys()) == {"0402", "1.10", "NO"}
        assert reloaded.components[0].part == "0402"

    def test_default_qty_omitted_on_save(self, tmp_path):
        project = Project(name="P", components=[Component(id="a", name="A")])
        path = tmp_path / "p.yaml"
        save_project(project, path)
        assert "qty" not in path.read_text()


class TestValidate:
    def test_valid_project_has_no_problems(self, sample_path):
        assert validate_project(load_project(sample_path)) == []

    def test_dangling_part_ref(self):
        project = Project(name="P", components=[Component(id="a", name="A", part="MISSING")])
        problems = validate_project(project)
        assert len(problems) == 1
        assert "MISSING" in problems[0]

    def test_duplicate_component_id(self):
        project = Project(
            name="P",
            components=[Component(id="a", name="A"), Component(id="a", name="B")],
        )
        problems = validate_project(project)
        assert any("duplicate" in p for p in problems)

    def test_duplicate_nested_component_id(self):
        project = Project(
            name="P",
            components=[Component(id="a", name="A", children=[Component(id="a", name="B")])],
        )
        assert any("duplicate" in p for p in validate_project(project))

    def test_connection_to_unknown_id(self):
        project = Project(
            name="P",
            components=[Component(id="a", name="A")],
            connections=[{"from": "a", "to": "ghost"}],
        )
        problems = validate_project(project)
        assert any("ghost" in p for p in problems)
