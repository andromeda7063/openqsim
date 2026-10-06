"""Unit tests for move, copy, and paste operations and selection interaction."""

import pytest
from libqsim.application.operations import (
    Clipboard,
    copy_gates,
    delete_gates,
    move_gates,
    paste,
)
from libqsim.application.selection import prune_selection
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


@pytest.mark.req("FR-1.7", "FR-1.8", "FR-1.9", "FR-1.37")
def test_move_single_gate_and_multiqubit_atomicity() -> None:
    """Moving a single gate or CNOT preserves atomicity, gate roles, and contiguous layout."""
    p_cx = GatePlacement(GateType.CNOT, targets=(2,), controls=(1,), column=0)
    c = Circuit(num_qubits=4, placements=(p_cx,))

    # Move CNOT by d_qubit=1, d_column=3
    res = move_gates(c, selection={p_cx}, d_qubit=1, d_column=3)
    assert res.status == "applied"
    expected = GatePlacement(GateType.CNOT, targets=(3,), controls=(2,), column=3)
    assert res.touched == (expected,)
    assert res.circuit.placements == (expected,)
    assert c.placements == (p_cx,)  # input unchanged


@pytest.mark.req("FR-1.46")
def test_move_group_into_cells_it_vacates() -> None:
    """A selection may move onto cells it vacates because old cells are removed first (FR-1.46)."""
    # Two adjacent gates in the same wire at column 0 and 1
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(0,), controls=(), column=1)
    c = Circuit(num_qubits=2, placements=(p0, p1))

    # Move both right by 1 column: p0 moves to col 1 (vacated by p1), p1 moves to col 2
    res = move_gates(c, selection={p0, p1}, d_qubit=0, d_column=1)
    assert res.status == "applied"
    exp0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=1)
    exp1 = GatePlacement(GateType.X, targets=(0,), controls=(), column=2)
    assert set(res.touched) == {exp0, exp1}
    assert set(res.circuit.placements) == {exp0, exp1}


@pytest.mark.req("FR-1.8", "FR-1.46", "NFR-3.4")
def test_move_blocked_by_unselected_gate() -> None:
    """A move that collides with an unselected gate is rejected atomically."""
    p_sel = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p_unsel = GatePlacement(GateType.X, targets=(0,), controls=(), column=1)
    c = Circuit(num_qubits=2, placements=(p_sel, p_unsel))

    # Move selected gate onto unselected gate's cell
    res = move_gates(c, selection={p_sel}, d_qubit=0, d_column=1)
    assert res.status == "rejected"
    assert len(res.messages) > 0
    assert res.circuit == c
    assert res.touched == ()


@pytest.mark.req("FR-1.8", "FR-1.38")
def test_move_arrow_semantics_and_boundary_rejection() -> None:
    """Arrow key deltas (up, down, left, right) work, and edge overflow is rejected atomically."""
    p = GatePlacement(GateType.H, targets=(1,), controls=(), column=1)
    c = Circuit(num_qubits=3, placements=(p,))

    # 4 cardinal directions
    res_up = move_gates(c, {p}, d_qubit=-1, d_column=0)
    assert res_up.status == "applied"
    assert res_up.touched[0].targets == (0,)

    res_down = move_gates(c, {p}, d_qubit=1, d_column=0)
    assert res_down.status == "applied"
    assert res_down.touched[0].targets == (2,)

    res_left = move_gates(c, {p}, d_qubit=0, d_column=-1)
    assert res_left.status == "applied"
    assert res_left.touched[0].column == 0

    res_right = move_gates(c, {p}, d_qubit=0, d_column=1)
    assert res_right.status == "applied"
    assert res_right.touched[0].column == 2

    # Boundary rejections: move beyond edges
    p_top_left = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    c_tl = Circuit(num_qubits=2, placements=(p_top_left,))
    assert move_gates(c_tl, {p_top_left}, d_qubit=-1, d_column=0).status == "rejected"
    assert move_gates(c_tl, {p_top_left}, d_qubit=0, d_column=-1).status == "rejected"

    p_bot_right = GatePlacement(GateType.H, targets=(1,), controls=(), column=49)
    c_br = Circuit(num_qubits=2, placements=(p_bot_right,))
    assert move_gates(c_br, {p_bot_right}, d_qubit=1, d_column=0).status == "rejected"
    assert move_gates(c_br, {p_bot_right}, d_qubit=0, d_column=1).status == "rejected"


@pytest.mark.req("FR-1.45", "FR-1.47")
def test_move_noop_and_invalid_selection_error() -> None:
    """Zero delta or empty selection is a noop; unassociated placement raises ValueError."""
    p = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    c = Circuit(num_qubits=2, placements=(p,))

    # Empty selection -> noop
    assert move_gates(c, selection=set(), d_qubit=1, d_column=1).status == "noop"

    # Zero delta -> noop
    assert move_gates(c, selection={p}, d_qubit=0, d_column=0).status == "noop"

    # Selection with placement not in circuit -> ValueError
    p_foreign = GatePlacement(GateType.X, targets=(1,), controls=(), column=0)
    with pytest.raises(ValueError):
        move_gates(c, selection={p_foreign}, d_qubit=1, d_column=0)


@pytest.mark.req("FR-1.24", "FR-1.26", "FR-1.27")
def test_copy_gates() -> None:
    """copy_gates stores placements relative to top-left anchor and preserves multi-qubit structure."""
    c = Circuit(num_qubits=5)

    # Empty selection -> None
    assert copy_gates(c, set()) is None

    # Multi-gate selection with CNOT
    # Anchor: min qubit is 2, min column is 3
    p_cx = GatePlacement(GateType.CNOT, targets=(3,), controls=(2,), column=3)
    p_h = GatePlacement(GateType.H, targets=(4,), controls=(), column=5)
    c_with_gates = Circuit(num_qubits=5, placements=(p_cx, p_h))

    cb = copy_gates(c_with_gates, {p_cx, p_h})
    assert isinstance(cb, Clipboard)
    assert len(cb.placements) == 2

    # Relative to (2, 3):
    # p_cx: targets=(3-2=1,), controls=(2-2=0,), column=3-3=0
    # p_h: targets=(4-2=2,), controls=(), column=5-3=2
    exp_cx = GatePlacement(GateType.CNOT, targets=(1,), controls=(0,), column=0)
    exp_h = GatePlacement(GateType.H, targets=(2,), controls=(), column=2)
    assert set(cb.placements) == {exp_cx, exp_h}

    # Foreign placement raises ValueError
    with pytest.raises(ValueError):
        copy_gates(c, {p_h})


@pytest.mark.req("FR-1.25", "FR-1.26", "FR-1.27", "FR-1.28", "FR-1.29", "FR-1.47")
def test_paste_operations() -> None:
    """paste places clipboard at destination anchor and rejects out-of-bounds or collision."""
    c = Circuit(num_qubits=4)

    # Empty/None clipboard -> noop
    assert paste(c, None, anchor_qubit=0, anchor_column=0).status == "noop"
    assert paste(c, Clipboard(placements=()), anchor_qubit=0, anchor_column=0).status == "noop"

    # Valid paste of CNOT relative (control 0, target 1, col 0)
    rel_cx = GatePlacement(GateType.CNOT, targets=(1,), controls=(0,), column=0)
    cb = Clipboard(placements=(rel_cx,))

    res_paste = paste(c, cb, anchor_qubit=1, anchor_column=5)
    assert res_paste.status == "applied"
    exp_cx = GatePlacement(GateType.CNOT, targets=(2,), controls=(1,), column=5)
    assert res_paste.touched == (exp_cx,)
    assert res_paste.circuit.placements == (exp_cx,)

    # Collision rejection: paste onto occupied cell
    c_occupied = res_paste.circuit
    res_coll = paste(c_occupied, cb, anchor_qubit=1, anchor_column=5)
    assert res_coll.status == "rejected"
    assert len(res_coll.messages) > 0
    assert res_coll.circuit == c_occupied

    # Bounds rejection: anchor causes placement to overflow qubit count (wire 3 + 1 = 4 >= 4)
    res_oob_q = paste(c, cb, anchor_qubit=3, anchor_column=0)
    assert res_oob_q.status == "rejected"
    assert res_oob_q.circuit == c

    # Bounds rejection: anchor causes column to overflow 50
    res_oob_col = paste(c, cb, anchor_qubit=0, anchor_column=50)
    assert res_oob_col.status == "rejected"
    assert res_oob_col.circuit == c


@pytest.mark.req("FR-1.6", "FR-1.21")
def test_prune_selection_after_delete() -> None:
    """prune_selection drops placements removed by delete_gates."""
    p0 = GatePlacement(GateType.H, targets=(0,), controls=(), column=0)
    p1 = GatePlacement(GateType.X, targets=(1,), controls=(), column=1)
    c = Circuit(num_qubits=2, placements=(p0, p1))
    sel = frozenset({p0, p1})

    # Delete p0
    res_del = delete_gates(c, {p0})
    assert res_del.status == "applied"

    # Prune selection against updated circuit
    pruned = prune_selection(res_del.circuit, sel)
    assert pruned == frozenset({p1})
