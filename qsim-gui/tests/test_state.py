"""Tests for SessionAdapter."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.models import GateType
from PySide6.QtWidgets import QApplication
from qsim_gui.state import SessionAdapter


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("NFR-5.5")
def test_adapter_contains_no_own_state(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)

    assert adapter.session is session
    assert adapter.circuit is session.circuit
    assert adapter.file_path is session.file_path
    assert adapter.baseline is session.baseline
    assert adapter.save_status == session.save_status
    assert adapter.simulation_status == session.simulation_status
    assert adapter.simulation_result is session.simulation_result
    assert adapter.can_undo == session.can_undo
    assert adapter.can_redo == session.can_redo

    # Mutate through session directly; adapter properties must reflect session without independent storage
    res = place_gate(session.circuit, GateType.H, qubit=0, column=0)
    session.apply(res)

    assert adapter.circuit == session.circuit
    assert adapter.save_status == SaveStatus.DIRTY
    assert adapter.can_undo is True
    assert adapter.can_redo is False


@pytest.mark.req("NFR-5.5")
def test_adapter_emits_changed_signal(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)

    signal_received = False

    def on_changed() -> None:
        nonlocal signal_received
        signal_received = True

    adapter.changed.connect(on_changed)

    res = place_gate(session.circuit, GateType.X, qubit=0, column=0)
    adapter.apply(res)

    assert signal_received is True


@pytest.mark.req("NFR-5.5")
def test_adapter_delegates_undo_redo_and_run(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)

    res = place_gate(session.circuit, GateType.X, qubit=0, column=0)
    adapter.apply(res)
    assert adapter.can_undo is True

    # Undo
    assert adapter.undo() is True
    assert adapter.can_undo is False
    assert adapter.can_redo is True
    assert len(adapter.circuit.placements) == 0

    # Redo
    assert adapter.redo() is True
    assert len(adapter.circuit.placements) == 1

    # Run
    outcome = adapter.run()
    assert outcome.ok is True
    assert adapter.simulation_status == SimulationStatus.CURRENT

    # Detach
    adapter.detach()
    # After detaching, session mutations do not emit adapter signal
    notified = False
    adapter.changed.connect(lambda: nonlocal_notify())

    def nonlocal_notify() -> None:
        nonlocal notified
        notified = True

    adapter.apply(place_gate(session.circuit, GateType.H, qubit=1, column=1))
    assert notified is False
