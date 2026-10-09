"""Palette drag previews draw gate-shaped, non-mutating ghosts."""

import pytest
from libqsim.application.operations import resize
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent
from PySide6.QtWidgets import QApplication
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import encode_gate_mime


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.mark.req("FR-1.52")
@pytest.mark.parametrize("gate_type", list(GateType))
def test_gate_drag_ghost_is_shaped_and_non_mutating(
    qapp: QApplication, gate_type: GateType
) -> None:
    session = EditorSession()
    if gate_type == GateType.Toffoli:
        session.apply(resize(session.circuit, 3))
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    canvas.show()
    qapp.processEvents()
    before = canvas.grab().toImage()
    state = (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    )
    selection = canvas.selection_controller.selection
    cx, cy = canvas.grid_geometry.cell_center(0, 1)
    mime = encode_gate_mime(gate_type)
    enter = QDragEnterEvent(
        QPoint(cx, cy),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragEnterEvent(enter)
    preview = canvas.drag_preview
    assert preview is not None
    assert preview.gate_type == gate_type
    assert preview.column == 1
    assert preview.occupied_qubits == tuple(range(len(canvas._drag_cells)))
    assert canvas.grab().toImage() != before

    nx, ny = canvas.grid_geometry.cell_center(0, 2)
    move = QDragMoveEvent(
        QPoint(nx, ny),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragMoveEvent(move)
    assert canvas.drag_preview is not None and canvas.drag_preview.column == 2
    canvas.dragLeaveEvent(QDragLeaveEvent())
    assert canvas.drag_preview is None
    assert canvas.grab().toImage() == before
    assert (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    ) == state
    assert canvas.selection_controller.selection == selection
