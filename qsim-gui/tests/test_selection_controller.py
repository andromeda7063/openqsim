"""Tests for SelectionController and selection/delete editing interaction."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QWidget
from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.selection_controller import SelectionController


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.21", "NFR-2.6")
def test_click_gate_and_click_empty() -> None:
    circuit = Circuit(num_qubits=3)
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=2)
    circuit = circuit.with_placements((p0, p1))

    ctrl = SelectionController()
    assert ctrl.selection == frozenset()
    assert ctrl.last_clicked_cell is None

    # Click on gate p0
    ctrl.click_cell(circuit, (0, 1))
    assert ctrl.selection == frozenset({p0})
    assert ctrl.last_clicked_cell == (0, 1)

    # Click on gate p1 replaces selection
    ctrl.click_cell(circuit, (1, 2))
    assert ctrl.selection == frozenset({p1})
    assert ctrl.last_clicked_cell == (1, 2)

    # Click on empty cell clears selection
    ctrl.click_cell(circuit, (2, 3))
    assert ctrl.selection == frozenset()
    assert ctrl.last_clicked_cell == (2, 3)


@pytest.mark.req("FR-1.21", "NFR-2.6")
def test_ctrl_click_toggle() -> None:
    circuit = Circuit(num_qubits=3)
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=2)
    circuit = circuit.with_placements((p0, p1))

    ctrl = SelectionController()

    # Click p0
    ctrl.click_cell(circuit, (0, 1), ctrl=False)
    assert ctrl.selection == frozenset({p0})

    # Ctrl-click p1 adds it to selection
    ctrl.click_cell(circuit, (1, 2), ctrl=True)
    assert ctrl.selection == frozenset({p0, p1})

    # Ctrl-click p0 removes it from selection
    ctrl.click_cell(circuit, (0, 1), ctrl=True)
    assert ctrl.selection == frozenset({p1})

    # Ctrl-click empty cell preserves current selection
    ctrl.click_cell(circuit, (2, 5), ctrl=True)
    assert ctrl.selection == frozenset({p1})
    assert ctrl.last_clicked_cell == (2, 5)


@pytest.mark.req("FR-1.20", "FR-1.22", "NFR-2.6")
def test_marquee_replace() -> None:
    circuit = Circuit(num_qubits=4)
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=2)
    p2 = GatePlacement(gate_type=GateType.Z, targets=(3,), controls=(), column=5)
    circuit = circuit.with_placements((p0, p1, p2))

    ctrl = SelectionController()
    ctrl.set_selection({p2})

    # Marquee from (0, 0) to (2, 3) replaces existing selection
    ctrl.marquee_begin((0, 0), ctrl=False)
    ctrl.marquee_update(circuit, (2, 3))
    assert ctrl.selection == frozenset({p0, p1})
    ctrl.marquee_end(circuit, (2, 3))
    assert ctrl.selection == frozenset({p0, p1})
    assert ctrl.last_clicked_cell == (0, 0)


@pytest.mark.req("FR-1.20", "FR-1.22", "NFR-2.6")
def test_ctrl_marquee_toggle() -> None:
    circuit = Circuit(num_qubits=4)
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=2)
    p2 = GatePlacement(gate_type=GateType.Z, targets=(2,), controls=(), column=2)
    circuit = circuit.with_placements((p0, p1, p2))

    ctrl = SelectionController()
    # Initially select p0 and p1
    ctrl.set_selection({p0, p1})

    # Ctrl-marquee covering p1 and p2 (qubits 1..2, column 2)
    # p1 is in base -> toggled off; p2 is not in base -> toggled on; p0 is untouched -> remains on
    ctrl.marquee_begin((1, 2), ctrl=True)
    ctrl.marquee_update(circuit, (2, 2))
    assert ctrl.selection == frozenset({p0, p2})
    ctrl.marquee_end(circuit, (2, 2))
    assert ctrl.selection == frozenset({p0, p2})


@pytest.mark.req("FR-1.23", "NFR-2.6")
def test_marquee_touching_one_wire_cnot_selects_whole_gate() -> None:
    circuit = Circuit(num_qubits=3)
    # CNOT on control 0, target 1, column 3
    cnot = GatePlacement(gate_type=GateType.CNOT, targets=(1,), controls=(0,), column=3)
    circuit = circuit.with_placements((cnot,))

    ctrl = SelectionController()

    # Marquee covering ONLY qubit 0, column 3 (touches control only)
    ctrl.marquee_begin((0, 3), ctrl=False)
    ctrl.marquee_update(circuit, (0, 3))
    ctrl.marquee_end(circuit, (0, 3))
    assert ctrl.selection == frozenset({cnot})

    # Clear and marquee covering ONLY qubit 1, column 3 (touches target only)
    ctrl.clear_selection()
    ctrl.marquee_begin((1, 3), ctrl=False)
    ctrl.marquee_update(circuit, (1, 3))
    ctrl.marquee_end(circuit, (1, 3))
    assert ctrl.selection == frozenset({cnot})


@pytest.mark.req("FR-1.36", "NFR-2.6")
def test_select_all() -> None:
    circuit = Circuit(num_qubits=3)
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(gate_type=GateType.CNOT, targets=(2,), controls=(1,), column=1)
    circuit = circuit.with_placements((p0, p1))

    ctrl = SelectionController()
    assert ctrl.selection == frozenset()

    ctrl.select_all(circuit)
    assert ctrl.selection == frozenset({p0, p1})


@pytest.mark.req("FR-1.6", "NFR-2.6")
def test_prune_after_circuit_change() -> None:
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=1)

    ctrl = SelectionController()
    ctrl.set_selection({p0, p1})

    # Suppose p1 is deleted from the circuit
    new_circuit = Circuit(num_qubits=2, placements=(p0,))
    ctrl.prune(new_circuit)
    assert ctrl.selection == frozenset({p0})


@pytest.mark.req("FR-1.14")
def test_selection_does_not_change_session_history_or_status() -> None:
    session = EditorSession()
    # Apply one gate so circuit has content and Clean status
    res = place_gate(session.circuit, GateType.H, qubit=0, column=0)
    session.apply(res)

    initial_save_status = session.save_status
    initial_sim_status = session.simulation_status
    initial_can_undo = session.can_undo
    initial_can_redo = session.can_redo

    ctrl = SelectionController()
    # Click gate
    ctrl.click_cell(session.circuit, (0, 0))
    # Select all
    ctrl.select_all(session.circuit)
    # Clear selection
    ctrl.clear_selection()
    # Marquee
    ctrl.marquee_begin((0, 0))
    ctrl.marquee_update(session.circuit, (1, 1))
    ctrl.marquee_end(session.circuit, (1, 1))

    # Session state must be completely untouched
    assert session.save_status == initial_save_status
    assert session.simulation_status == initial_sim_status
    assert session.can_undo == initial_can_undo
    assert session.can_redo == initial_can_redo


@pytest.mark.req("FR-1.6", "FR-1.35")
def test_delete_selection_action(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Place two gates
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=1, column=1))
    assert len(adapter.circuit.placements) == 2

    # Select the H gate
    h_gate = next(p for p in adapter.circuit.placements if p.gate_type == GateType.H)
    ctrl.click_cell(adapter.circuit, (0, 0))
    assert ctrl.selection == frozenset({h_gate})
    assert commands.action_delete.isEnabled() is True

    # Trigger delete
    commands.action_delete.trigger()
    assert len(adapter.circuit.placements) == 1
    assert adapter.circuit.placements[0].gate_type == GateType.X
    # Selection pruned / cleared
    assert ctrl.selection == frozenset()
    assert commands.action_delete.isEnabled() is False


@pytest.mark.req("FR-1.6", "FR-1.35", "FR-1.45")
def test_delete_empty_selection_is_noop(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert len(adapter.circuit.placements) == 1
    assert ctrl.selection == frozenset()
    assert commands.action_delete.isEnabled() is False

    # Trigger delete with empty selection
    commands.action_delete.trigger()
    # No mutation occurred, circuit untouched, undo stack unchanged
    assert len(adapter.circuit.placements) == 1
    assert commands.action_undo.isEnabled() is True  # still the single place_gate


@pytest.mark.req("FR-1.35", "FR-1.36")
def test_delete_and_select_all_shortcuts(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Select all shortcut is Ctrl+A
    assert (
        commands.action_select_all.shortcut().matches(QKeySequence("Ctrl+A"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    # Delete has Delete and Backspace shortcuts
    shortcuts = [s.toString() for s in commands.action_delete.shortcuts()]
    assert "Del" in shortcuts or "Delete" in shortcuts
    assert "Backspace" in shortcuts or "BkSp" in shortcuts


@pytest.mark.req("FR-1.10", "FR-1.45")
def test_clear_action(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Empty circuit: clear is disabled
    assert commands.action_clear.isEnabled() is False

    # Add gate: clear is enabled
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert commands.action_clear.isEnabled() is True
    assert len(adapter.circuit.placements) == 1

    # Select gate, then clear
    ctrl.click_cell(adapter.circuit, (0, 0))
    assert len(ctrl.selection) == 1

    commands.action_clear.trigger()
    assert len(adapter.circuit.placements) == 0
    assert len(ctrl.selection) == 0
    assert commands.action_clear.isEnabled() is False


@pytest.mark.req("FR-1.21", "NFR-2.6")
def test_canvas_mouse_click_and_focus(qapp: QApplication) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from qsim_gui.widgets.circuit_canvas import CircuitCanvas

    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=1))
    canvas = CircuitCanvas(adapter=adapter)
    canvas.show()

    h_gate = adapter.circuit.placements[0]
    cx, cy = canvas.grid_geometry.cell_center(0, 1)

    # Simulate mouse press on gate
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(cx, cy),
        QPointF(cx, cy),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press_event)
    qapp.processEvents()

    assert canvas.selection_controller.selection == frozenset({h_gate})
    assert canvas.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert canvas.hasFocus() is True


@pytest.mark.req("FR-1.20", "NFR-2.6")
def test_canvas_marquee_drag(qapp: QApplication) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from qsim_gui.widgets.circuit_canvas import CircuitCanvas

    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=1))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=1, column=2))
    canvas = CircuitCanvas(adapter=adapter)

    # Start marquee on empty cell (0, 0)
    x0, y0 = canvas.grid_geometry.cell_center(0, 0)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(x0, y0),
        QPointF(x0, y0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press_event)
    assert canvas.selection_controller.is_marquee_active is True

    # Drag to cell (1, 3)
    x1, y1 = canvas.grid_geometry.cell_center(1, 3)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(x1, y1),
        QPointF(x1, y1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move_event)

    # Both gates must be selected
    assert len(canvas.selection_controller.selection) == 2

    # Release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(x1, y1),
        QPointF(x1, y1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(release_event)
    assert canvas.selection_controller.is_marquee_active is False
    assert len(canvas.selection_controller.selection) == 2


@pytest.mark.req("FR-1.35", "FR-1.36")
def test_canvas_keyboard_delete_and_select_all(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from qsim_gui.widgets.circuit_canvas import CircuitCanvas

    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=1, column=1))
    canvas = CircuitCanvas(adapter=adapter)

    # Press Ctrl+A
    select_all_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_A,
        Qt.KeyboardModifier.ControlModifier,
    )
    canvas.keyPressEvent(select_all_event)
    assert len(canvas.selection_controller.selection) == 2

    # Press Delete
    del_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(del_event)
    assert len(adapter.circuit.placements) == 0
    assert len(canvas.selection_controller.selection) == 0
