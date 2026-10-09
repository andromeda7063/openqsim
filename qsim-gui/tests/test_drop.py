"""Tests for drag and drop placement semantics and event handling."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas, handle_drop
from qsim_gui.widgets.gate_palette import encode_gate_mime
from qsim_gui.widgets.grid import GridGeometry


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.4", "FR-1.49")
def test_handle_drop_places_each_gate_type() -> None:
    for idx, gate_type in enumerate(GateType):
        session = EditorSession()
        # Ensure enough qubits for Toffoli (needs 3 qubits: 0, 1, 2)
        if gate_type == GateType.Toffoli:
            from libqsim.application.operations import resize

            session.apply(resize(session.circuit, 3))

        res = handle_drop(session, gate_type, cell=(0, idx))
        assert res.status == "applied"
        assert len(session.circuit.placements) == 1
        placement = session.circuit.placements[0]
        assert placement.gate_type == gate_type
        assert placement.column == idx
        assert session.can_undo is True


@pytest.mark.req("FR-1.5", "FR-1.49", "NFR-3.4")
def test_handle_drop_cnot_at_last_wire_rejected() -> None:
    session = EditorSession()  # 2 qubits: 0, 1
    # Wire 1 cannot host a 2-qubit CNOT (targets 1, 2 but wire 2 doesn't exist)
    res = handle_drop(session, GateType.CNOT, cell=(1, 0))

    assert res.status == "rejected"
    assert len(session.circuit.placements) == 0
    assert session.can_undo is False
    assert len(res.messages) > 0


@pytest.mark.req("FR-1.5", "NFR-3.4")
def test_handle_drop_collision_rejected_atomically() -> None:
    session = EditorSession()
    # Place H at (0, 0)
    res1 = handle_drop(session, GateType.H, cell=(0, 0))
    assert res1.status == "applied"
    assert session.can_undo is True

    # Attempt to drop X at (0, 0)
    res2 = handle_drop(session, GateType.X, cell=(0, 0))
    assert res2.status == "rejected"
    assert len(session.circuit.placements) == 1
    assert session.circuit.placements[0].gate_type == GateType.H
    # Undo history must still have only 1 entry from the initial placement
    assert session.undo() is True
    assert session.can_undo is False


@pytest.mark.req("FR-1.5", "NFR-3.4")
def test_handle_drop_after_measurement_rejected() -> None:
    session = EditorSession()
    # Place Measurement at (0, 2)
    res_m = handle_drop(session, GateType.Measurement, cell=(0, 2))
    assert res_m.status == "applied"

    # Placing gate at (0, 3) on wire 0 violates measurement rule
    res_after = handle_drop(session, GateType.H, cell=(0, 3))
    assert res_after.status == "rejected"
    assert len(session.circuit.placements) == 1
    assert session.circuit.placements[0].gate_type == GateType.Measurement


@pytest.mark.req("FR-1.4", "FR-1.5", "NFR-6.4")
def test_canvas_drop_event_end_to_end(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    geo = GridGeometry(cell_width=48, cell_height=48)
    canvas = CircuitCanvas(adapter=adapter, geometry=geo, ui=ui)

    # 1. Drop valid gate at cell (0, 0)
    cx, cy = geo.cell_center(0, 0)
    mime_data = encode_gate_mime(GateType.H)
    event = QDropEvent(
        QPointF(cx, cy),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(event)

    assert len(session.circuit.placements) == 1
    assert session.circuit.placements[0].gate_type == GateType.H
    assert len(ui.errors) == 0

    # 2. A release in the canvas margin reports a boundary error.
    event_outside = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(event_outside)
    assert len(session.circuit.placements) == 1
    assert len(ui.errors) == 1
    assert "outside" in ui.errors[0][1]

    # 3. Drop invalid (collision at (0, 0)): triggers ui.show_error
    mime_x = encode_gate_mime(GateType.X)
    event_invalid = QDropEvent(
        QPointF(cx, cy),
        Qt.DropAction.CopyAction,
        mime_x,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(event_invalid)
    assert len(session.circuit.placements) == 1
    assert len(ui.errors) == 2
    title, msg = ui.errors[-1]
    assert title == "Placement Error"
    assert len(msg) > 0
