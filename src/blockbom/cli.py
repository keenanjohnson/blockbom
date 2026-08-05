"""Command-line interface for blockbom."""

import argparse
import sys
from pathlib import Path

from .exceptions import BlockBomError
from .export import (
    export_consolidated_csv,
    export_indented_csv,
    export_mermaid,
    export_xlsx,
)
from .importer import diagram_to_project
from .metadata import MetadataLoader
from .parser import MermaidParser
from .project import load_project, save_project, validate_project

INIT_TEMPLATE = """\
blockbom: 1
name: "My Prototype"

# The hierarchy of your design. Components may nest via `children`
# and reference the parts library via `part`. `qty` defaults to 1.
components:
  - id: enclosure
    name: "Main Enclosure"
    children:
      - id: psu
        name: "Power Supply"
        part: "PS-12V-5A"
      - id: mcu
        name: "Controller"
      - id: screws
        name: "Lid Screws"
        part: "M3-8MM"
        qty: 4

# Block-diagram edges (drawn in the diagram, not part of BOM math).
connections:
  - {from: psu, to: mcu, label: "12V"}

# Part library, keyed by part number. Quote numeric-looking part numbers.
parts:
  "PS-12V-5A":
    description: "12V 5A power supply"
    supplier: "Digi-Key"
    link: "https://example.com"
    cost: 25.99
    weight_g: 180
  "M3-8MM":
    description: "M3x8 socket head screw"
    cost: 0.08
    weight_g: 1.2
"""


def cmd_init(args: argparse.Namespace) -> int:
    """Create a starter project.yaml."""
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"error: {path} already exists (use --force to overwrite)", file=sys.stderr)
        return 1
    path.write_text(INIT_TEMPLATE, encoding="utf-8")
    print(f"Created {path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Convert a Mermaid diagram (plus optional parts.yaml) into a project.yaml."""
    mermaid_path = Path(args.mermaid)
    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"error: {output_path} already exists (use --force to overwrite)", file=sys.stderr)
        return 1

    diagram = MermaidParser().parse(mermaid_path.read_text(encoding="utf-8"))
    metadata = MetadataLoader().load(Path(args.parts)) if args.parts else {}
    project = diagram_to_project(diagram, metadata, name=mermaid_path.stem)
    save_project(project, output_path)

    components = project.all_components()
    print(
        f"Imported {mermaid_path} -> {output_path} "
        f"({len(components)} components, {len(project.parts)} parts)"
    )
    for problem in validate_project(project):
        print(f"warning: {problem}", file=sys.stderr)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Validate a project file."""
    project = load_project(args.project)
    problems = validate_project(project)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    components = project.all_components()
    print(f"{args.project}: OK ({len(components)} components, {len(project.parts)} parts)")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export BOMs and diagrams from a project file."""
    outputs = [args.csv, args.consolidated, args.xlsx, args.mmd]
    if not any(outputs):
        print(
            "error: nothing to export (pass at least one of --csv, --consolidated, --xlsx, --mmd)",
            file=sys.stderr,
        )
        return 1

    project = load_project(args.project)
    problems = validate_project(project)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        print("error: fix validation problems before exporting", file=sys.stderr)
        return 1

    if args.csv:
        export_indented_csv(project, args.csv, source=args.project)
        print(f"Wrote indented BOM: {args.csv}")
    if args.consolidated:
        export_consolidated_csv(project, args.consolidated, source=args.project)
        print(f"Wrote consolidated BOM: {args.consolidated}")
    if args.xlsx:
        export_xlsx(project, args.xlsx, source=args.project)
        print(f"Wrote workbook: {args.xlsx}")
    if args.mmd:
        export_mermaid(project, args.mmd)
        print(f"Wrote Mermaid diagram: {args.mmd}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Serve a live-updating preview of the project."""
    from .preview import serve_preview

    if not Path(args.project).exists():
        print(f"error: file not found: {args.project}", file=sys.stderr)
        return 1
    serve_preview(args.project, port=args.port, open_browser=not args.no_open)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blockbom",
        description="Design block-diagram + BOM combos for hardware prototypes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="create a starter project.yaml")
    p_init.add_argument("path", nargs="?", default="project.yaml", help="file to create")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing file")
    p_init.set_defaults(func=cmd_init)

    p_import = subparsers.add_parser("import", help="convert a Mermaid .mmd into a project.yaml")
    p_import.add_argument("mermaid", help="path to the .mmd file")
    p_import.add_argument("--parts", help="optional parts.yaml metadata file")
    p_import.add_argument("-o", "--output", default="project.yaml", help="output project file")
    p_import.add_argument("--force", action="store_true", help="overwrite an existing output file")
    p_import.set_defaults(func=cmd_import)

    p_check = subparsers.add_parser("check", help="validate a project file")
    p_check.add_argument("project", help="path to project.yaml")
    p_check.set_defaults(func=cmd_check)

    p_export = subparsers.add_parser("export", help="export BOMs and diagrams")
    p_export.add_argument("project", help="path to project.yaml")
    p_export.add_argument("--csv", help="write the indented (hierarchical) BOM CSV here")
    p_export.add_argument("--consolidated", help="write the consolidated BOM CSV here")
    p_export.add_argument("--xlsx", help="write an Excel workbook here")
    p_export.add_argument("--mmd", help="write the Mermaid diagram here")
    p_export.set_defaults(func=cmd_export)

    p_watch = subparsers.add_parser("watch", help="live preview: diagram + BOM in the browser")
    p_watch.add_argument("project", help="path to project.yaml")
    p_watch.add_argument("--port", type=int, default=8351, help="port to serve on")
    p_watch.add_argument("--no-open", action="store_true", help="do not open the browser")
    p_watch.set_defaults(func=cmd_watch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 1
    except BlockBomError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
