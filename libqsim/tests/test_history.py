"""Unit tests for History snapshot stack management."""

import pytest
from libqsim.application.history import History
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


@pytest.mark.req("FR-1.12", "FR-1.13", "LC-4")
def test_history_initial_state() -> None:
    history = History()
    assert not history.can_undo
    assert not history.can_redo
    c = Circuit(2)
    assert history.undo(c) is None
    assert history.redo(c) is None


@pytest.mark.req("FR-1.12", "FR-1.13", "LC-4")
def test_history_push_and_undo_redo() -> None:
    history = History()
    c0 = Circuit(2)
    c1 = Circuit(2, [GatePlacement(GateType.H, [0], [], 0)])
    c2 = Circuit(2, [GatePlacement(GateType.H, [0], [], 0), GatePlacement(GateType.X, [1], [], 1)])

    history.push(c0)
    assert history.can_undo
    assert not history.can_redo

    history.push(c1)
    assert history.can_undo
    assert not history.can_redo

    # Undo back to c1
    prev = history.undo(c2)
    assert prev == c1
    assert history.can_undo
    assert history.can_redo

    # Undo back to c0
    prev2 = history.undo(c1)
    assert prev2 == c0
    assert not history.can_undo
    assert history.can_redo

    # Redo forward to c1
    nxt = history.redo(c0)
    assert nxt == c1
    assert history.can_undo
    assert history.can_redo

    # Redo forward to c2
    nxt2 = history.redo(c1)
    assert nxt2 == c2
    assert history.can_undo
    assert not history.can_redo


@pytest.mark.req("FR-1.12", "LC-5")
def test_history_push_clears_redo() -> None:
    history = History()
    c0 = Circuit(2)
    c1 = Circuit(2, [GatePlacement(GateType.H, [0], [], 0)])
    c2 = Circuit(2, [GatePlacement(GateType.X, [1], [], 0)])

    history.push(c0)
    assert history.undo(c1) == c0
    assert history.can_redo

    # New mutation commits c0 as history snapshot
    history.push(c0)
    assert not history.can_redo
    assert history.can_undo
    assert history.redo(c2) is None


@pytest.mark.req("FR-1.15", "LC-9")
def test_history_clear() -> None:
    history = History()
    c0 = Circuit(2)
    c1 = Circuit(2, [GatePlacement(GateType.H, [0], [], 0)])
    history.push(c0)
    assert history.undo(c1) == c0
    assert history.can_redo
    history.clear()
    assert not history.can_undo
    assert not history.can_redo
