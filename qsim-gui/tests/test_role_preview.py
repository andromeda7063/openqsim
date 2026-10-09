"""Control and target roles stay visible in placement and move previews."""

import pytest
from libqsim.application.operations import change_target, move_gates, place_gate, resize
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QDragEnterEvent
from PySide6.QtWidgets import QApplication
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import encode_gate_mime


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


@pytest.mark.req("FR-1.53")
@pytest.mark.parametrize(
    "gate_type,num_qubits",
    [(GateType.CNOT, 2), (GateType.CNOT, 10), (GateType.Toffoli, 3), (GateType.Toffoli, 10)],
)
def test_palette_preview_roles_match_placement(
    qapp: QApplication, gate_type: GateType, num_qubits: int
) -> None:
    session = EditorSession()
    session.apply(resize(session.circuit, num_qubits))
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    for top in range(num_qubits - (2 if gate_type == GateType.CNOT else 3) + 1):
        cx, cy = canvas.grid_geometry.cell_center(top, 0)
        mime = encode_gate_mime(gate_type)
        event = QDragEnterEvent(
            QPoint(cx, cy),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.dragEnterEvent(event)
        result = place_gate(session.circuit, gate_type, top, 0)
        assert result.status == "applied"
        assert canvas.drag_preview == result.touched[0]
        assert canvas.drag_preview.targets == (top + (1 if gate_type == GateType.CNOT else 2),)
        assert canvas.drag_preview.occupied_qubits == tuple(
            range(top, top + len(canvas._drag_cells))
        )


@pytest.mark.req("FR-1.53")
@pytest.mark.parametrize(
    "gate_type,num_qubits,cycles", [(GateType.CNOT, 2, 2), (GateType.Toffoli, 3, 3)]
)
def test_move_preview_preserves_changed_roles(
    qapp: QApplication, gate_type: GateType, num_qubits: int, cycles: int
) -> None:
    session = EditorSession()
    session.apply(resize(session.circuit, num_qubits))
    session.apply(place_gate(session.circuit, gate_type, 0, 0))
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    for _ in range(cycles):
        original = session.circuit.placements[0]
        canvas.selection_controller.set_selection({original})
        canvas.selection_controller.start_drag_move((0, 0), (100, 100))
        canvas.selection_controller.update_drag_move((0, 1), (150, 100))
        preview = canvas.move_preview
        assert len(preview) == 1
        expected = move_gates(session.circuit, (original,), 0, 1)
        assert preview == expected.touched
        assert preview[0].controls == original.controls
        assert preview[0].targets == original.targets
        canvas.selection_controller.end_drag_move(session.circuit, (0, 1))
        session.apply(change_target(session.circuit, original))
