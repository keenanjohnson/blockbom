# blockbom — Project Plan & Context

**Goal:** evolve blockbom from a Mermaid→CSV converter into a tool for rapidly
designing and iterating on block-diagram + BOM combos for hardware prototypes.

**Definition of done (Phase 1):** a hardware engineer can describe a prototype in
one `project.yaml`, see a live block diagram while editing, and export a
versioned Excel/CSV BOM with cost/weight rollups — good enough to design a real
upcoming prototype with.

---

## Current state (v0.1.0)

Small pure-Python pipeline (~770 lines): Mermaid `.mmd` → parser → hierarchy →
CSV, with optional `parts.yaml` metadata (part number, link, cost). Modules:
`parser.py`, `hierarchy.py`, `models.py`, `metadata.py`, `exporter.py`.
Tests, CI, and PyPI packaging exist.

## Decisions made (with rationale)

| Decision | Choice | Why |
|---|---|---|
| Source of truth | Single `project.yaml` per project | Git-diffable (version history free from git), hand-editable, losslessly writable by a future GUI. Mermaid can't hold qty/metadata/positions and round-tripping hand-written `.mmd` is painful. |
| Mermaid's role | Import + render format only | `blockbom import` converts existing `.mmd`; Mermaid is emitted for previews/READMEs. |
| Repo strategy | Evolve this repo, no fork | Existing parser/exporter/tests survive as the import/export paths. Bump to 0.2.0; keep `generate_bom()` as a compat wrapper. |
| YAML handling | pydantic schema on load, `ruamel.yaml` for round-trip, always quote part numbers/revisions on emit | Neutralizes YAML implicit-typing bugs (`0402`→int, `1.10`→`1.1`, `NO`→False) that would end up in purchase orders. |
| Format swappability | Parse → pydantic models → emit; format touches only the edges | If a GUI becomes the primary editor, canonical format can flip to JSON with a one-time converter. |
| Diagram layout | Auto-layout (Mermaid/ELK) first; no stored coordinates | Purely derived from structure; add saved positions only if auto-layout annoys in practice. |
| Version history | Git, not app-managed snapshots | Exports are stamped with git commit hash + date for traceability. |
| Packaging | Publish from this repo; core stays light; heavy deps behind extras (`blockbom[edit]`) | Standard library-that-grows-into-a-tool pattern (Streamlit, Datasette, Jupyter). Stay 0.x until schema settles; small public API in `__init__.py`. |
| Web editor (Phase 2) | Monorepo `frontend/` (React Flow), built assets ship in the wheel, `blockbom edit` serves locally | Schema/engine/editor version together while the schema is churning. |

## Data model

Two core ideas the current code lacks:

1. **Quantities.** Every placement has a `qty` (4× M3 screws). Rollups multiply
   qty through the tree.
2. **Parts vs placements.** Part definitions live in a `parts:` library keyed by
   part number; tree nodes *reference* them. The same part used in three
   subsystems is defined once — enabling a consolidated (flat, deduplicated,
   total-qty) BOM alongside the indented one.

### Draft `project.yaml` schema

```yaml
blockbom: 1                # schema version
name: "Widget Prototype"

components:                # the hierarchy (instances/placements)
  - id: enclosure
    name: "Main Enclosure"
    part: "ENC-100"
    children:
      - id: psu
        name: "Power Supply"
        part: "PS-12V-5A"
      - id: mcu
        name: "Controller"
        part: "MCU-ARM-01"
      - id: screws
        name: "Lid Screws"
        part: "M3-8MM"
        qty: 4             # default 1
  - id: display
    name: "External Display"   # no part yet — undecided parts are fine

connections:               # block-diagram edges (not part of BOM math)
  - {from: psu, to: mcu, label: "12V"}
  - {from: mcu, to: display, label: "SPI"}

parts:                     # part library, keyed by part number
  "PS-12V-5A":
    description: "12V 5A power supply"
    supplier: "Digi-Key"
    supplier_pn: "1234-ND"
    link: "https://example.com/ps"
    cost: 25.99            # unit cost
    weight_g: 180
  "M3-8MM":
    description: "M3x8 socket head screw"
    cost: 0.08
    weight_g: 1.2
```

Notes:
- Node-level ad-hoc fields (e.g. inline `cost` on a component with no part yet)
  are allowed so early sketching isn't blocked on filling out the library.
- Extra part fields beyond the known set are preserved and exported as extra
  BOM columns (freeform metadata without schema churn).

### Rollup semantics

- **Extended qty** of a placement = product of `qty` along its path from root.
- **Assembly rollups** (computed, never stored): total cost, total weight,
  part count for each subtree. Unknown values roll up as "≥ X (incomplete)" —
  missing data must be visible, not silently zero.
- **Two BOM views:** indented (hierarchy, current CSV shape + new columns) and
  consolidated (grouped by part number, summed qty — what you send a supplier).

## Architecture

```
project.yaml ←→ core engine (pydantic models, rollups, importers/exporters)
                    ├── CLI: init, import, check, export, watch  (Phase 1)
                    └── local web editor: FastAPI + React Flow   (Phase 2)
```

Engine remains a pure library with no UI knowledge.

---

## Phase 1 — engine + CLI (the usable product)

1. **Schema + models** — pydantic models for the schema above; `ruamel` load/save
   round-trip; `blockbom check` validation (dangling part refs, duplicate ids,
   cycles).
   → verify: round-trip test (load→save is a no-op diff); validation unit tests.
2. **Mermaid import** — `blockbom import diagram.mmd [parts.yaml] -o project.yaml`
   reusing the existing parser; subgraphs → children, nodes → components,
   edges → connections.
   → verify: importing `examples/sample.mmd` + exporting CSV matches current
   v0.1.0 output (compat test); `generate_bom()` wrapper still passes existing tests.
3. **Rollup engine** — extended qty, cost/weight rollups, consolidated BOM.
   → verify: unit tests with nested-qty cases (e.g. 2× board × 4× screw = 8)
   and missing-data cases.
4. **Exporters** — indented CSV (extended), consolidated CSV, XLSX (`openpyxl`:
   one sheet per view, rollup summary), Mermaid emit. Every export stamped with
   project name, date, git commit hash (+ `-dirty` when uncommitted).
   → verify: XLSX opens in Excel/LibreOffice; stamp matches `git rev-parse`.
5. **Live preview** — `blockbom watch project.yaml`: on save, re-validate and
   re-render the diagram + BOM summary to a local HTML page that auto-refreshes.
   → verify: edit file, browser updates without manual reload.
6. **Release 0.2.0** — README rewrite around the new workflow, changelog,
   publish to PyPI.
   → verify: `pip install blockbom` in a clean venv; run the full loop on a real
   prototype (the true acceptance test: design one of the upcoming prototypes
   with it).

**Phase 1 exit = usable product:** `blockbom init` → edit `project.yaml` in
editor with `blockbom watch` preview alongside → `blockbom export --xlsx` →
commit. Iterate.

## Phase 2 — visual editor ✅ (implemented, v0.3.0)

- `blockbom edit`: FastAPI backend (behind `blockbom[edit]` extra) serving a
  React Flow canvas — nested groups mirror the hierarchy, drag-to-reparent,
  draw connections — plus a spreadsheet-style table for bulk metadata editing.
- All edits write `project.yaml` through the same models. Git stays the
  save/version mechanism. (Comment preservation on GUI saves is still open —
  saves currently re-emit canonical YAML without comments.)
- Frontend lives in `frontend/` (Vite + React + @xyflow/react + elkjs);
  built assets ship in the wheel via hatch `artifacts`.
- Auto-layout via ELK; no stored positions. Revisit only if it proves
  insufficient in use.

## Phase 3 — polish (as needed)

- `blockbom diff <rev-a> <rev-b>`: structured BOM diff between git revisions
  (parts added/removed, qty/cost deltas).
- Supplier enrichment: Octopart / Digi-Key API lookups to fill cost,
  availability, datasheet links from part numbers.
- Config for currency/units; per-project column customization.

## Non-goals (for now)

- Multi-user server / database backend
- Schematic capture or netlists — blocks and connections stay coarse-grained
- Inventory management, purchasing workflows
- App-managed version history (git does this)

## Open questions

- Connection metadata (voltage, protocol, wire gauge) — schema allows a `label`
  now; richer typed fields later if a use case appears.
- Alternates/substitute parts per placement — punt until a prototype needs it.
- Currency handling — assume single currency per project for now.
