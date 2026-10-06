"""Tests for Move (drag and arrow keys) and Change target interactions."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget
from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.selection_controller import SelectionController


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.7")
def test_drag_delta_and_threshold() -> None:
    ctrl = SelectionController()
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=2)
    ctrl.set_selection({p0})

    # Initiate drag on selected gate
    ctrl.start_drag_move(cell=(0, 2), pixel_pos=(100, 100))
    assert ctrl.is_drag_initiated is True
    assert ctrl.is_dragging_move is False

    # Small movement below threshold (e.g. 3 pixels)
    ctrl.update_drag_move(cell=(0, 2), pixel_pos=(102, 102))
    assert ctrl.is_dragging_move is False

    # Movement beyond threshold (e.g. 15 pixels) to cell (1, 4)
    ctrl.update_drag_move(cell=(1, 4), pixel_pos=(120, 120))
    assert ctrl.is_dragging_move is True
    assert ctrl.drag_delta == (1, 2)  # d_qubit = 1 - 0 = 1, d_col = 4 - 2 = 2


@pytest.mark.req("FR-1.7", "FR-1.21")
def test_drag_release_on_start_cell_treated_as_click() -> None:
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=1)
    circuit = Circuit(num_qubits=2, placements=(p0, p1))

    ctrl = SelectionController()
    ctrl.set_selection({p0, p1})

    # Drag initiated on p0 and released on start cell without moving
    ctrl.start_drag_move(cell=(0, 1), pixel_pos=(100, 100))
    ctrl.update_drag_move(cell=(0, 1), pixel_pos=(101, 101))
    # Release on start cell should treat as single click on p0
    action = ctrl.end_drag_move(circuit, cell=(0, 1))
    assert action == "click"
    # p0 selected alone
    assert ctrl.selection == frozenset({p0})
    assert ctrl.is_dragging_move is False


@pytest.mark.req("FR-1.7", "FR-1.21")
def test_drag_unselected_gate_selects_and_drags() -> None:
    p0 = GatePlacement(gate_type=GateType.H, targets=(0,), controls=(), column=1)
    p1 = GatePlacement(gate_type=GateType.X, targets=(1,), controls=(), column=1)
    circuit = Circuit(num_qubits=2, placements=(p0, p1))

    ctrl = SelectionController()
    ctrl.set_selection({p0})

    # Mouse down on unselected gate p1 selects p1 first
    ctrl.press_cell_for_drag(circuit, cell=(1, 1), pixel_pos=(100, 100), ctrl=False)
    assert ctrl.selection == frozenset({p1})
    assert ctrl.is_drag_initiated is True

    # Drag p1
    ctrl.update_drag_move(cell=(1, 3), pixel_pos=(150, 100))
    assert ctrl.is_dragging_move is True
    assert ctrl.drag_delta == (0, 2)


@pytest.mark.req("FR-1.7", "FR-1.37")
def test_arrow_key_movement_success_and_selection_following() -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))

    ctrl = SelectionController()
    h_gate = adapter.circuit.placements[0]
    ctrl.set_selection({h_gate})

    # Move right: d_qubit=0, d_column=1
    res = ctrl.move_selection(adapter.circuit, d_qubit=0, d_column=1)
    assert res.status == "applied"
    adapter.apply(res)
    ctrl.follow_move(res)

    # Placements updated in circuit
    assert len(adapter.circuit.placements) == 1
    new_h = adapter.circuit.placements[0]
    assert new_h.column == 1
    assert new_h.targets == (0,)
    # Selection followed moved gate
    assert ctrl.selection == frozenset({new_h})

    # Move down: d_qubit=1, d_column=0
    res2 = ctrl.move_selection(adapter.circuit, d_qubit=1, d_column=0)
    assert res2.status == "applied"
    adapter.apply(res2)
    ctrl.follow_move(res2)

    new_h2 = adapter.circuit.placements[0]
    assert new_h2.column == 1
    assert new_h2.targets == (1,)
    assert ctrl.selection == frozenset({new_h2})


@pytest.mark.req("FR-1.8", "FR-1.38")
def test_arrow_key_rejection_at_circuit_bounds() -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))

    ctrl = SelectionController()
    h_gate = adapter.circuit.placements[0]
    ctrl.set_selection({h_gate})

    init_history_len = len(session._history._undo_stack)

    # Attempt to move up (qubit -1, invalid)
    res = ctrl.move_selection(adapter.circuit, d_qubit=-1, d_column=0)
    assert res.status == "rejected"
    applied = adapter.apply(res)
    assert applied is False

    # Circuit and selection remain unchanged, no undo entry
    assert adapter.circuit.placements[0] == h_gate
    assert ctrl.selection == frozenset({h_gate})
    assert len(session._history._undo_stack) == init_history_len

    # Attempt to move left (col -1, invalid)
    res2 = ctrl.move_selection(adapter.circuit, d_qubit=0, d_column=-1)
    assert res2.status == "rejected"
    applied2 = adapter.apply(res2)
    assert applied2 is False
    assert adapter.circuit.placements[0] == h_gate
    assert ctrl.selection == frozenset({h_gate})
    assert len(session._history._undo_stack) == init_history_len


@pytest.mark.req("FR-1.8", "FR-1.46")
def test_arrow_key_rejection_onto_unselected_gate() -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=0, column=1))

    ctrl = SelectionController()
    h_gate = next(p for p in adapter.circuit.placements if p.gate_type == GateType.H)
    ctrl.set_selection({h_gate})

    # Try moving H gate onto X gate at (0, 1)
    res = ctrl.move_selection(adapter.circuit, d_qubit=0, d_column=1)
    assert res.status == "rejected"
    applied = adapter.apply(res)
    assert applied is False

    assert ctrl.selection == frozenset({h_gate})
    assert len(adapter.circuit.placements) == 2


@pytest.mark.req("FR-1.46")
def test_move_onto_vacated_cells_is_allowed() -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    # Gates at (0, 0) and (0, 1)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=0, column=1))

    ctrl = SelectionController()
    # Select BOTH gates
    ctrl.select_all(adapter.circuit)
    assert len(ctrl.selection) == 2

    # Shift right by 1 column: gate at (0, 0) moves into (0, 1) which was vacated!
    res = ctrl.move_selection(adapter.circuit, d_qubit=0, d_column=1)
    assert res.status == "applied"
    applied = adapter.apply(res)
    assert applied is True
    ctrl.follow_move(res)

    cols = {p.column for p in adapter.circuit.placements}
    assert cols == {1, 2}


@pytest.mark.req("FR-1.47")
def test_empty_selection_arrow_key_is_noop() -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))

    ctrl = SelectionController()
    assert ctrl.selection == frozenset()

    res = ctrl.move_selection(adapter.circuit, d_qubit=0, d_column=1)
    assert res.status == "noop"
    applied = adapter.apply(res)
    assert applied is False
    assert len(session._history._undo_stack) == 1


@pytest.mark.req("FR-1.50")
def test_change_target_enabled_states(qapp: QApplication) -> None:
    from libqsim.application.operations import resize

    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(resize(session.circuit, 3))
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Empty selection: disabled
    assert commands.action_change_target.isEnabled() is False

    # H gate selected: disabled
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    h_gate = adapter.circuit.placements[0]
    ctrl.set_selection({h_gate})
    assert commands.action_change_target.isEnabled() is False

    # CNOT placed and selected: enabled
    adapter.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=2))
    cnot = next(p for p in adapter.circuit.placements if p.gate_type == GateType.CNOT)
    ctrl.set_selection({cnot})
    assert commands.action_change_target.isEnabled() is True

    # Multi-selection (CNOT + H): disabled
    ctrl.set_selection({cnot, h_gate})
    assert commands.action_change_target.isEnabled() is False

    # Toffoli placed and selected: enabled
    adapter.apply(place_gate(session.circuit, GateType.Toffoli, qubit=0, column=4))
    toffoli = next(p for p in adapter.circuit.placements if p.gate_type == GateType.Toffoli)
    ctrl.set_selection({toffoli})
    assert commands.action_change_target.isEnabled() is True


@pytest.mark.req("FR-1.50")
def test_change_target_cnot_swap(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Drop CNOT at qubit 0, column 1: controls=(0,), targets=(1,)
    adapter.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    cnot = adapter.circuit.placements[0]
    assert cnot.controls == (0,)
    assert cnot.targets == (1,)
    ctrl.set_selection({cnot})

    # Trigger Change target
    commands.action_change_target.trigger()
    new_cnot = adapter.circuit.placements[0]
    assert new_cnot.controls == (1,)
    assert new_cnot.targets == (0,)
    assert ctrl.selection == frozenset({new_cnot})

    # Trigger again: swaps back
    commands.action_change_target.trigger()
    swapped_back = adapter.circuit.placements[0]
    assert swapped_back.controls == (0,)
    assert swapped_back.targets == (1,)
    assert ctrl.selection == frozenset({swapped_back})


@pytest.mark.req("FR-1.50")
def test_change_target_toffoli_cycles_top_middle_bottom_top(qapp: QApplication) -> None:
    from libqsim.application.operations import resize

    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(resize(session.circuit, 3))
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Default Toffoli dropped at 0: controls=(0, 1), targets=(2,) [bottom]
    adapter.apply(place_gate(session.circuit, GateType.Toffoli, qubit=0, column=0))
    t0 = adapter.circuit.placements[0]
    assert t0.targets == (2,)
    ctrl.set_selection({t0})

    # 1. bottom -> top (target 0, controls 1, 2)
    commands.action_change_target.trigger()
    t1 = adapter.circuit.placements[0]
    assert t1.targets == (0,)
    assert set(t1.controls) == {1, 2}
    assert ctrl.selection == frozenset({t1})

    # 2. top -> middle (target 1, controls 0, 2)
    commands.action_change_target.trigger()
    t2 = adapter.circuit.placements[0]
    assert t2.targets == (1,)
    assert set(t2.controls) == {0, 2}
    assert ctrl.selection == frozenset({t2})

    # 3. middle -> bottom (target 2, controls 0, 1)
    commands.action_change_target.trigger()
    t3 = adapter.circuit.placements[0]
    assert t3.targets == (2,)
    assert set(t3.controls) == {0, 1}
    assert ctrl.selection == frozenset({t3})


@pytest.mark.req("FR-1.37", "NFR-2.7")
def test_canvas_arrow_key_and_scroll_into_view(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    canvas = CircuitCanvas(adapter=adapter)
    canvas.show()

    scroll_area = QScrollArea()
    scroll_area.setWidget(canvas)
    scroll_area.resize(300, 200)
    scroll_area.show()

    # Select the H gate
    canvas.selection_controller.click_cell(adapter.circuit, (0, 0))
    assert len(canvas.selection_controller.selection) == 1

    # Press Right arrow key
    right_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Right,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(right_event)

    # Gate moved right to column 1
    assert adapter.circuit.placements[0].column == 1
    assert next(iter(canvas.selection_controller.selection)).column == 1
