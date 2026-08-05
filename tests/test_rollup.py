"""Tests for the rollup engine."""

from blockbom.project import Component, Part, Project
from blockbom.rollup import consolidated_bom, indented_bom, project_rollup


def _board_project() -> Project:
    """2x driver board, each with 4 screws and 1 MCU; one loose display."""
    return Project(
        name="P",
        components=[
            Component(
                id="board",
                name="Driver Board",
                qty=2,
                children=[
                    Component(id="mcu", name="MCU", part="MCU-1"),
                    Component(id="screws", name="Screws", part="M3-8MM", qty=4),
                ],
            ),
            Component(id="display", name="Display", part="DISP-1"),
        ],
        parts={
            "MCU-1": Part(cost=5.00, weight_g=10),
            "M3-8MM": Part(cost=0.10, weight_g=1),
            "DISP-1": Part(cost=20.00, weight_g=50, supplier="Adafruit"),
        },
    )


class TestExtendedQty:
    def test_qty_multiplies_through_levels(self):
        rows = indented_bom(_board_project())
        by_id = {r.component_id: r for r in rows}
        assert by_id["board"].extended_qty == 2
        assert by_id["mcu"].extended_qty == 2
        assert by_id["screws"].extended_qty == 8  # 2 boards x 4 screws
        assert by_id["display"].extended_qty == 1

    def test_extended_cost_uses_extended_qty(self):
        rows = indented_bom(_board_project())
        by_id = {r.component_id: r for r in rows}
        assert by_id["screws"].extended_cost == 8 * 0.10
        assert by_id["mcu"].extended_cost == 2 * 5.00

    def test_levels(self):
        rows = indented_bom(_board_project())
        by_id = {r.component_id: r for r in rows}
        assert by_id["board"].level == 0
        assert by_id["mcu"].level == 1
        assert by_id["display"].level == 0


class TestAssemblyRollup:
    def test_assembly_rollup_covers_subtree(self):
        rows = indented_bom(_board_project())
        board = next(r for r in rows if r.component_id == "board")
        assert board.is_assembly
        assert board.rollup is not None
        # Per board: 5.00 + 4 * 0.10 = 5.40; two boards = 10.80
        assert board.rollup.total_cost == 10.80
        assert board.rollup.total_weight_g == 2 * (10 + 4 * 1)
        assert board.rollup.part_count == 2 * 5
        assert board.rollup.cost_complete

    def test_leaf_has_no_rollup(self):
        rows = indented_bom(_board_project())
        display = next(r for r in rows if r.component_id == "display")
        assert display.rollup is None

    def test_assembly_with_own_part_includes_own_cost(self):
        project = Project(
            name="P",
            components=[
                Component(
                    id="enc",
                    name="Enclosure",
                    part="ENC-100",
                    children=[Component(id="psu", name="PSU", part="PS-1")],
                )
            ],
            parts={"ENC-100": Part(cost=40.0), "PS-1": Part(cost=10.0)},
        )
        enc = indented_bom(project)[0]
        assert enc.rollup is not None
        assert enc.rollup.total_cost == 50.0
        assert enc.rollup.part_count == 2  # shell + psu


class TestIncomplete:
    def test_missing_leaf_cost_marks_incomplete(self):
        project = Project(
            name="P",
            components=[
                Component(
                    id="a",
                    name="Assembly",
                    children=[
                        Component(id="known", name="Known", cost=5.0),
                        Component(id="unknown", name="Unknown"),
                    ],
                )
            ],
        )
        assembly = indented_bom(project)[0]
        assert assembly.rollup is not None
        assert assembly.rollup.total_cost == 5.0
        assert not assembly.rollup.cost_complete

    def test_pure_grouping_assembly_is_not_missing_data(self):
        project = Project(
            name="P",
            components=[
                Component(
                    id="group",
                    name="Grouping Only",
                    children=[Component(id="x", name="X", cost=1.0, weight_g=2.0)],
                )
            ],
        )
        rollup = project_rollup(project)
        assert rollup.cost_complete
        assert rollup.weight_complete

    def test_part_without_cost_marks_incomplete(self):
        project = Project(
            name="P",
            components=[Component(id="x", name="X", part="NC-1")],
            parts={"NC-1": Part(description="no cost yet")},
        )
        assert not project_rollup(project).cost_complete


class TestProjectRollup:
    def test_totals(self):
        rollup = project_rollup(_board_project())
        assert rollup.total_cost == 2 * (5.00 + 0.40) + 20.00
        assert rollup.total_weight_g == 2 * 14 + 50
        assert rollup.part_count == 11  # 2 boards + 2 mcus + 8 screws... boards are grouping
        assert rollup.cost_complete


class TestConsolidated:
    def test_shared_part_across_subsystems_sums_qty(self):
        project = Project(
            name="P",
            components=[
                Component(
                    id="a",
                    name="Sub A",
                    children=[Component(id="s1", name="Screws A", part="M3", qty=4)],
                ),
                Component(
                    id="b",
                    name="Sub B",
                    qty=2,
                    children=[Component(id="s2", name="Screws B", part="M3", qty=3)],
                ),
            ],
            parts={"M3": Part(cost=0.10)},
        )
        rows = consolidated_bom(project)
        m3 = next(r for r in rows if r.part_number == "M3")
        assert m3.total_qty == 4 + 2 * 3
        assert m3.extended_cost == 10 * 0.10

    def test_pure_grouping_assembly_excluded(self):
        rows = consolidated_bom(_board_project())
        names = {r.name for r in rows}
        assert "Driver Board" not in names
        assert len(rows) == 3

    def test_partless_components_grouped_by_name(self):
        project = Project(
            name="P",
            components=[
                Component(id="b1", name="Bracket", cost=2.0),
                Component(id="b2", name="Bracket", cost=2.0),
            ],
        )
        rows = consolidated_bom(project)
        assert len(rows) == 1
        assert rows[0].total_qty == 2
        assert rows[0].part_number == ""

    def test_part_description_and_supplier_carried(self):
        rows = consolidated_bom(_board_project())
        disp = next(r for r in rows if r.part_number == "DISP-1")
        assert disp.supplier == "Adafruit"
