"""Unit and state transition tests for EditorSession."""

from pathlib import Path

import pytest
from libqsim.application.operations import OperationResult, place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.simulation.engine import SimulationError
from libqsim.simulation.results import SimulationResult


def get_save_status(session: EditorSession) -> SaveStatus:
    return session.save_status


def get_sim_status(session: EditorSession) -> SimulationStatus:
    return session.simulation_status


@pytest.mark.req("LC-1", "FR-1.1", "FR-1.2", "NFR-5.5", "NFR-7.8")
def test_lc1_startup() -> None:
    session = EditorSession()
    assert session.circuit == Circuit(2)
    assert session.circuit.num_qubits == 2
    assert session.file_path is None
    assert session.baseline == session.circuit
    assert get_save_status(session) == SaveStatus.CLEAN
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.simulation_result is None
    assert not session.can_undo
    assert not session.can_redo


@pytest.mark.req("LC-7", "LC-8", "FR-3.15")
def test_trace_navigation_stale_retention_and_failed_run_preservation() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.X, qubit=1, column=3))
    assert session.run().ok
    assert [snapshot.column for snapshot in session.simulation_trace] == [None, 0, 3]
    assert session.selected_step == 0
    assert session.selected_snapshot == session.simulation_trace[0]

    assert session.select_step(2)
    prior_result = session.simulation_result
    prior_trace = session.simulation_trace
    session.apply(place_gate(session.circuit, GateType.Z, qubit=0, column=5))
    assert session.simulation_status == SimulationStatus.STALE
    assert session.selected_step == 2
    assert session.simulation_trace is prior_trace

    def fail(_circuit: Circuit) -> SimulationResult:
        raise SimulationError("expected failure")

    outcome = session.run(simulate_fn=fail)
    assert not outcome.ok
    assert session.simulation_result is prior_result
    assert session.simulation_trace is prior_trace
    assert session.selected_step == 2
    assert session.simulation_status == SimulationStatus.STALE


@pytest.mark.req("LC-2", "FR-1.13", "FR-3.7", "NFR-5.5")
def test_lc2_mutation_and_stale() -> None:
    session = EditorSession()

    # Mutation with no previous simulation stays NONE
    res = place_gate(session.circuit, GateType.H, 0, 0)
    applied = session.apply(res)
    assert applied
    assert get_save_status(session) == SaveStatus.DIRTY
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.can_undo
    assert not session.can_redo

    # Run simulation -> CURRENT
    run_res = session.run()
    assert run_res.ok
    assert get_sim_status(session) == SimulationStatus.CURRENT
    assert get_save_status(session) == SaveStatus.DIRTY  # Save status unchanged

    # Mutation with existing result -> STALE
    res2 = place_gate(session.circuit, GateType.X, 1, 1)
    applied2 = session.apply(res2)
    assert applied2
    assert get_sim_status(session) == SimulationStatus.STALE


@pytest.mark.req("LC-3", "LC-4", "FR-1.12", "FR-1.13")
def test_lc3_lc4_undo_redo_and_baseline_equality() -> None:
    session = EditorSession()
    # Apply gate 1: H at (0, 0)
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    assert get_save_status(session) == SaveStatus.DIRTY

    # Run -> CURRENT
    run_res = session.run()
    assert run_res.ok
    assert get_sim_status(session) == SimulationStatus.CURRENT

    # Undo -> circuit is empty, matches baseline -> CLEAN!
    assert session.can_undo
    undone = session.undo()
    assert undone
    assert session.circuit == session.baseline
    assert get_save_status(session) == SaveStatus.CLEAN
    # Undo stales simulation result (LC-4)
    assert get_sim_status(session) == SimulationStatus.STALE

    # Redo -> DIRTY again
    assert session.can_redo
    redone = session.redo()
    assert redone
    assert get_save_status(session) == SaveStatus.DIRTY
    assert get_sim_status(session) == SimulationStatus.STALE


@pytest.mark.req("LC-5", "FR-1.12")
def test_lc5_apply_after_undo_clears_redo() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.undo()
    assert session.can_redo

    # Commit new mutation
    session.apply(place_gate(session.circuit, GateType.X, 1, 0))
    assert not session.can_redo
    assert session.can_undo


@pytest.mark.req("LC-7", "FR-3.5", "FR-3.6", "FR-3.7")
def test_lc7_run_success_and_stale_never_restores_historical() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    save_status_before = get_save_status(session)

    run_res = session.run()
    assert run_res.ok
    assert get_sim_status(session) == SimulationStatus.CURRENT
    assert get_save_status(session) == save_status_before
    first_res = session.simulation_result
    assert first_res is not None

    # Mutate -> STALE
    session.apply(place_gate(session.circuit, GateType.X, 1, 1))
    assert get_sim_status(session) == SimulationStatus.STALE

    # Undo back to the circuit that was simulated -> STILL STALE!
    session.undo()
    assert get_sim_status(session) == SimulationStatus.STALE
    assert session.simulation_result is first_res


@pytest.mark.req("LC-8", "FR-3.12", "NFR-3.2")
def test_lc8_failing_simulation() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    run_res = session.run()
    assert run_res.ok
    assert get_sim_status(session) == SimulationStatus.CURRENT
    prev_result = session.simulation_result

    def failing_sim(circuit: Circuit) -> SimulationResult:
        raise SimulationError("Injected simulation failure")

    # Failing run on CURRENT result
    fail_res = session.run(simulate_fn=failing_sim)
    assert not fail_res.ok
    assert "Injected simulation failure" in fail_res.messages[0]
    assert get_sim_status(session) == SimulationStatus.CURRENT
    assert session.simulation_result is prev_result

    # Mutate to make it STALE
    session.apply(place_gate(session.circuit, GateType.Z, 0, 1))
    assert get_sim_status(session) == SimulationStatus.STALE

    # Failing run on STALE result
    fail_res2 = session.run(simulate_fn=failing_sim)
    assert not fail_res2.ok
    assert get_sim_status(session) == SimulationStatus.STALE
    assert session.simulation_result is prev_result


@pytest.mark.req("LC-8", "FR-3.12")
def test_lc8_invalid_circuit_run_refuses_simulation() -> None:
    session = EditorSession()
    # Force an invalid circuit into session directly
    invalid_circuit = Circuit(2, [GatePlacement(GateType.H, [0], [], 55)])
    session._circuit = invalid_circuit

    sim_called = False

    def spy_sim(circuit: Circuit) -> SimulationResult:
        nonlocal sim_called
        sim_called = True
        raise AssertionError("Simulator should not have been called")

    run_res = session.run(simulate_fn=spy_sim)
    assert not run_res.ok
    assert not sim_called
    assert any("column" in m.lower() for m in run_res.messages)


@pytest.mark.req("LC-9", "LC-10", "LC-6", "FR-1.15", "FR-1.14")
def test_lc9_lc10_lc6_lifecycle_primitives() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.run()

    # establish_loaded
    loaded_circuit = Circuit(3, [GatePlacement(GateType.X, [1], [], 0)])
    loaded_path = Path("/tmp/test.qcs")
    session.establish_loaded(loaded_circuit, loaded_path)
    assert session.circuit == loaded_circuit
    assert session.baseline == loaded_circuit
    assert session.file_path == loaded_path
    assert get_save_status(session) == SaveStatus.CLEAN
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.simulation_result is None
    assert not session.can_undo
    assert not session.can_redo

    # establish_imported
    imported_circuit = Circuit(4, [GatePlacement(GateType.Y, [2], [], 0)])
    session.establish_imported(imported_circuit)
    assert session.circuit == imported_circuit
    assert session.baseline is None
    assert session.file_path is None
    assert get_save_status(session) == SaveStatus.DIRTY
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.simulation_result is None
    assert not session.can_undo
    assert not session.can_redo

    # mark_saved
    save_path = Path("/tmp/saved.qcs")
    session.mark_saved(save_path)
    assert session.baseline == imported_circuit
    assert session.file_path == save_path
    assert get_save_status(session) == SaveStatus.CLEAN

    # new()
    session.new()
    assert session.circuit == Circuit(2)
    assert session.baseline == Circuit(2)
    assert session.file_path is None
    assert get_save_status(session) == SaveStatus.CLEAN
    assert get_sim_status(session) == SimulationStatus.NONE
    assert not session.can_undo
    assert not session.can_redo


@pytest.mark.req("FR-1.45", "NFR-5.5")
def test_noop_and_rejected_operations_preserve_state() -> None:
    session = EditorSession()
    notifications = 0

    def on_change() -> None:
        nonlocal notifications
        notifications += 1

    session.subscribe(on_change)

    # Place an invalid gate (e.g. CNOT on bottom wire of 2-qubit circuit)
    invalid_result = place_gate(session.circuit, GateType.CNOT, 1, 0)
    assert invalid_result.status == "rejected"
    assert not session.apply(invalid_result)
    assert notifications == 0
    assert not session.can_undo
    assert get_save_status(session) == SaveStatus.CLEAN

    # Apply a valid gate
    valid_result = place_gate(session.circuit, GateType.H, 0, 0)
    assert valid_result.status == "applied"
    assert session.apply(valid_result)
    assert notifications == 1
    assert session.can_undo


@pytest.mark.req("LC-2", "NFR-5.5")
def test_circuit_mutated_then_restored_with_different_placement_order() -> None:
    session = EditorSession()
    # Baseline with two gates in column 0 and column 1
    p0 = GatePlacement(GateType.H, [0], [], 0)
    p1 = GatePlacement(GateType.X, [1], [], 1)
    baseline_circuit = Circuit(2, [p0, p1])
    session.establish_loaded(baseline_circuit, Path("/tmp/test.qcs"))
    assert get_save_status(session) == SaveStatus.CLEAN

    # Mutate session: e.g. delete gate p0
    session.apply(place_gate(session.circuit, GateType.Z, 0, 2))
    assert get_save_status(session) == SaveStatus.DIRTY

    # Mutate to a circuit containing [p1, p0] (different order)
    reversed_circuit = Circuit(2, [p1, p0])
    res = OperationResult(status="applied", circuit=reversed_circuit)
    session.apply(res)
    # Equality uses canonical ordering, so save_status must be CLEAN
    assert get_save_status(session) == SaveStatus.CLEAN
