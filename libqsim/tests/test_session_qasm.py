"""Unit tests for EditorSession OpenQASM import and export."""

from pathlib import Path

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.gates import GateType


def get_save_status(session: EditorSession) -> SaveStatus:
    return session.save_status


def get_sim_status(session: EditorSession) -> SimulationStatus:
    return session.simulation_status


@pytest.mark.req("LC-10", "FR-6.11", "NFR-5.4")
def test_session_import_qasm_success(tmp_path: Path) -> None:
    qasm_file = tmp_path / "circuit.qasm"
    qasm_file.write_text(
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n',
        encoding="utf-8",
    )

    session = EditorSession()
    # Establish existing baseline
    session.apply(place_gate(session.circuit, GateType.X, 0, 0))
    session.mark_saved(tmp_path / "orig.qcs")
    session.run()
    assert get_save_status(session) == SaveStatus.CLEAN
    assert get_sim_status(session) == SimulationStatus.CURRENT

    # Import replaces session with unsaved session
    res = session.import_qasm(qasm_file)
    assert res.ok
    assert session.file_path is None
    assert get_save_status(session) == SaveStatus.DIRTY
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.simulation_result is None
    assert not session.can_undo
    assert not session.can_redo
    assert len(session.circuit.placements) == 2


@pytest.mark.req("LC-11", "FR-6.11", "NFR-3.5")
def test_session_import_qasm_failure_preserves_state(tmp_path: Path) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.run()
    initial_circuit = session.circuit
    initial_result = session.simulation_result
    initial_can_undo = session.can_undo

    # Bad QASM file
    bad_file = tmp_path / "bad.qasm"
    bad_file.write_text("invalid qasm", encoding="utf-8")

    res = session.import_qasm(bad_file)
    assert not res.ok
    assert session.circuit == initial_circuit
    assert session.simulation_result is initial_result
    assert get_sim_status(session) == SimulationStatus.CURRENT
    assert get_save_status(session) == SaveStatus.DIRTY
    assert session.can_undo == initial_can_undo
    assert session.file_path is None


@pytest.mark.req("FR-6.12", "FR-1.14")
def test_session_export_qasm_preserves_statuses_and_history(tmp_path: Path) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.run()

    save_status_before = get_save_status(session)
    sim_status_before = get_sim_status(session)
    can_undo_before = session.can_undo

    export_path = tmp_path / "exported.qasm"
    res = session.export_qasm(export_path)
    assert res.ok
    assert export_path.exists()

    # Statuses and history untouched
    assert get_save_status(session) == save_status_before
    assert get_sim_status(session) == sim_status_before
    assert session.can_undo == can_undo_before
