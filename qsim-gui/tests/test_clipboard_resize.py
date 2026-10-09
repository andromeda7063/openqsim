"""Tests for in-app clipboard, copy/paste, qubit resizing, and undo/redo synchronization."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate, resize
from libqsim.application.session import EditorSession
from libqsim.domain.gates import GateType
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QSpinBox, QWidget
from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.selection_controller import SelectionController


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.24", "FR-1.33", "FR-1.47")
def test_copy_action_lifecycle_and_empty_selection(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    assert (
        commands.action_copy.shortcut().matches(QKeySequence("Ctrl+C"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    # Initially no selection -> copy disabled
    assert commands.action_copy.isEnabled() is False
    assert commands.clipboard is None

    # Place a gate and select it
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=1))
    h_gate = adapter.circuit.placements[0]
    ctrl.set_selection({h_gate})
    assert commands.action_copy.isEnabled() is True

    # Copy
    commands.action_copy.trigger()
    assert commands.clipboard is not None
    assert len(commands.clipboard.placements) == 1
    assert commands.action_paste.isEnabled() is True

    # Deselect -> copy disabled, but clipboard retained
    ctrl.clear_selection()
    assert commands.action_copy.isEnabled() is False
    assert commands.clipboard is not None


@pytest.mark.req("FR-1.25", "FR-1.26", "FR-1.27", "FR-1.30", "FR-1.34", "FR-1.48")
def test_paste_at_anchor_and_relative_geometry(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(resize(session.circuit, 4))
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    assert (
        commands.action_paste.shortcut().matches(QKeySequence("Ctrl+V"))
        == QKeySequence.SequenceMatch.ExactMatch
    )

    # Place CNOT (q0->q1, col 1) and X (q2, col 2)
    adapter.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=2, column=2))
    ctrl.select_all(adapter.circuit)
    commands.action_copy.trigger()

    # Click anchor cell (qubit 1, column 5)
    ctrl.click_empty(cell=(1, 5))
    assert ctrl.last_clicked_cell == (1, 5)

    init_history_len = len(session._history._undo_stack)
    commands.action_paste.trigger()

    # Exactly 1 history entry created
    assert len(session._history._undo_stack) == init_history_len + 1

    # Check pasted placements relative to (1, 5):
    # CNOT was at (0..1, col 1), anchor was (0, 1) -> relative (0..1, col 0) -> dest (1..2, col 5)
    # X was at (2, col 2) -> relative (2, col 1) -> dest (3, col 6)
    pasted_cnot = next(
        p for p in adapter.circuit.placements if p.gate_type == GateType.CNOT and p.column == 5
    )
    assert pasted_cnot.controls == (1,)
    assert pasted_cnot.targets == (2,)

    pasted_x = next(
        p for p in adapter.circuit.placements if p.gate_type == GateType.X and p.column == 6
    )
    assert pasted_x.targets == (3,)

    # Paste does NOT change selection
    assert ctrl.selection == frozenset()


@pytest.mark.req("FR-1.48")
def test_paste_with_no_prior_click_defaults_to_qubit0_col0(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    # Place H at (1, 2)
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=1, column=2))
    ctrl.set_selection(adapter.circuit.placements)
    commands.action_copy.trigger()

    # Clear last_clicked_cell to simulate fresh session with no clicks
    ctrl._last_clicked_cell = None
    assert ctrl.last_clicked_cell is None

    # Clear circuit so (0, 0) is empty
    commands.action_clear.trigger()
    assert len(adapter.circuit.placements) == 0

    commands.action_paste.trigger()
    assert len(adapter.circuit.placements) == 1
    pasted_gate = adapter.circuit.placements[0]
    assert pasted_gate.targets == (0,)
    assert pasted_gate.column == 0


@pytest.mark.req("FR-1.28", "FR-1.29")
def test_paste_overflow_or_collision_rejected(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    ctrl.set_selection(adapter.circuit.placements)
    commands.action_copy.trigger()

    init_circuit = adapter.circuit
    init_history_len = len(session._history._undo_stack)

    # 1. Collision at (0, 0)
    ctrl.click_empty(cell=(0, 0))
    commands.action_paste.trigger()
    assert len(ui.errors) == 1
    assert "Paste Error" in ui.errors[0][0]
    assert adapter.circuit == init_circuit
    assert len(session._history._undo_stack) == init_history_len

    # 2. Out of bounds at column 50
    ctrl.click_empty(cell=(0, 50))
    commands.action_paste.trigger()
    assert len(ui.errors) == 2
    assert adapter.circuit == init_circuit
    assert len(session._history._undo_stack) == init_history_len


@pytest.mark.req("FR-1.47")
def test_empty_clipboard_paste_is_noop(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    ctrl = SelectionController()
    commands = CommandActions(widget, adapter, ui, selection_controller=ctrl)

    assert commands.clipboard is None
    commands.action_paste.trigger()
    assert len(session._history._undo_stack) == 0
    assert len(ui.errors) == 0


@pytest.mark.req("FR-1.3", "FR-1.16")
def test_qubit_count_increase_in_main_window(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    spin_box = window.findChild(QSpinBox, "qubit_spin_box")
    assert spin_box is not None
    assert spin_box.value() == 2
    assert adapter.circuit.num_qubits == 2

    # Place a gate on qubit 1
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=1, column=0))

    # Increase to 5
    spin_box.setValue(5)
    assert adapter.circuit.num_qubits == 5
    assert len(adapter.circuit.placements) == 1
    assert adapter.circuit.placements[0].targets == (1,)


@pytest.mark.req("FR-1.17", "FR-1.18", "FR-1.19")
def test_destructive_resize_confirmation_and_cancel_snapback(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)
    spin_box = window.findChild(QSpinBox, "qubit_spin_box")
    assert spin_box is not None

    # Expand to 4 qubits
    spin_box.setValue(4)
    assert adapter.circuit.num_qubits == 4

    # Place gate on qubit 3 (will be removed if resized to 2)
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=3, column=0))
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert len(adapter.circuit.placements) == 2

    # User cancels resize dialog (confirm_response = False)
    ui.confirm_response = False
    spin_box.setValue(2)

    # Dialog was prompted identifying gates
    assert len(ui.confirms) == 1
    assert "1" in ui.confirms[0][1]  # 1 affected gate
    # Circuit unchanged
    assert adapter.circuit.num_qubits == 4
    assert len(adapter.circuit.placements) == 2
    # Spin box snapped back to 4
    assert spin_box.value() == 4

    # Now user confirms resize dialog (confirm_response = True)
    ui.confirm_response = True
    spin_box.setValue(2)
    assert len(ui.confirms) == 2
    assert adapter.circuit.num_qubits == 2
    assert len(adapter.circuit.placements) == 1
    assert adapter.circuit.placements[0].gate_type == GateType.H
    assert spin_box.value() == 2


@pytest.mark.req("FR-1.12", "FR-1.19")
def test_undo_redo_syncs_qubit_spin_box(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)
    spin_box = window.findChild(QSpinBox, "qubit_spin_box")
    assert spin_box is not None

    # Initial: 2 qubits
    assert spin_box.value() == 2

    # Resize to 5 qubits
    spin_box.setValue(5)
    assert adapter.circuit.num_qubits == 5
    assert spin_box.value() == 5

    # Undo resize
    window.commands.action_undo.trigger()
    assert adapter.circuit.num_qubits == 2
    assert spin_box.value() == 2

    # Redo resize
    window.commands.action_redo.trigger()
    assert adapter.circuit.num_qubits == 5
    assert spin_box.value() == 5
