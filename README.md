# blockbom

Design block-diagram + BOM combos for hardware prototypes, fast.

Describe your design in one `project.yaml` — the component hierarchy, the
connections between blocks, and a parts library with costs and weights. blockbom
gives you a live diagram preview while you edit, computes quantity/cost/weight
rollups, and exports versioned BOMs to Excel and CSV.

```
project.yaml  ──►  blockbom  ──►  live preview (diagram + rollups)
                              ──►  indented & consolidated BOM (CSV / XLSX)
                              ──►  Mermaid diagram for docs
```

Version history is git: the project file is plain YAML, and every export is
stamped with the git revision it came from.

## Installation

```bash
# Using uv
uv add blockbom

# Using pip
pip install blockbom
```

## Quick start

```bash
blockbom init                    # create a starter project.yaml
blockbom watch project.yaml      # live diagram + BOM preview in the browser
# ...edit project.yaml in your editor; the preview updates on save...
blockbom export project.yaml --xlsx bom.xlsx
```

Already have a Mermaid diagram? Import it:

```bash
blockbom import diagram.mmd --parts parts.yaml -o project.yaml
```

## The project file

```yaml
blockbom: 1
name: "Widget Prototype"

components:                # the hierarchy; qty defaults to 1
  - id: enclosure
    name: "Main Enclosure"
    part: "ENC-100"        # optional reference into the parts library
    children:
      - id: psu
        name: "Power Supply"
        part: "PS-12V-5A"
      - id: screws
        name: "Lid Screws"
        part: "M3-8MM"
        qty: 4
  - id: display
    name: "External Display"   # undecided parts are fine

connections:               # block-diagram edges (not part of BOM math)
  - {from: psu, to: display, label: "12V"}

parts:                     # part library, keyed by part number
  "ENC-100":
    description: "1L enclosure"
    cost: 40.00
    weight_g: 350
  "PS-12V-5A":
    description: "12V 5A power supply"
    supplier: "Digi-Key"
    supplier_pn: "1234-ND"
    link: "https://example.com/ps"
    cost: 25.99
    weight_g: 180
  "M3-8MM":
    description: "M3x8 socket head screw"
    cost: 0.08
    weight_g: 1.2
```

Notes:

- **Quote numeric-looking part numbers** (`"0402"`, `"1.10"`) — blockbom
  rejects unquoted ones rather than let YAML silently mangle them, and keeps
  them as text in Excel exports.
- Parts may carry **any extra fields** (`mfr`, `tolerance`, ...); they become
  extra BOM columns.
- Components without a `part` can hold inline `cost` / `weight_g` / `link`
  while you're still sketching.

## Rollups

- Quantities multiply through the hierarchy: 2× board with 4× screws = 8 screws
  in the consolidated BOM.
- Assemblies roll up subtree cost and weight; the whole project gets totals.
- Missing data is visible, never silently zero: totals show
  `>= 123.40 (incomplete)` when some parts lack a cost or weight.

## Commands

| Command | What it does |
|---|---|
| `blockbom init [path]` | Create a starter project.yaml |
| `blockbom import d.mmd [--parts p.yaml] [-o out.yaml]` | Convert a Mermaid flowchart into a project |
| `blockbom check project.yaml` | Validate schema + references (dangling parts, duplicate ids) |
| `blockbom export project.yaml --xlsx bom.xlsx` | Export (also `--csv`, `--consolidated`, `--mmd`) |
| `blockbom watch project.yaml` | Live preview server (diagram, rollups, BOM) |

Exports:

- `--csv` — indented BOM: the hierarchy with levels, extended quantities, and
  per-assembly subtree rollups
- `--consolidated` — flat BOM grouped by part number with summed quantities
  and a totals row: what you hand a supplier
- `--xlsx` — workbook with Summary, Indented BOM, and Consolidated BOM sheets
- `--mmd` — the block diagram as Mermaid, for READMEs and docs

Every export is stamped with the project name, date, and git revision
(`-dirty` if the working tree has uncommitted changes), so any spreadsheet can
be traced back to the exact design state that produced it.

The `watch` preview renders the diagram with mermaid.js from a CDN, so it
needs internet access; the BOM table and rollups work offline.

## Python API

```python
from blockbom import load_project, consolidated_bom, project_rollup

project = load_project("project.yaml")
rollup = project_rollup(project)
print(f"Total cost: {rollup.total_cost:.2f} (complete: {rollup.cost_complete})")

for row in consolidated_bom(project):
    print(row.part_number, row.total_qty, row.extended_cost)
```

The original Mermaid → CSV path from v0.1.0 is unchanged:

```python
from blockbom import generate_bom

items = generate_bom("diagram.mmd", "output.csv", "parts.yaml")
```

See [examples/](examples/) for a full sample (Mermaid source, parts file, and
the imported project.yaml).

## Development

```bash
git clone https://github.com/keenanjohnson/blockbom.git
cd blockbom
uv sync --extra dev

uv run pytest            # tests
uv run mypy src/blockbom # type checking
uv run ruff check src/blockbom && uv run ruff format --check src/blockbom
```

The roadmap (visual editor, BOM diffs between git revisions, supplier API
enrichment) lives in [PLAN.md](PLAN.md).

## License

MIT
