"""Unit tests for headless guarded action execution (LC-12 to LC-15)."""

from pathlib import Path

import pytest
from libqsim.application.guarded import UserChoice, run_guarded
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus
from libqsim.domain.gates import GateType


def get_save_status(session: EditorSession) -> SaveStatus:
    return session.save_status


@pytest.mark.req("LC-12", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_clean_session_always_executes_action(trigger: str) -> None:
    session = EditorSession()
    assert get_save_status(session) == SaveStatus.CLEAN

    action_executed = False
    save_called = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        return True

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        return True

    # Choice should be ignored when CLEAN
    result = run_guarded(session, None, save_fn, action_fn)
    assert result is True
    assert action_executed is True
    assert save_called is False


@pytest.mark.req("LC-12", "LC-13", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_dirty_save_success(trigger: str) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    assert get_save_status(session) == SaveStatus.DIRTY

    save_called = False
    action_executed = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        session.mark_saved(Path("/tmp/test.qcs"))
        return True

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        return True

    result = run_guarded(session, UserChoice.SAVE, save_fn, action_fn)
    assert result is True
    assert save_called is True
    assert action_executed is True


@pytest.mark.req("LC-12", "LC-13", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_dirty_save_failure(trigger: str) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    initial_circuit = session.circuit
    assert get_save_status(session) == SaveStatus.DIRTY

    save_called = False
    action_executed = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        return False  # Save failed or was cancelled by user in dialog

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        return True

    result = run_guarded(session, UserChoice.SAVE, save_fn, action_fn)
    assert result is False
    assert save_called is True
    assert action_executed is False
    # Session state completely unchanged
    assert session.circuit == initial_circuit
    assert get_save_status(session) == SaveStatus.DIRTY


@pytest.mark.req("LC-12", "LC-14", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_dirty_dont_save(trigger: str) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    assert get_save_status(session) == SaveStatus.DIRTY

    save_called = False
    action_executed = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        return True

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        return True

    result = run_guarded(session, UserChoice.DONT_SAVE, save_fn, action_fn)
    assert result is True
    assert save_called is False
    assert action_executed is True


@pytest.mark.req("LC-12", "LC-14", "LC-11", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_dirty_dont_save_failing_action(trigger: str) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    initial_circuit = session.circuit
    initial_can_undo = session.can_undo
    assert get_save_status(session) == SaveStatus.DIRTY

    save_called = False
    action_executed = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        return True

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        # Simulated action failure (e.g. open/import failed): preserves state
        return False

    result = run_guarded(session, UserChoice.DONT_SAVE, save_fn, action_fn)
    # The action ran
    assert result is True
    assert save_called is False
    assert action_executed is True
    # Nothing was discarded: initial session state intact
    assert session.circuit == initial_circuit
    assert session.can_undo == initial_can_undo
    assert get_save_status(session) == SaveStatus.DIRTY


@pytest.mark.req("LC-12", "LC-15", "NFR-7.8")
@pytest.mark.parametrize("trigger", ["New", "Open", "Import", "Exit"])
def test_guarded_dirty_cancel(trigger: str) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    initial_circuit = session.circuit
    assert get_save_status(session) == SaveStatus.DIRTY

    save_called = False
    action_executed = False

    def save_fn() -> bool:
        nonlocal save_called
        save_called = True
        return True

    def action_fn() -> bool:
        nonlocal action_executed
        action_executed = True
        return True

    result = run_guarded(session, UserChoice.CANCEL, save_fn, action_fn)
    assert result is False
    assert save_called is False
    assert action_executed is False
    assert session.circuit == initial_circuit
    assert get_save_status(session) == SaveStatus.DIRTY
