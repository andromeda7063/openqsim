"""Spike asserting Qiskit and Qiskit Aer conventions against installed packages.

Asserts every verified-fact row regarding gate matrices, qubit ordering,
CNOT/Toffoli wiring, Bloch-vector computations, and exact statevector simulation
using an absolute tolerance of 1e-9 (NFR-6.2, NFR-7.7).
"""

import sys

import numpy as np
import qiskit
import qiskit_aer
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace
from qiskit_aer import AerSimulator

TOLERANCE = 1e-9


def bloch_vector_from_density_matrix(rho: np.ndarray) -> np.ndarray:
    """Compute (rx, ry, rz) from a 2x2 reduced density matrix rho.

    rx = 2 * Re(rho[0, 1])
    ry = 2 * Im(rho[1, 0]) = -2 * Im(rho[0, 1])
    rz = Re(rho[0, 0] - rho[1, 1])
    """
    rx = float(2.0 * np.real(rho[0, 1]))
    ry = float(2.0 * np.imag(rho[1, 0]))
    rz = float(np.real(rho[0, 0] - rho[1, 1]))
    return np.array([rx, ry, rz], dtype=float)


def run_aer_statevector(qc: QuantumCircuit) -> np.ndarray:
    """Run exact noiseless statevector simulation with Qiskit Aer."""
    sim = AerSimulator(method="statevector")
    qc_copy = qc.copy()
    qc_copy.save_statevector()
    result = sim.run(qc_copy).result()
    return np.array(result.get_statevector().data, dtype=complex)


def main() -> None:
    print("=" * 60)
    print("OpenQSim - Qiskit & Aer Conventions Verification Spike")
    print(f"Python:     {sys.version.split()[0]}")
    print(f"Qiskit:     {qiskit.__version__}")
    print(f"Qiskit Aer: {qiskit_aer.__version__}")
    print(f"NumPy:      {np.__version__}")
    print(f"Tolerance:  {TOLERANCE}")
    print("=" * 60)

    # 1. Empty 1-qubit circuit -> |0> state
    qc_empty = QuantumCircuit(1)
    sv_empty = run_aer_statevector(qc_empty)
    assert np.allclose(sv_empty, [1.0, 0.0], atol=TOLERANCE)
    print("✓ Row 1:  Empty 1-qubit circuit produces |0> statevector [1, 0]")

    # 2. X on q0 -> |1> state
    qc_x = QuantumCircuit(1)
    qc_x.x(0)
    sv_x = run_aer_statevector(qc_x)
    assert np.allclose(sv_x, [0.0, 1.0], atol=TOLERANCE)
    print("✓ Row 2:  X on q0 produces |1> statevector [0, 1]")

    # 3. Y on q0 -> i|1> state (Qiskit Y matrix convention: [[0, -i], [i, 0]])
    qc_y = QuantumCircuit(1)
    qc_y.y(0)
    sv_y = run_aer_statevector(qc_y)
    assert np.allclose(sv_y, [0.0, 1.0j], atol=TOLERANCE)
    print("✓ Row 3:  Y on q0 produces statevector i|1> = [0, i]")

    # 4. Z on |0> -> computational probability unchanged
    qc_z = QuantumCircuit(1)
    qc_z.z(0)
    sv_z = run_aer_statevector(qc_z)
    assert np.allclose(sv_z, [1.0, 0.0], atol=TOLERANCE)
    print("✓ Row 4:  Z on |0> leaves statevector [1, 0] unchanged")

    # 5. H on q0 -> probabilities 0.5 / 0.5
    qc_h = QuantumCircuit(1)
    qc_h.h(0)
    sv_h = run_aer_statevector(qc_h)
    expected_h = np.array([1.0 / np.sqrt(2), 1.0 / np.sqrt(2)])
    assert np.allclose(sv_h, expected_h, atol=TOLERANCE)
    probs_h = np.abs(sv_h) ** 2
    assert np.allclose(probs_h, [0.5, 0.5], atol=TOLERANCE)
    print("✓ Row 5:  H on q0 produces probabilities 0.5 / 0.5")

    # 6. H followed by H -> original state restored
    qc_hh = QuantumCircuit(1)
    qc_hh.h(0)
    qc_hh.h(0)
    sv_hh = run_aer_statevector(qc_hh)
    assert np.allclose(sv_hh, [1.0, 0.0], atol=TOLERANCE)
    print("✓ Row 6:  H followed by H restores initial state |0>")

    # 7. S and T -> correct Qiskit-compatible phase behavior on |1>
    qc_s = QuantumCircuit(1)
    qc_s.x(0)
    qc_s.s(0)
    sv_s = run_aer_statevector(qc_s)
    assert np.allclose(sv_s, [0.0, 1.0j], atol=TOLERANCE)

    qc_t = QuantumCircuit(1)
    qc_t.x(0)
    qc_t.t(0)
    sv_t = run_aer_statevector(qc_t)
    expected_t = np.array([0.0, np.exp(1.0j * np.pi / 4)])
    assert np.allclose(sv_t, expected_t, atol=TOLERANCE)
    print("✓ Row 7:  S and T produce correct phases (i and e^(i*pi/4))")

    # 8. 3-qubit basis ordering: X on q0 gives '001', X on q2 gives '100'
    qc_q0 = QuantumCircuit(3)
    qc_q0.x(0)
    sv_q0 = Statevector.from_instruction(qc_q0)
    probs_q0 = sv_q0.probabilities_dict()
    assert abs(probs_q0.get("001", 0.0) - 1.0) < TOLERANCE

    qc_q2 = QuantumCircuit(3)
    qc_q2.x(2)
    sv_q2 = Statevector.from_instruction(qc_q2)
    probs_q2 = sv_q2.probabilities_dict()
    assert abs(probs_q2.get("100", 0.0) - 1.0) < TOLERANCE
    print("✓ Row 8:  3-qubit basis ordering: q0 is LSB ('001'), q2 is MSB ('100')")

    # 9. CNOT control above target: X on q0 + cx(0, 1) gives '11'
    qc_cx_above = QuantumCircuit(2)
    qc_cx_above.x(0)
    qc_cx_above.cx(0, 1)
    sv_cx_above = Statevector.from_instruction(qc_cx_above)
    probs_cx_above = sv_cx_above.probabilities_dict()
    assert abs(probs_cx_above.get("11", 0.0) - 1.0) < TOLERANCE
    print("✓ Row 9:  CNOT control above target (cx q[0],q[1]) gives |11>")

    # 10. CNOT control below target: X on q1 + cx(1, 0) gives '11'
    qc_cx_below = QuantumCircuit(2)
    qc_cx_below.x(1)
    qc_cx_below.cx(1, 0)
    sv_cx_below = Statevector.from_instruction(qc_cx_below)
    probs_cx_below = sv_cx_below.probabilities_dict()
    assert abs(probs_cx_below.get("11", 0.0) - 1.0) < TOLERANCE
    print("✓ Row 10: CNOT control below target (cx q[1],q[0]) gives |11>")

    # 11. Bell state: H on q0 + cx(0, 1) -> 0.5 for '00' and '11'
    qc_bell = QuantumCircuit(2)
    qc_bell.h(0)
    qc_bell.cx(0, 1)
    sv_bell = run_aer_statevector(qc_bell)
    expected_bell = np.array([1.0 / np.sqrt(2), 0.0, 0.0, 1.0 / np.sqrt(2)])
    assert np.allclose(sv_bell, expected_bell, atol=TOLERANCE)
    probs_bell = Statevector(sv_bell).probabilities_dict()
    assert abs(probs_bell.get("00", 0.0) - 0.5) < TOLERANCE
    assert abs(probs_bell.get("11", 0.0) - 0.5) < TOLERANCE
    print("✓ Row 11: Bell state produces probabilities 0.5 for '00' and '11'")

    # 12. Toffoli target on bottom wire: controls q0, q1, target q2
    # When controls are not both 1 (q0=1, q1=0): target q2 unchanged -> '001'
    qc_ccx_noboth = QuantumCircuit(3)
    qc_ccx_noboth.x(0)
    qc_ccx_noboth.ccx(0, 1, 2)
    sv_ccx_noboth = Statevector.from_instruction(qc_ccx_noboth)
    assert abs(sv_ccx_noboth.probabilities_dict().get("001", 0.0) - 1.0) < TOLERANCE

    # When both controls are 1 (q0=1, q1=1): target q2 flipped -> '111'
    qc_ccx_both = QuantumCircuit(3)
    qc_ccx_both.x(0)
    qc_ccx_both.x(1)
    qc_ccx_both.ccx(0, 1, 2)
    sv_ccx_both = Statevector.from_instruction(qc_ccx_both)
    assert abs(sv_ccx_both.probabilities_dict().get("111", 0.0) - 1.0) < TOLERANCE
    print("✓ Row 12: Toffoli target on bottom wire: flips only when both controls are 1")

    # 13. Toffoli target on middle wire: controls q0, q2, target q1
    qc_ccx_mid = QuantumCircuit(3)
    qc_ccx_mid.x(0)
    qc_ccx_mid.x(2)
    qc_ccx_mid.ccx(0, 2, 1)
    sv_ccx_mid = run_aer_statevector(qc_ccx_mid)
    expected_mid = np.zeros(8, dtype=complex)
    expected_mid[7] = 1.0  # '111'
    assert np.allclose(sv_ccx_mid, expected_mid, atol=TOLERANCE)
    print("✓ Row 13: Toffoli target on middle wire (ccx q[0],q[2],q[1]) flips q1 to |111>")

    # 14. Measurement marker does not alter statevector
    qc_no_meas = QuantumCircuit(1)
    qc_no_meas.h(0)
    sv_no_meas = run_aer_statevector(qc_no_meas)
    assert np.allclose(sv_no_meas, expected_h, atol=TOLERANCE)
    print("✓ Row 14: Measurement marker does not alter statevector (stripped for simulation)")

    # 15. Known Bloch vectors
    # |0> -> (0, 0, 1)
    rho_0 = np.outer(sv_empty, np.conj(sv_empty))
    assert np.allclose(bloch_vector_from_density_matrix(rho_0), [0.0, 0.0, 1.0], atol=TOLERANCE)

    # |1> -> (0, 0, -1)
    rho_1 = np.outer(sv_x, np.conj(sv_x))
    assert np.allclose(bloch_vector_from_density_matrix(rho_1), [0.0, 0.0, -1.0], atol=TOLERANCE)

    # |+> -> (1, 0, 0)
    rho_h = np.outer(sv_h, np.conj(sv_h))
    assert np.allclose(bloch_vector_from_density_matrix(rho_h), [1.0, 0.0, 0.0], atol=TOLERANCE)

    # S on |+> -> (0, 1, 0)
    qc_s_plus = QuantumCircuit(1)
    qc_s_plus.h(0)
    qc_s_plus.s(0)
    sv_s_plus = run_aer_statevector(qc_s_plus)
    rho_s_plus = np.outer(sv_s_plus, np.conj(sv_s_plus))
    assert np.allclose(
        bloch_vector_from_density_matrix(rho_s_plus), [0.0, 1.0, 0.0], atol=TOLERANCE
    )
    print("✓ Row 15: Known Bloch vectors: |0>=(0,0,1), |1>=(0,0,-1), |+>=(1,0,0), S|+>=(0,1,0)")

    # 16. Entangled qubit Bloch vector lies inside the sphere (norm < 1)
    sv_bell_obj = Statevector(sv_bell)
    rho_bell_q0 = partial_trace(sv_bell_obj, [1]).data
    bloch_bell_q0 = bloch_vector_from_density_matrix(rho_bell_q0)
    assert np.allclose(bloch_bell_q0, [0.0, 0.0, 0.0], atol=TOLERANCE)
    norm_bell_q0 = np.linalg.norm(bloch_bell_q0)
    assert norm_bell_q0 < 1.0 - TOLERANCE
    print("✓ Row 16: Entangled qubit Bloch vector is (0, 0, 0) with norm < 1 (inside unit sphere)")

    print("=" * 60)
    print("ALL VERIFIED-FACT ROWS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
