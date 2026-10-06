"""Unit tests for EditorSession file operations (save, save_as, open)."""

import os
from pathlib import Path

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.persistence.qcs import write


def get_save_status(session: EditorSession) -> SaveStatus:
    return session.save_status


def get_sim_status(session: EditorSession) -> SimulationStatus:
    return session.simulation_status


@pytest.mark.req("LC-16", "FR-5.13")
def test_session_save_without_path_reports_needs_path() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    res = session.save()
    assert not res.ok
    assert res.needs_path
    assert get_save_status(session) == SaveStatus.DIRTY


@pytest.mark.req("LC-6", "LC-17", "FR-5.1", "FR-5.12")
def test_session_save_as_and_save(tmp_path: Path) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    file_path = tmp_path / "saved.qcs"

    res = session.save_as(file_path)
    assert res.ok
    assert session.file_path == file_path
    assert get_save_status(session) == SaveStatus.CLEAN
    assert session.baseline == session.circuit

    # Mutate again
    session.apply(place_gate(session.circuit, GateType.X, 1, 1))
    assert get_save_status(session) == SaveStatus.DIRTY

    # Save to established path
    res2 = session.save()
    assert res2.ok
    assert get_save_status(session) == SaveStatus.CLEAN
    assert session.baseline == session.circuit


@pytest.mark.req("LC-9", "FR-5.4", "FR-5.7", "NFR-5.3")
def test_session_open_success(tmp_path: Path) -> None:
    # Prepare a file on disk
    disc_c = Circuit(3, [GatePlacement(GateType.X, [2], [], 0)])
    disc_path = tmp_path / "on_disk.qcs"
    write(disc_path, disc_c)

    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.run()
    assert get_sim_status(session) == SimulationStatus.CURRENT

    # Open file
    res = session.open(disc_path)
    assert res.ok
    assert session.circuit == disc_c
    assert session.baseline == disc_c
    assert session.file_path == disc_path
    assert get_save_status(session) == SaveStatus.CLEAN
    assert get_sim_status(session) == SimulationStatus.NONE
    assert session.simulation_result is None
    assert not session.can_undo
    assert not session.can_redo


@pytest.mark.req("LC-11", "FR-5.8", "FR-5.14", "NFR-3.5")
def test_session_open_failure_preserves_state(tmp_path: Path) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    session.run()
    initial_circuit = session.circuit
    initial_result = session.simulation_result
    initial_can_undo = session.can_undo

    # Try opening a non-existent file
    res = session.open(tmp_path / "missing.qcs")
    assert not res.ok
    assert session.circuit == initial_circuit
    assert session.simulation_result is initial_result
    assert get_sim_status(session) == SimulationStatus.CURRENT
    assert get_save_status(session) == SaveStatus.DIRTY
    assert session.can_undo == initial_can_undo
    assert session.file_path is None

    # Try opening an invalid JSON file
    bad_file = tmp_path / "bad.qcs"
    bad_file.write_text("not json", encoding="utf-8")
    res2 = session.open(bad_file)
    assert not res2.ok
    assert session.circuit == initial_circuit
    assert session.simulation_result is initial_result
    assert get_sim_status(session) == SimulationStatus.CURRENT


@pytest.mark.req("FR-5.10", "NFR-3.3")
def test_session_save_failure_preserves_state(tmp_path: Path) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, 0, 0))
    ro_dir = tmp_path / "ro"
    ro_dir.mkdir()
    target_file = ro_dir / "target.qcs"
    os.chmod(ro_dir, 0o555)

    try:
        res = session.save_as(target_file)
        assert not res.ok
        assert session.file_path is None
        assert get_save_status(session) == SaveStatus.DIRTY
    finally:
        os.chmod(ro_dir, 0o755)
