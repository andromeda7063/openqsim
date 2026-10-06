"""Acceptance test for the end-to-end headless workflow."""

from pathlib import Path

import numpy as np
import pytest

import libqsim


@pytest.mark.req(
    "FR-3.1",
    "FR-3.2",
    "FR-3.3",
    "FR-3.4",
    "FR-5.1",
    "FR-5.4",
    "FR-6.4",
    "FR-6.13",
    "NFR-7.8",
)
def test_headless_bell_flow(tmp_path: Path) -> None:
    # 1. New session
    session = libqsim.EditorSession()
    assert session.save_status == libqsim.SaveStatus.CLEAN
    assert session.simulation_status == libqsim.SimulationStatus.NONE

    # 2. Place H on q0 and CNOT at wire 0 (control 0, target 1)
    res_h = libqsim.place_gate(session.circuit, libqsim.GateType.H, 0, 0)
    assert session.apply(res_h)

    res_cx = libqsim.place_gate(session.circuit, libqsim.GateType.CNOT, 0, 1)
    assert session.apply(res_cx)
    assert session.save_status == libqsim.SaveStatus.DIRTY

    # 3. Run simulation
    run_res = session.run()
    assert run_res.ok
    assert session.simulation_status == libqsim.SimulationStatus.CURRENT
    sim_result = session.simulation_result
    assert sim_result is not None

    # Check probabilities: Bell state (|00> and |11> at 0.5)
    probs = sim_result.probabilities
    assert len(probs) == 4
    assert np.isclose(probs[0], 0.5, atol=1e-9)  # |00>
    assert np.isclose(probs[1], 0.0, atol=1e-9)  # |01>
    assert np.isclose(probs[2], 0.0, atol=1e-9)  # |10>
    assert np.isclose(probs[3], 0.5, atol=1e-9)  # |11>

    # Check Bloch vectors (both at origin for entangled state)
    bloch = sim_result.bloch_vectors
    assert len(bloch) == 2
    assert np.allclose(bloch[0], [0.0, 0.0, 0.0], atol=1e-9)
    assert np.allclose(bloch[1], [0.0, 0.0, 0.0], atol=1e-9)

    # 4. Save to temp .qcs and load back
    qcs_path = tmp_path / "bell.qcs"
    save_res = session.save_as(qcs_path)
    assert save_res.ok
    assert session.save_status == libqsim.SaveStatus.CLEAN

    open_res = session.open(qcs_path)
    assert open_res.ok
    assert session.save_status == libqsim.SaveStatus.CLEAN
    assert session.simulation_status == libqsim.SimulationStatus.NONE

    # 5. Export OpenQASM
    qasm_text = libqsim.export_text(session.circuit)
    assert "h q[0];" in qasm_text
    assert "cx q[0],q[1];" in qasm_text

    # 6. Import OpenQASM into session
    imported_circuit = libqsim.import_text(qasm_text)
    session.establish_imported(imported_circuit)
    assert session.save_status == libqsim.SaveStatus.DIRTY

    # 7. Run again and assert probabilities match
    run_res2 = session.run()
    assert run_res2.ok
    sim_result2 = session.simulation_result
    assert sim_result2 is not None
    assert np.allclose(sim_result.probabilities, sim_result2.probabilities, atol=1e-9)
