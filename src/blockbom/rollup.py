"""Rollup calculations: extended quantities, cost/weight totals, BOM views.

All values are computed on demand from the project, never stored.
Missing data is tracked explicitly so rollups can be reported as
">= X (incomplete)" instead of silently reading as zero.
"""

from dataclasses import dataclass, field
from typing import Any

from .project import Component, Part, Project


@dataclass
class Rollup:
    """Subtree totals for an assembly (or the whole project)."""

    total_cost: float = 0.0
    cost_complete: bool = True
    total_weight_g: float = 0.0
    weight_complete: bool = True
    part_count: int = 0


@dataclass
class IndentedRow:
    """One row of the indented (hierarchical) BOM."""

    level: int
    component_id: str
    name: str
    qty: int
    extended_qty: int
    part_number: str
    supplier: str
    supplier_pn: str
    link: str
    unit_cost: float | None
    extended_cost: float | None
    unit_weight_g: float | None
    extended_weight_g: float | None
    is_assembly: bool
    rollup: Rollup | None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsolidatedRow:
    """One row of the consolidated (flat, deduplicated) BOM."""

    part_number: str
    name: str
    total_qty: int
    supplier: str
    supplier_pn: str
    link: str
    unit_cost: float | None
    extended_cost: float | None
    unit_weight_g: float | None
    extended_weight_g: float | None
    extra: dict[str, Any] = field(default_factory=dict)


def _resolve_part(project: Project, component: Component) -> Part | None:
    if component.part is not None:
        return project.parts.get(component.part)
    return None


def _unit_cost(project: Project, component: Component) -> float | None:
    part = _resolve_part(project, component)
    if part is not None and part.cost is not None:
        return part.cost
    return component.cost


def _unit_weight(project: Project, component: Component) -> float | None:
    part = _resolve_part(project, component)
    if part is not None and part.weight_g is not None:
        return part.weight_g
    return component.weight_g


def _is_pure_grouping(project: Project, component: Component) -> bool:
    """An assembly that only groups children, with no part/cost/weight of its own."""
    return (
        bool(component.children)
        and component.part is None
        and component.cost is None
        and component.weight_g is None
    )


def _subtree_rollup(project: Project, component: Component) -> Rollup:
    """Per-instance rollup of a component's subtree (not scaled by its own qty)."""
    rollup = Rollup()

    unit_cost = _unit_cost(project, component)
    unit_weight = _unit_weight(project, component)

    if unit_cost is not None:
        rollup.total_cost += unit_cost
    elif not _is_pure_grouping(project, component):
        rollup.cost_complete = False

    if unit_weight is not None:
        rollup.total_weight_g += unit_weight
    elif not _is_pure_grouping(project, component):
        rollup.weight_complete = False

    if not component.children:
        rollup.part_count = 1
    elif not _is_pure_grouping(project, component):
        # An assembly that is itself a part (e.g. the enclosure shell)
        rollup.part_count = 1

    for child in component.children:
        child_rollup = _subtree_rollup(project, child)
        rollup.total_cost += child.qty * child_rollup.total_cost
        rollup.total_weight_g += child.qty * child_rollup.total_weight_g
        rollup.part_count += child.qty * child_rollup.part_count
        rollup.cost_complete = rollup.cost_complete and child_rollup.cost_complete
        rollup.weight_complete = rollup.weight_complete and child_rollup.weight_complete

    return rollup


def _scale(rollup: Rollup, factor: int) -> Rollup:
    return Rollup(
        total_cost=rollup.total_cost * factor,
        cost_complete=rollup.cost_complete,
        total_weight_g=rollup.total_weight_g * factor,
        weight_complete=rollup.weight_complete,
        part_count=rollup.part_count * factor,
    )


def project_rollup(project: Project) -> Rollup:
    """Totals for the whole project."""
    rollup = Rollup()
    for component in project.components:
        sub = _subtree_rollup(project, component)
        rollup.total_cost += component.qty * sub.total_cost
        rollup.total_weight_g += component.qty * sub.total_weight_g
        rollup.part_count += component.qty * sub.part_count
        rollup.cost_complete = rollup.cost_complete and sub.cost_complete
        rollup.weight_complete = rollup.weight_complete and sub.weight_complete
    return rollup


def indented_bom(project: Project) -> list[IndentedRow]:
    """Hierarchical BOM: one row per placement, with extended quantities.

    Assembly rows carry a Rollup covering their whole subtree (scaled by
    the assembly's extended quantity).
    """
    rows: list[IndentedRow] = []

    def visit(component: Component, level: int, parent_qty: int) -> None:
        extended_qty = parent_qty * component.qty
        part = _resolve_part(project, component)
        unit_cost = _unit_cost(project, component)
        unit_weight = _unit_weight(project, component)
        is_assembly = bool(component.children)

        rows.append(
            IndentedRow(
                level=level,
                component_id=component.id,
                name=component.name,
                qty=component.qty,
                extended_qty=extended_qty,
                part_number=component.part or "",
                supplier=(part.supplier if part else None) or "",
                supplier_pn=(part.supplier_pn if part else None) or "",
                link=((part.link if part else None) or component.link) or "",
                unit_cost=unit_cost,
                extended_cost=extended_qty * unit_cost if unit_cost is not None else None,
                unit_weight_g=unit_weight,
                extended_weight_g=(extended_qty * unit_weight if unit_weight is not None else None),
                is_assembly=is_assembly,
                rollup=_scale(_subtree_rollup(project, component), extended_qty)
                if is_assembly
                else None,
                extra=part.extra_fields() if part else {},
            )
        )

        for child in component.children:
            visit(child, level + 1, extended_qty)

    for component in project.components:
        visit(component, 0, 1)

    return rows


def consolidated_bom(project: Project) -> list[ConsolidatedRow]:
    """Flat BOM grouped by part number with summed extended quantities.

    Components without a part reference are grouped by name. Pure grouping
    assemblies (no part, cost, or weight of their own) are excluded — they
    are structure, not things you buy.
    """
    rows: dict[str, ConsolidatedRow] = {}

    def visit(component: Component, parent_qty: int) -> None:
        extended_qty = parent_qty * component.qty

        if not _is_pure_grouping(project, component):
            key = component.part if component.part is not None else f"name:{component.name}"
            part = _resolve_part(project, component)
            existing = rows.get(key)
            if existing is None:
                rows[key] = ConsolidatedRow(
                    part_number=component.part or "",
                    name=(part.description if part else None) or component.name,
                    total_qty=extended_qty,
                    supplier=(part.supplier if part else None) or "",
                    supplier_pn=(part.supplier_pn if part else None) or "",
                    link=((part.link if part else None) or component.link) or "",
                    unit_cost=_unit_cost(project, component),
                    extended_cost=None,
                    unit_weight_g=_unit_weight(project, component),
                    extended_weight_g=None,
                    extra=part.extra_fields() if part else {},
                )
            else:
                existing.total_qty += extended_qty

        for child in component.children:
            visit(child, extended_qty)

    for component in project.components:
        visit(component, 1)

    result = list(rows.values())
    for row in result:
        if row.unit_cost is not None:
            row.extended_cost = row.total_qty * row.unit_cost
        if row.unit_weight_g is not None:
            row.extended_weight_g = row.total_qty * row.unit_weight_g
    return result
