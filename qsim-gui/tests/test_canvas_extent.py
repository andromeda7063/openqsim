"""Viewport-driven circuit canvas extent."""

import pytest
from libqsim.application.operations import delete_gates, place_gate, resize
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtWidgets import QApplication, QScrollArea
from qsim_gui.state import SessionAdapter
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
    area.resize(300, 220)
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
    area.resize(420, 220)
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
    area.resize(300, 220)
    area.show()
    qapp.processEvents()
    assert area.verticalScrollBar().maximum() == 0
    adapter.apply(resize(session.circuit, 10))
    qapp.processEvents()
    assert area.verticalScrollBar().maximum() > 0
