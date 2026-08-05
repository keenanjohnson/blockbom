# Changelog

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
