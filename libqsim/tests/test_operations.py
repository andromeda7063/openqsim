"""Unit tests for circuit editing operations and mutation results."""

import time

import pytest
from libqsim.application.operations import (
    change_target,
    clear,
    delete_gates,
    place_gate,
    plan_resize,
    resize,
)
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


@pytest.mark.req("FR-1.4", "FR-1.5", "FR-1.49")
def test_place_single_qubit_gate_and_measurement() -> None:
    """Placing single-qubit gates and measurements succeeds and touches the new placement."""
    c0 = Circuit(num_qubits=2)
    res_h = place_gate(c0, GateType.H, qubit=0, column=0)
    assert res_h.status == "applied"
    assert len(res_h.circuit.placements) == 1
    assert res_h.touched == (GatePlacement(GateType.H, (0,), (), 0),)
    assert c0.placements == ()  # input unchanged

    res_meas = place_gate(res_h.circuit, GateType.Measurement, qubit=1, column=1)
    assert res_meas.status == "applied"
    assert len(res_meas.circuit.placements) == 2
    assert res_meas.touched == (GatePlacement(GateType.Measurement, (1,), (), 1),)


@pytest.mark.req("FR-1.4", "FR-1.49")
def test_place_cnot_and_toffoli_default_orientation() -> None:
    """Dropped CNOT and Toffoli default to upper wires as controls and bottom wire as target."""
    c = Circuit(num_qubits=4)

    # CNOT dropped at wire 1 -> control 1, target 2
    res_cx = place_gate(c, GateType.CNOT, qubit=1, column=0)
    assert res_cx.status == "applied"
    expected_cx = GatePlacement(GateType.CNOT, targets=(2,), controls=(1,), column=0)
    assert res_cx.touched == (expected_cx,)
    assert res_cx.circuit.placements == (expected_cx,)

    # Toffoli dropped at wire 0 -> controls 0, 1, target 2
    res_ccx = place_gate(res_cx.circuit, GateType.Toffoli, qubit=0, column=1)
    assert res_ccx.status == "applied"
    expected_ccx = GatePlacement(GateType.Toffoli, targets=(2,), controls=(0, 1), column=1)
    assert res_ccx.touched == (expected_ccx,)


@pytest.mark.req("FR-1.5", "NFR-3.4")
def test_place_gate_rejected_boundary_and_collision() -> None:
    """Invalid placements are rejected atomically; input circuit remains unchanged."""
    c = Circuit(num_qubits=3)

    # CNOT at wire 2 on 3-qubit circuit needs wire 3 -> out of bounds
    res_cx_oob = place_gate(c, GateType.CNOT, qubit=2, column=0)
    assert res_cx_oob.status == "rejected"
    assert len(res_cx_oob.messages) > 0
    assert res_cx_oob.circuit == c
    assert res_cx_oob.touched == ()

    # Toffoli at wire 1 on 3-qubit circuit needs wire 3 -> out of bounds
    res_ccx_oob = place_gate(c, GateType.Toffoli, qubit=1, column=0)
    assert res_ccx_oob.status == "rejected"
    assert len(res_ccx_oob.messages) > 0
    assert res_ccx_oob.circuit == c

    # Place H at (0, 0), then attempt to place X at (0, 0) -> collision
    res_h = place_gate(c, GateType.H, qubit=0, column=0)
    assert res_h.status == "applied"
    c_with_h = res_h.circuit

    res_collision = place_gate(c_with_h, GateType.X, qubit=0, column=0)
    assert res_collision.status == "rejected"
    assert len(res_collision.messages) > 0
    assert res_collision.circuit == c_with_h

    # Column out of bounds (< 0 or >= 50)
    res_neg_col = place_gate(c, GateType.X, qubit=0, column=-1)
    assert res_neg_col.status == "rejected"
    res_50_col = place_gate(c, GateType.X, qubit=0, column=50)
    assert res_50_col.status == "rejected"

    # Measurement rule violation: gate after measurement on same wire
    c_meas = place_gate(c, GateType.Measurement, qubit=0, column=5).circuit
    res_after_meas = place_gate(c_meas, GateType.X, qubit=0, column=6)
    assert res_after_meas.status == "rejected"
    assert res_after_meas.circuit == c_meas


@pytest.mark.req("FR-1.6", "FR-1.45")
def test_delete_gates() -> None:
    """Deleting gates applies when removing existing gates and is a noop on empty/unmatched."""
    p1 = GatePlacement(GateType.H, (0,), (), 0)
    p2 = GatePlacement(GateType.X, (1,), (), 0)
    c = Circuit(num_qubits=2, placements=(p1, p2))

    # Delete existing placement
    res = delete_gates(c, (p1,))
    assert res.status == "applied"
    assert res.circuit.placements == (p2,)
    assert res.touched == ()
    assert c.placements == (p1, p2)  # input unchanged

    # Delete empty collection -> noop
    res_empty = delete_gates(c, ())
    assert res_empty.status == "noop"
    assert res_empty.circuit == c
    assert res_empty.messages == ()

    # Delete non-existent placement -> noop
    p_nonexistent = GatePlacement(GateType.Z, (0,), (), 2)
    res_nonexistent = delete_gates(c, (p_nonexistent,))
    assert res_nonexistent.status == "noop"
    assert res_nonexistent.circuit == c


@pytest.mark.req("FR-1.10", "FR-1.45")
def test_clear() -> None:
    """Clear removes all gates if non-empty, and returns noop on empty circuit."""
    c_empty = Circuit(num_qubits=3)
    res_empty = clear(c_empty)
    assert res_empty.status == "noop"
    assert res_empty.circuit == c_empty
    assert res_empty.messages == ()

    p = GatePlacement(GateType.H, (0,), (), 0)
    c_gates = Circuit(num_qubits=3, placements=(p,))
    res_clear = clear(c_gates)
    assert res_clear.status == "applied"
    assert res_clear.circuit.placements == ()
    assert c_gates.placements == (p,)  # input unchanged


@pytest.mark.req("FR-1.9", "FR-1.50")
def test_change_target_cnot() -> None:
    """change_target swaps CNOT control and target; twice returns to original."""
    c = Circuit(num_qubits=3)
    c1 = place_gate(c, GateType.CNOT, qubit=0, column=2).circuit
    p_orig = c1.placements[0]
    assert p_orig.controls == (0,)
    assert p_orig.targets == (1,)

    # Swap 1
    res1 = change_target(c1, p_orig)
    assert res1.status == "applied"
    p_swapped = res1.touched[0]
    assert p_swapped.controls == (1,)
    assert p_swapped.targets == (0,)
    assert res1.circuit.placements == (p_swapped,)

    # Swap 2 -> returns to original
    res2 = change_target(res1.circuit, p_swapped)
    assert res2.status == "applied"
    assert res2.circuit == c1
    assert res2.touched[0] == p_orig


@pytest.mark.req("FR-1.9", "FR-1.50")
def test_change_target_toffoli_cycle() -> None:
    """change_target cycles Toffoli target top -> middle -> bottom -> top."""
    c = Circuit(num_qubits=3)
    # Default drop at wire 0: controls 0, 1, target 2 (bottom)
    c0 = place_gate(c, GateType.Toffoli, qubit=0, column=0).circuit
    p0 = c0.placements[0]
    assert p0.targets == (2,)
    assert p0.controls == (0, 1)

    # Cycle 1: bottom (2) -> top (0)
    res1 = change_target(c0, p0)
    assert res1.status == "applied"
    p1 = res1.touched[0]
    assert p1.targets == (0,)
    assert p1.controls == (1, 2)
    assert p1.occupied_qubits == (0, 1, 2)

    # Cycle 2: top (0) -> middle (1)
    res2 = change_target(res1.circuit, p1)
    assert res2.status == "applied"
    p2 = res2.touched[0]
    assert p2.targets == (1,)
    assert p2.controls == (0, 2)
    assert p2.occupied_qubits == (0, 1, 2)

    # Cycle 3: middle (1) -> bottom (2) -> matches initial
    res3 = change_target(res2.circuit, p2)
    assert res3.status == "applied"
    assert res3.circuit == c0
    assert res3.touched[0] == p0


@pytest.mark.req("FR-1.50")
def test_change_target_rejected_for_single_qubit_and_missing() -> None:
    """change_target rejects non-CNOT/Toffoli gates or placements not in circuit."""
    p_h = GatePlacement(GateType.H, (0,), (), 0)
    c = Circuit(num_qubits=2, placements=(p_h,))

    # Non-CNOT/Toffoli
    res = change_target(c, p_h)
    assert res.status == "rejected"
    assert len(res.messages) > 0
    assert res.circuit == c

    # Placement not in circuit
    p_cx = GatePlacement(GateType.CNOT, (1,), (0,), 1)
    res_missing = change_target(c, p_cx)
    assert res_missing.status == "rejected"
    assert len(res_missing.messages) > 0


@pytest.mark.req("FR-1.16", "FR-1.17")
def test_plan_resize() -> None:
    """plan_resize correctly identifies affected gates and confirmation requirement."""
    p_q0 = GatePlacement(GateType.H, (0,), (), 0)
    p_q1 = GatePlacement(GateType.X, (1,), (), 0)
    p_cx = GatePlacement(GateType.CNOT, targets=(2,), controls=(1,), column=1)
    c = Circuit(num_qubits=4, placements=(p_q0, p_q1, p_cx))

    # Increase size: no affected, no confirmation
    plan_grow = plan_resize(c, 5)
    assert plan_grow.requested == 5
    assert plan_grow.affected == ()
    assert not plan_grow.needs_confirmation

    # Decrease to 3: p_cx occupies wire 2 (< 3), wire 3 is empty -> no affected
    plan_shrink_3 = plan_resize(c, 3)
    assert plan_shrink_3.affected == ()
    assert not plan_shrink_3.needs_confirmation

    # Decrease to 2: p_cx occupies wires 1 and 2 (2 >= 2) -> affected!
    plan_shrink_2 = plan_resize(c, 2)
    assert plan_shrink_2.affected == (p_cx,)
    assert plan_shrink_2.needs_confirmation


@pytest.mark.req("FR-1.3", "FR-1.16", "FR-1.17", "FR-1.18", "FR-1.19", "FR-1.45")
def test_resize_operations() -> None:
    """resize handles size range, noops, expansion, and destructive confirmation."""
    p_q0 = GatePlacement(GateType.H, (0,), (), 0)
    # CNOT with control on 2, target on 1
    p_cx = GatePlacement(GateType.CNOT, targets=(1,), controls=(2,), column=1)
    c = Circuit(num_qubits=3, placements=(p_q0, p_cx))

    # Out of range (0 and 11) rejected
    assert resize(c, 0).status == "rejected"
    assert resize(c, 11).status == "rejected"

    # Same size -> noop
    res_same = resize(c, 3)
    assert res_same.status == "noop"
    assert res_same.circuit == c

    # Increase -> applied, placements kept
    res_grow = resize(c, 5)
    assert res_grow.status == "applied"
    assert res_grow.circuit.num_qubits == 5
    assert res_grow.circuit.placements == c.placements

    # Decrease with no affected gates (c with just p_q0)
    c_single = Circuit(num_qubits=3, placements=(p_q0,))
    res_shrink_safe = resize(c_single, 2, confirmed=False)
    assert res_shrink_safe.status == "applied"
    assert res_shrink_safe.circuit.num_qubits == 2
    assert res_shrink_safe.circuit.placements == (p_q0,)

    # Decrease with affected gates and confirmed=False -> rejected with message
    res_unconfirmed = resize(c, 2, confirmed=False)
    assert res_unconfirmed.status == "rejected"
    assert len(res_unconfirmed.messages) > 0
    assert res_unconfirmed.circuit == c  # unchanged

    # Decrease with affected gates and confirmed=True -> removes affected gates
    res_confirmed = resize(c, 2, confirmed=True)
    assert res_confirmed.status == "applied"
    assert res_confirmed.circuit.num_qubits == 2
    assert res_confirmed.circuit.placements == (p_q0,)  # p_cx removed because control on wire 2


@pytest.mark.req("NFR-1.2")
@pytest.mark.perf
def test_editing_performance_10_qubit_circuit() -> None:
    """Each editing operation on a 10-qubit circuit finishes within 100 ms (NFR-1.2)."""
    # Build a full 10-qubit circuit with gates in multiple columns
    placements: list[GatePlacement] = []
    for col in range(20):
        for q in range(0, 10, 2):
            placements.append(
                GatePlacement(GateType.CNOT, targets=(q + 1,), controls=(q,), column=col)
            )
    c = Circuit(num_qubits=10, placements=placements)

    # 1. place_gate
    t0 = time.perf_counter()
    res_place = place_gate(c, GateType.X, qubit=0, column=25)
    dt_place = time.perf_counter() - t0
    assert res_place.status == "applied"
    assert dt_place < 0.100

    # 2. change_target
    p_to_change = placements[0]
    t0 = time.perf_counter()
    res_change = change_target(c, p_to_change)
    dt_change = time.perf_counter() - t0
    assert res_change.status == "applied"
    assert dt_change < 0.100

    # 3. delete_gates
    t0 = time.perf_counter()
    res_del = delete_gates(c, (p_to_change,))
    dt_del = time.perf_counter() - t0
    assert res_del.status == "applied"
    assert dt_del < 0.100

    # 4. resize confirmed
    t0 = time.perf_counter()
    res_resize = resize(c, 8, confirmed=True)
    dt_resize = time.perf_counter() - t0
    assert res_resize.status == "applied"
    assert dt_resize < 0.100

    # 5. clear
    t0 = time.perf_counter()
    res_clear = clear(c)
    dt_clear = time.perf_counter() - t0
    assert res_clear.status == "applied"
    assert dt_clear < 0.100
