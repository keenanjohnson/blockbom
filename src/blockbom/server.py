"""FastAPI backend for the visual editor (`blockbom edit`).

Requires the `edit` extra: pip install blockbom[edit]
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .export import emit_mermaid
from .project import Project, load_project, save_project, validate_project
from .rollup import consolidated_bom, indented_bom, project_rollup

STATIC_DIR = Path(__file__).parent / "_static"


def project_payload(project: Project) -> dict[str, Any]:
    """The full editor payload: project data plus everything derived from it."""
    rollup = project_rollup(project)
    return {
        "project": project.model_dump(by_alias=True, exclude_none=True),
        "problems": validate_project(project),
        "rollup": {
            "total_cost": rollup.total_cost,
            "cost_complete": rollup.cost_complete,
            "total_weight_g": rollup.total_weight_g,
            "weight_complete": rollup.weight_complete,
            "part_count": rollup.part_count,
        },
        "consolidated": [
            {
                "part_number": row.part_number,
                "name": row.name,
                "total_qty": row.total_qty,
                "supplier": row.supplier,
                "unit_cost": row.unit_cost,
                "extended_cost": row.extended_cost,
                "unit_weight_g": row.unit_weight_g,
                "extended_weight_g": row.extended_weight_g,
            }
            for row in consolidated_bom(project)
        ],
        "indented": [
            {
                "level": row.level,
                "id": row.component_id,
                "name": row.name,
                "qty": row.qty,
                "extended_qty": row.extended_qty,
                "part_number": row.part_number,
            }
            for row in indented_bom(project)
        ],
        "mermaid": emit_mermaid(project),
    }


def create_app(project_path: Path | str) -> FastAPI:
    """Build the editor app serving (and persisting) one project file."""
    path = Path(project_path)
    app = FastAPI(title="blockbom editor")

    @app.get("/api/project")
    def get_project() -> dict[str, Any]:
        try:
            project = load_project(path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        return project_payload(project)

    @app.put("/api/project")
    def put_project(body: dict[str, Any]) -> dict[str, Any]:
        try:
            project = Project.model_validate(body)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors()) from e
        save_project(project, path)
        return project_payload(project)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def serve_editor(project_path: Path | str, port: int = 8352, open_browser: bool = True) -> None:
    """Run the editor server until interrupted (blocking)."""
    import threading
    import webbrowser

    import uvicorn

    app = create_app(project_path)
    url = f"http://127.0.0.1:{port}/"
    print(f"Editing {project_path} — editor at {url} (Ctrl-C to stop)")
    if not STATIC_DIR.is_dir():
        print(
            "warning: frontend assets not found; only the API is served "
            "(run the frontend dev server or reinstall blockbom)"
        )
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
