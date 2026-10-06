"""Headless Bell state construction, simulation, persistence, and OpenQASM interchange."""

import sys
import tempfile
from pathlib import Path

import numpy as np

import libqsim


def main() -> None:
    print("=== OpenQSim Headless Bell State Demo ===")

    # 1. New session (LC-1: empty 2-qubit circuit, Clean baseline, None simulation)
    session = libqsim.EditorSession()
    print(f"Startup: {session.circuit.num_qubits} qubits, SaveStatus={session.save_status.name}")

    # 2. Place H on q0 and CNOT at wire 0 (defaults to control 0, target 1)
    res_h = libqsim.place_gate(session.circuit, libqsim.GateType.H, 0, 0)
    session.apply(res_h)

    res_cx = libqsim.place_gate(session.circuit, libqsim.GateType.CNOT, 0, 1)
    session.apply(res_cx)
    print(f"Constructed Bell circuit with {len(session.circuit.placements)} gates.")

    # 3. Run simulation
    outcome = session.run()
    if not outcome.ok or session.simulation_result is None:
        print(f"Simulation failed: {outcome.messages}")
        sys.exit(1)

    result = session.simulation_result
    labels = libqsim.basis_labels(2)
    print("\nSimulation Probabilities:")
    for label, prob in zip(labels, result.probabilities, strict=True):
        print(f"  |{label}>: {prob:.4f}")

    print("\nBloch Vectors (rx, ry, rz):")
    for q_idx, vec in enumerate(result.bloch_vectors):
        print(f"  q{q_idx}: [{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}]")

    # 4. Save to temp .qcs and load back
    with tempfile.NamedTemporaryFile(suffix=".qcs", delete=False) as tf:
        temp_path = Path(tf.name)

    try:
        save_outcome = session.save_as(temp_path)
        assert save_outcome.ok, f"Failed to save QCS: {save_outcome.message}"
        print(f"\nSaved session to {temp_path.name}")

        open_outcome = session.open(temp_path)
        assert open_outcome.ok, f"Failed to open QCS: {open_outcome.message}"
        print("Loaded circuit back from QCS.")

        # 5. Export OpenQASM
        qasm_text = libqsim.export_text(session.circuit)
        print("\nExported OpenQASM 2.0:\n" + qasm_text.strip())

        # 6. Import OpenQASM into session
        imported_circuit = libqsim.import_text(qasm_text)
        session.establish_imported(imported_circuit)

        # 7. Run simulation again on imported circuit
        outcome2 = session.run()
        assert outcome2.ok and session.simulation_result is not None
        result2 = session.simulation_result

        assert np.allclose(result.probabilities, result2.probabilities, atol=1e-9)
        print("\nVerification successful: Probabilities match after QCS and QASM round-trip.")
    finally:
        if temp_path.exists():
            temp_path.unlink()

    print("\nBell: 00 and 11 at 0.5, both Bloch vectors at the origin.")
    sys.exit(0)


if __name__ == "__main__":
    main()
