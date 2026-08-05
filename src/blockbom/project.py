"""Project file schema: load, save, and validate project.yaml files."""

from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML

from .exceptions import MetadataError

SCHEMA_VERSION = 1


class Part(BaseModel):
    """A part definition in the parts library, keyed by part number."""

    model_config = ConfigDict(extra="allow")

    description: str | None = None
    supplier: str | None = None
    supplier_pn: str | None = None
    link: str | None = None
    cost: float | None = Field(default=None, ge=0)
    weight_g: float | None = Field(default=None, ge=0)

    def extra_fields(self) -> dict[str, Any]:
        """Freeform fields beyond the known schema (exported as extra BOM columns)."""
        return dict(self.model_extra or {})


class Component(BaseModel):
    """A placement in the hierarchy, optionally referencing a part."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    part: str | None = None
    qty: int = Field(default=1, ge=1)
    # Inline ad-hoc values for components with no part (yet)
    cost: float | None = Field(default=None, ge=0)
    weight_g: float | None = Field(default=None, ge=0)
    link: str | None = None
    children: list["Component"] = Field(default_factory=list)

    def walk(self) -> "list[Component]":
        """This component and all descendants, depth-first."""
        result = [self]
        for child in self.children:
            result.extend(child.walk())
        return result


class Connection(BaseModel):
    """A block-diagram edge between two components (not part of BOM math)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    source: str = Field(alias="from")
    target: str = Field(alias="to")
    label: str | None = None


class Project(BaseModel):
    """A complete blockbom project."""

    model_config = ConfigDict(extra="forbid")

    blockbom: int = SCHEMA_VERSION
    name: str
    components: list[Component] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    parts: dict[str, Part] = Field(default_factory=dict)

    def all_components(self) -> list[Component]:
        """All components in the tree, depth-first."""
        result: list[Component] = []
        for component in self.components:
            result.extend(component.walk())
        return result


def _yaml() -> YAML:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 100
    return yaml


def load_project(path: Path | str) -> Project:
    """Load and schema-validate a project.yaml file.

    Raises:
        FileNotFoundError: If the file does not exist.
        MetadataError: If the YAML is malformed or fails schema validation.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        try:
            data = _yaml().load(f)
        except Exception as e:
            raise MetadataError(f"Failed to parse YAML in {path}: {e}") from e

    if data is None:
        raise MetadataError(f"{path} is empty")

    try:
        return Project.model_validate(data)
    except ValidationError as e:
        raise MetadataError(_format_validation_error(path, e)) from e


def save_project(project: Project, path: Path | str) -> None:
    """Write a project to a YAML file.

    Strings that YAML would reinterpret (e.g. part number "0402", revision
    "1.10") are quoted automatically by the emitter.
    """
    path = Path(path)
    data = _project_to_data(project)
    with open(path, "w", encoding="utf-8") as f:
        _yaml().dump(data, f)


def project_to_yaml(project: Project) -> str:
    """Render a project to a YAML string."""
    buffer = StringIO()
    _yaml().dump(_project_to_data(project), buffer)
    return buffer.getvalue()


def _project_to_data(project: Project) -> dict[str, Any]:
    """Dump a project to plain data, omitting defaults but keeping the schema version."""
    data = project.model_dump(by_alias=True, exclude_none=True, exclude_defaults=True)
    ordered: dict[str, Any] = {"blockbom": project.blockbom, "name": project.name}
    for key in ("components", "connections", "parts"):
        if data.get(key):
            ordered[key] = data[key]
    return ordered


def _format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"{path} failed schema validation:"]
    for err in error.errors():
        location = ".".join(str(part) for part in err["loc"])
        message = err["msg"]
        if err["type"] == "string_type":
            message += ' (numeric-looking values like part numbers must be quoted, e.g. "0402")'
        lines.append(f"  {location}: {message}")
    return "\n".join(lines)


def validate_project(project: Project) -> list[str]:
    """Referential checks beyond the schema. Returns a list of problems (empty = ok)."""
    problems: list[str] = []

    seen_ids: set[str] = set()
    for component in project.all_components():
        if component.id in seen_ids:
            problems.append(f"duplicate component id: {component.id!r}")
        seen_ids.add(component.id)

    for component in project.all_components():
        if component.part is not None and component.part not in project.parts:
            problems.append(
                f"component {component.id!r} references part {component.part!r} "
                "which is not in the parts library"
            )

    for connection in project.connections:
        for endpoint in (connection.source, connection.target):
            if endpoint not in seen_ids:
                problems.append(
                    f"connection {connection.source!r} -> {connection.target!r} "
                    f"references unknown component id {endpoint!r}"
                )

    return problems
