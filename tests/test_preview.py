"""Tests for the live preview server."""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from blockbom.preview import PreviewState, _make_handler, build_preview_data

PROJECT_YAML = '''\
blockbom: 1
name: "Preview Widget"
components:
  - id: a
    name: "Thing"
    part: "P-1"
parts:
  "P-1":
    cost: 2.50
    weight_g: 10
'''


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    path = tmp_path / "project.yaml"
    path.write_text(PROJECT_YAML, encoding="utf-8")
    return path


class TestBuildPreviewData:
    def test_valid_project(self, project_path):
        data = build_preview_data(project_path, 1.0)
        assert data["name"] == "Preview Widget"
        assert data["problems"] == []
        assert data["summary"]["cost"] == "2.50"
        assert data["summary"]["parts"] == "1"
        assert data["mermaid"].startswith("flowchart TD")
        assert data["bom"][0][0] == "P-1"

    def test_validation_problems_surfaced(self, project_path):
        project_path.write_text(
            PROJECT_YAML.replace('part: "P-1"', 'part: "MISSING"'), encoding="utf-8"
        )
        data = build_preview_data(project_path, 1.0)
        assert any("MISSING" in p for p in data["problems"])

    def test_broken_yaml_reports_error_not_crash(self, project_path):
        project_path.write_text("components: [unclosed", encoding="utf-8")
        data = build_preview_data(project_path, 2.0)
        assert data["problems"]
        assert data["bom"] == []

    def test_version_passthrough(self, project_path):
        assert build_preview_data(project_path, 42.0)["version"] == 42.0


class TestHTTPServer:
    def test_serves_page_and_data(self, project_path):
        state = PreviewState(build_preview_data(project_path, 1.0))
        server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as res:
                html = res.read().decode("utf-8")
            assert "mermaid" in html

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/data.json") as res:
                data = json.loads(res.read())
            assert data["name"] == "Preview Widget"

            # Simulate a file change: state updates are visible on next fetch
            state.set(build_preview_data(project_path, 2.0))
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/data.json") as res:
                assert json.loads(res.read())["version"] == 2.0
        finally:
            server.shutdown()
