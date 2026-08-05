"""Tests for the editor API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blockbom.project import load_project
from blockbom.server import create_app

PROJECT_YAML = '''\
blockbom: 1
name: "Editor Widget"
components:
  - id: board
    name: "Board"
    qty: 2
    children:
      - id: mcu
        name: "MCU"
        part: "MCU-1"
parts:
  "MCU-1":
    cost: 5.00
    weight_g: 10
'''


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(PROJECT_YAML, encoding="utf-8")
    return path


@pytest.fixture
def client(project_path: Path) -> TestClient:
    return TestClient(create_app(project_path))


class TestGetProject:
    def test_returns_project_and_derived_data(self, client):
        data = client.get("/api/project").json()
        assert data["project"]["name"] == "Editor Widget"
        assert data["problems"] == []
        assert data["rollup"]["total_cost"] == 10.0
        assert data["rollup"]["part_count"] == 2
        assert data["consolidated"][0]["part_number"] == "MCU-1"
        assert data["consolidated"][0]["total_qty"] == 2
        assert data["mermaid"].startswith("flowchart TD")

    def test_connections_use_from_to_aliases(self, project_path):
        project_path.write_text(
            PROJECT_YAML + 'connections:\n  - {from: board, to: mcu, label: "x"}\n',
            encoding="utf-8",
        )
        data = TestClient(create_app(project_path)).get("/api/project").json()
        connection = data["project"]["connections"][0]
        assert connection["from"] == "board"
        assert connection["to"] == "mcu"

    def test_broken_yaml_gives_422(self, project_path, client):
        project_path.write_text("components: [unclosed", encoding="utf-8")
        assert client.get("/api/project").status_code == 422


class TestPutProject:
    def test_roundtrip_edit_persists(self, client, project_path):
        data = client.get("/api/project").json()
        project = data["project"]
        project["components"][0]["qty"] = 3

        response = client.put("/api/project", json=project)
        assert response.status_code == 200
        assert response.json()["rollup"]["total_cost"] == 15.0

        # Persisted to disk through the models
        reloaded = load_project(project_path)
        assert reloaded.components[0].qty == 3

    def test_dangling_part_ref_saves_but_reports_problem(self, client):
        project = client.get("/api/project").json()["project"]
        project["components"][0]["children"][0]["part"] = "GHOST"
        response = client.put("/api/project", json=project)
        assert response.status_code == 200
        assert any("GHOST" in p for p in response.json()["problems"])

    def test_schema_invalid_body_rejected_and_not_saved(self, client, project_path):
        before = project_path.read_text()
        response = client.put(
            "/api/project", json={"name": "X", "components": [{"id": "a"}]}
        )
        assert response.status_code == 422
        assert project_path.read_text() == before

    def test_part_number_survives_api_roundtrip(self, client, project_path):
        project = client.get("/api/project").json()["project"]
        project["parts"]["0402"] = {"cost": 0.01}
        project["components"][0]["children"][0]["part"] = "0402"
        response = client.put("/api/project", json=project)
        assert response.status_code == 200
        assert load_project(project_path).components[0].children[0].part == "0402"
