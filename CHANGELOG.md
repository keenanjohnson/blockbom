# Changelog

## 0.3.0 — 2026-08-05

### Added
- **`blockbom edit` — the visual editor** (Phase 2). A local web app for
  editing a project:
  - React Flow canvas with the hierarchy as nested groups, auto-laid-out
    with ELK; drag a block into an assembly (or onto empty canvas) to
    re-parent it; draw connections between block handles; delete blocks and
    connections with the keyboard.
  - Inspector panel for the selected block (name, qty, part reference,
    inline cost/weight/link) or connection (label).
  - Table view: spreadsheet-style bulk editing of all components and the
    parts library, including part-number renames that update every reference.
  - Header shows live rollups (cost, weight, part count) and validation
    problems; Save (or Cmd/Ctrl-S) writes `project.yaml` through the same
    pydantic models the CLI uses — git remains the version mechanism.
- FastAPI backend (`GET/PUT /api/project`) behind the `blockbom[edit]`
  extra; the base install stays dependency-light.
- Frontend lives in `frontend/` (Vite + React); built assets ship inside the
  wheel, so `pip install 'blockbom[edit]'` needs no Node at install time.

## 0.2.0 — 2026-08-05

blockbom grows from a Mermaid→CSV converter into a tool for designing
block-diagram + BOM combos. See [PLAN.md](PLAN.md) for the architecture.

### Added
- **`project.yaml`** as the canonical project format: component hierarchy with
  per-placement `qty`, block-diagram connections, and a parts library keyed by
  part number (supplier, cost, weight, links, freeform extra fields).
- **CLI** (`blockbom`):
  - `init` — create a starter project.yaml
  - `import` — convert a Mermaid `.mmd` (+ optional parts.yaml) into a project
  - `check` — schema + referential validation (dangling part refs, duplicate
    ids, unknown connection endpoints)
  - `export` — indented CSV, consolidated CSV, XLSX workbook, Mermaid diagram
  - `watch` — live browser preview (diagram, rollups, BOM) that reloads on save
- **Rollups**: extended quantities multiply through the hierarchy; cost/weight
  totals per assembly and per project; missing data reported as
  `>= X (incomplete)` instead of silently zero.
- **Consolidated BOM**: flat view grouped by part number with summed
  quantities — the sheet you send a supplier.
- **Export stamps**: every export carries project name, date, and the git
  revision of the project file's repo (`-dirty` when uncommitted).
- Python API: `load_project`, `save_project`, `validate_project`,
  `indented_bom`, `consolidated_bom`, `project_rollup`, exporters.

### Fixed
- Parser: nested subgraphs now record parent/child relationships; nodes are
  assigned to their innermost subgraph only (previously duplicated across
  levels); labeled edges with inline-defined source nodes parse correctly; more
  general edge patterns no longer re-match fragments of already-parsed edges.

### Unchanged
- `generate_bom()` and `parse_mermaid()` keep their v0.1.0 behavior.

## 0.1.0

Initial release: Mermaid flowchart → hierarchical CSV BOM with optional YAML
part metadata.
