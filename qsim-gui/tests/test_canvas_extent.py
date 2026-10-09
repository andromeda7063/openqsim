"""Viewport-driven circuit canvas extent."""

from pathlib import Path

import pytest
from libqsim.application.operations import delete_gates, place_gate, resize
from libqsim.application.session import EditorSession
from libqsim.domain.models import Circuit, GatePlacement, GateType
from libqsim.persistence.qcs import write
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QScrollArea
from qsim_gui.state import SessionAdapter
from qsim_gui.theme import Theme, apply_theme
from qsim_gui.widgets.circuit_canvas import CircuitCanvas


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.mark.req("FR-1.51", "NFR-2.7")
def test_canvas_extent_tracks_viewport_and_circuit(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    area = QScrollArea()
    area.setWidget(canvas)
    area.setFixedSize(300, 220)
    area.show()
    qapp.processEvents()

    viewport_width = area.viewport().width()
    visible = canvas.grid_geometry.visible_columns(viewport_width)
    assert canvas.revealed_columns == visible
    assert canvas.width() == viewport_width
    assert area.horizontalScrollBar().maximum() == 0

    adapter.apply(place_gate(session.circuit, GateType.H, 0, visible - 1))
    qapp.processEvents()
    assert canvas.revealed_columns == visible + 1
    assert area.horizontalScrollBar().maximum() > 0

    adapter.apply(delete_gates(session.circuit, session.circuit.placements))
    qapp.processEvents()
    assert canvas.revealed_columns == visible
    assert area.horizontalScrollBar().maximum() == 0

    baseline = (session.circuit, session.save_status, session.simulation_status, session.can_undo)
    area.setFixedSize(420, 220)
    qapp.processEvents()
    assert canvas.revealed_columns == canvas.grid_geometry.visible_columns(area.viewport().width())
    assert area.horizontalScrollBar().maximum() == 0
    assert (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
    ) == baseline

    adapter.apply(place_gate(session.circuit, GateType.X, 0, 49))
    qapp.processEvents()
    assert canvas.revealed_columns == 50
    assert area.horizontalScrollBar().maximum() > 0
    assert canvas.grid_geometry.point_to_cell(*canvas.grid_geometry.cell_center(0, 49)) == (0, 49)
    assert canvas.grid_geometry.point_to_cell(*canvas.grid_geometry.cell_center(0, 50)) is None


@pytest.mark.req("FR-1.51", "NFR-2.7")
def test_vertical_scrollbar_only_when_needed(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(resize(session.circuit, 1))
    area = QScrollArea()
    canvas = CircuitCanvas(adapter)
    area.setWidget(canvas)
    area.setFixedSize(300, 220)
    area.show()
    qapp.processEvents()
    assert area.verticalScrollBar().maximum() == 0
    adapter.apply(resize(session.circuit, 10))
    qapp.processEvents()
    assert area.verticalScrollBar().maximum() > 0


@pytest.mark.req("FR-1.51", "LC-9", "LC-10")
def test_load_undo_redo_and_new_recompute_extent(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    area = QScrollArea()
    area.setWidget(canvas)
    area.setFixedSize(300, 220)
    area.show()
    qapp.processEvents()
    visible = canvas.revealed_columns

    adapter.apply(place_gate(session.circuit, GateType.H, 0, visible - 1))
    assert canvas.revealed_columns == visible + 1
    adapter.undo()
    assert canvas.revealed_columns == visible
    adapter.redo()
    assert canvas.revealed_columns == visible + 1

    path = tmp_path / "last-column.qcs"
    write(path, Circuit(2, (GatePlacement(GateType.X, (0,), (), 49),)))
    assert session.open(path).ok
    assert canvas.revealed_columns == 50
    area.horizontalScrollBar().setValue(area.horizontalScrollBar().maximum())
    qapp.processEvents()
    x, _, w, _ = canvas.grid_geometry.cell_to_rect(0, 49)
    assert area.horizontalScrollBar().value() <= x
    assert x + w <= area.horizontalScrollBar().value() + area.viewport().width()

    session.new()
    assert canvas.revealed_columns == visible
    assert area.horizontalScrollBar().maximum() == 0


@pytest.mark.req("FR-1.51", "NFR-2.9")
@pytest.mark.parametrize("theme", [Theme.DARK, Theme.DARK_PURPLE])
def test_revealed_canvas_uses_theme_colors(qapp: QApplication, theme: Theme) -> None:
    apply_theme(qapp, theme)
    session = EditorSession()
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    area = QScrollArea()
    area.setWidget(canvas)
    area.setFixedSize(300, 220)
    area.show()
    qapp.processEvents()
    base = qapp.palette().color(QPalette.ColorRole.Base)
    wire_y = canvas.grid_geometry.cell_center(0, 0)[1]
    for change in (None, place_gate(session.circuit, GateType.H, 0, 4)):
        if change is not None:
            adapter.apply(change)
        image = canvas.grab().toImage()
        assert image.pixelColor(canvas.width() - 2, 90) == base
        wire_x = min(
            canvas.width() - 5,
            canvas.grid_geometry.margins.left
            + canvas.revealed_columns * canvas.grid_geometry.cell_width
            - 5,
        )
        wire = image.pixelColor(wire_x, wire_y)
        assert wire != base
        assert wire.red() < 255 and wire.green() < 255 and wire.blue() < 255
