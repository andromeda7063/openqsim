"""Unit tests for selection query, geometry, and selection state operations."""

import pytest
from libqsim.application.selection import (
    click_selection,
    gate_at,
    gates_in_rect,
    marquee_selection,
    prune_selection,
    select_all,
)
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


@pytest.mark.req("FR-1.21", "FR-1.23")
def test_gate_at_single_and_multiqubit() -> None:
    """gate_at finds single-qubit gates and finds multi-qubit gates from ANY occupied wire."""
    p_h = GatePlacement(GateType.H, targets=(0,), controls=(), column=1)
    p_cx = GatePlacement(GateType.CNOT, targets=(2,), controls=(1,), column=3)
    c = Circuit(num_qubits=4, placements=(p_h, p_cx))

    # Single-qubit gate hit and miss
    assert gate_at(c, qubit=0, column=1) == p_h
    assert gate_at(c, qubit=1, column=1) is None
    assert gate_at(c, qubit=0, column=2) is None

    # Multi-qubit gate hit from control wire (1) and target wire (2)
    assert gate_at(c, qubit=1, column=3) == p_cx
    assert gate_at(c, qubit=2, column=3) == p_cx

    # Multi-qubit gate miss on unoccupied wire
    assert gate_at(c, qubit=0, column=3) is None
    assert gate_at(c, qubit=3, column=3) is None


@pytest.mark.req("FR-1.20", "FR-1.23")
def test_gates_in_rect_atomicity_and_normalization() -> None:
    """gates_in_rect returns whole multi-qubit gates if any wire intersects, and normalizes bounds."""
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=2)
    p_cx = GatePlacement(GateType.CNOT, targets=(3,), controls=(2,), column=4)
    c = Circuit(num_qubits=5, placements=(p0, p1, p_cx))

    # Exact enclosing rect for p0 and p1
    res1 = gates_in_rect(c, q_min=0, q_max=1, c_min=0, c_max=2)
    assert res1 == frozenset({p0, p1})

    # Rect intersecting ONLY wire 2 of CNOT (which occupies wires 2 and 3)
    # FR-1.23: entire multi-qubit gate must be selected
    res_partial_wire = gates_in_rect(c, q_min=2, q_max=2, c_min=4, c_max=4)
    assert res_partial_wire == frozenset({p_cx})

    # Inverted rectangle coordinates (q_min > q_max, c_min > c_max)
    res_inverted = gates_in_rect(c, q_min=1, q_max=0, c_min=2, c_max=0)
    assert res_inverted == frozenset({p0, p1})

    # Disjoint rectangle
    res_empty = gates_in_rect(c, q_min=4, q_max=4, c_min=0, c_max=0)
    assert res_empty == frozenset()


@pytest.mark.req("FR-1.36")
def test_select_all() -> None:
    """select_all returns all placements in circuit as a frozenset."""
    c_empty = Circuit(num_qubits=2)
    assert select_all(c_empty) == frozenset()

    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=1)
    c = Circuit(num_qubits=2, placements=(p0, p1))
    assert select_all(c) == frozenset({p0, p1})


@pytest.mark.req("FR-1.21")
def test_click_selection() -> None:
    """click_selection handles click-to-replace, empty-click, and Ctrl toggle."""
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=1)

    current = frozenset({p0})

    # Click another gate without Ctrl -> replaces selection
    res_replace = click_selection(current, hit=p1, ctrl=False)
    assert res_replace == frozenset({p1})

    # Click empty space without Ctrl -> clears selection
    res_clear = click_selection(current, hit=None, ctrl=False)
    assert res_clear == frozenset()

    # Click unselected gate with Ctrl -> adds to selection
    res_add = click_selection(current, hit=p1, ctrl=True)
    assert res_add == frozenset({p0, p1})

    # Click selected gate with Ctrl -> removes from selection
    res_remove = click_selection(frozenset({p0, p1}), hit=p0, ctrl=True)
    assert res_remove == frozenset({p1})

    # Click empty space with Ctrl -> retains current selection
    res_empty_ctrl = click_selection(current, hit=None, ctrl=True)
    assert res_empty_ctrl == current


@pytest.mark.req("FR-1.20", "FR-1.22")
def test_marquee_selection() -> None:
    """marquee_selection replaces without Ctrl, and toggles intersected gates with Ctrl."""
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=1)
    p2 = GatePlacement(GateType.Z, targets=(0,), controls=(), column=2)

    current = frozenset({p0})
    rect_gates = [p1, p2]

    # Marquee without Ctrl -> replaces current selection
    res_replace = marquee_selection(current, rect_gates, ctrl=False)
    assert res_replace == frozenset({p1, p2})

    # Marquee with Ctrl -> toggles state of intersected gates
    # p0 is already selected and intersected -> deselected
    # p1 is not selected and intersected -> selected
    res_toggle = marquee_selection(current=frozenset({p0}), rect_gates=[p0, p1], ctrl=True)
    assert res_toggle == frozenset({p1})


@pytest.mark.req("FR-1.21")
def test_prune_selection() -> None:
    """prune_selection drops placements no longer in the circuit."""
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=1)
    p_removed = GatePlacement(GateType.Z, targets=(0,), controls=(), column=2)

    c = Circuit(num_qubits=2, placements=(p0, p1))
    sel = frozenset({p0, p_removed})

    pruned = prune_selection(c, sel)
    assert pruned == frozenset({p0})
