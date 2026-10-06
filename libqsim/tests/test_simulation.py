"""Comprehensive test suite for the Qiskit Aer simulation engine (FR-3.1..3.4, 3.9, 3.10, FR-2.12, NFR-7.1, 7.3, 7.7, 3.1)."""

import random
from unittest.mock import patch

import numpy as np
import pytest
from libqsim.domain.gates import GateType, matrix
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.simulation.engine import InvalidCircuitError, SimulationError, simulate


def _oracle_simulate(circuit: Circuit) -> np.ndarray:
    """Pure-numpy reference simulator under 40 lines (kron-based, qubit 0 is LSB)."""
    n = circuit.num_qubits
    psi = np.zeros(2**n, dtype=np.complex128)
    psi[0] = 1.0
    i2 = np.eye(2, dtype=np.complex128)
    p1 = np.array([[0, 0], [0, 1]], dtype=np.complex128)
    x_mat = matrix(GateType.X)
    assert x_mat is not None
    single_ops = {
        gt: matrix(gt)
        for gt in (GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T)
    }

    def _kron(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.asarray(np.kron(a, b), dtype=np.complex128)

    for p in sorted(circuit.placements, key=lambda g: (g.column, g.lowest_occupied_qubit or 0)):
        if p.gate_type == GateType.Measurement:
            continue
        if p.gate_type in single_ops:
            op = single_ops[p.gate_type]
            assert op is not None
            m = np.array([1], dtype=np.complex128)
            for q in reversed(range(n)):
                m = _kron(m, op if q == p.targets[0] else i2)
            psi = np.asarray(m @ psi, dtype=np.complex128)
        elif p.gate_type == GateType.CNOT:
            c, t = p.controls[0], p.targets[0]
            m = np.array([1], dtype=np.complex128)
            for q in reversed(range(n)):
                m = _kron(m, p1 if q == c else ((x_mat - i2) if q == t else i2))
            psi = np.asarray(psi + m @ psi, dtype=np.complex128)
        elif p.gate_type == GateType.Toffoli:
            c1, c2, t = p.controls[0], p.controls[1], p.targets[0]
            m = np.array([1], dtype=np.complex128)
            for q in reversed(range(n)):
                m = _kron(m, p1 if q in (c1, c2) else ((x_mat - i2) if q == t else i2))
            psi = np.asarray(psi + m @ psi, dtype=np.complex128)
    return psi


@pytest.fixture
def invalid_circuit_fixture() -> Circuit:
    """Fixture producing an invalid circuit with colliding gates."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.X, targets=[0], controls=[], column=0)
    return Circuit(num_qubits=2, placements=[p1, p2])


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.1", "NFR-7.7")
def test_single_qubit_reference_circuits() -> None:
    """Empty circuit, X, Y, H, H then H, and Z after H match exact literal statevectors."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)

    # Empty 1-qubit circuit -> [1, 0]
    res_empty = simulate(Circuit(num_qubits=1))
    ref_empty = np.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)
    assert np.allclose(res_empty.statevector, ref_empty, atol=1e-9)

    # X -> [0, 1]
    res_x = simulate(
        Circuit(
            num_qubits=1, placements=[GatePlacement(GateType.X, targets=[0], controls=[], column=0)]
        )
    )
    ref_x = np.array([0.0 + 0.0j, 1.0 + 0.0j], dtype=np.complex128)
    assert np.allclose(res_x.statevector, ref_x, atol=1e-9)

    # Y -> [0, i]
    res_y = simulate(
        Circuit(
            num_qubits=1, placements=[GatePlacement(GateType.Y, targets=[0], controls=[], column=0)]
        )
    )
    ref_y = np.array([0.0 + 0.0j, 1.0j], dtype=np.complex128)
    assert np.allclose(res_y.statevector, ref_y, atol=1e-9)

    # H -> [1/sqrt2, 1/sqrt2]
    res_h = simulate(
        Circuit(
            num_qubits=1, placements=[GatePlacement(GateType.H, targets=[0], controls=[], column=0)]
        )
    )
    ref_h = np.array([inv_sqrt2 + 0.0j, inv_sqrt2 + 0.0j], dtype=np.complex128)
    assert np.allclose(res_h.statevector, ref_h, atol=1e-9)

    # H then H -> [1, 0]
    res_hh = simulate(
        Circuit(
            num_qubits=1,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.H, targets=[0], controls=[], column=1),
            ],
        )
    )
    assert np.allclose(res_hh.statevector, ref_empty, atol=1e-9)

    # Z after H -> [1/sqrt2, -1/sqrt2]
    res_hz = simulate(
        Circuit(
            num_qubits=1,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.Z, targets=[0], controls=[], column=1),
            ],
        )
    )
    ref_hz = np.array([inv_sqrt2 + 0.0j, -inv_sqrt2 + 0.0j], dtype=np.complex128)
    assert np.allclose(res_hz.statevector, ref_hz, atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.1", "NFR-7.7")
def test_s_and_t_phases_on_plus_state() -> None:
    """S and T phases applied to H|0> match literal complex statevectors."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)

    # S on H|0> -> [1/sqrt2, i/sqrt2]
    res_s = simulate(
        Circuit(
            num_qubits=1,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.S, targets=[0], controls=[], column=1),
            ],
        )
    )
    ref_s = np.array([inv_sqrt2 + 0.0j, 1.0j * inv_sqrt2], dtype=np.complex128)
    assert np.allclose(res_s.statevector, ref_s, atol=1e-9)

    # T on H|0> -> [1/sqrt2, 0.5 + 0.5j]
    res_t = simulate(
        Circuit(
            num_qubits=1,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.T, targets=[0], controls=[], column=1),
            ],
        )
    )
    ref_t = np.array([inv_sqrt2 + 0.0j, 0.5 + 0.5j], dtype=np.complex128)
    assert np.allclose(res_t.statevector, ref_t, atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.3", "NFR-7.7")
def test_bell_state_probabilities() -> None:
    """Bell state has probabilities 0.5 at '00' and '11'."""
    c = Circuit(
        num_qubits=2,
        placements=[
            GatePlacement(GateType.H, targets=[0], controls=[], column=0),
            GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1),
        ],
    )
    res = simulate(c)
    assert np.isclose(res.probabilities[0], 0.5, atol=1e-9)
    assert np.isclose(res.probabilities[1], 0.0, atol=1e-9)
    assert np.isclose(res.probabilities[2], 0.0, atol=1e-9)
    assert np.isclose(res.probabilities[3], 0.5, atol=1e-9)
    assert np.isclose(float(np.sum(res.probabilities)), 1.0, atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.1", "NFR-7.7")
def test_cnot_both_orientations() -> None:
    """CNOT with control above target and target above control both function correctly."""
    # X on q0 + control q0, target q1 -> state |11> (index 3)
    c1 = Circuit(
        num_qubits=2,
        placements=[
            GatePlacement(GateType.X, targets=[0], controls=[], column=0),
            GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1),
        ],
    )
    res1 = simulate(c1)
    assert np.isclose(res1.probabilities[3], 1.0, atol=1e-9)

    # X on q1 + control q1, target q0 -> state |11> (index 3)
    c2 = Circuit(
        num_qubits=2,
        placements=[
            GatePlacement(GateType.X, targets=[1], controls=[], column=0),
            GatePlacement(GateType.CNOT, targets=[0], controls=[1], column=1),
        ],
    )
    res2 = simulate(c2)
    assert np.isclose(res2.probabilities[3], 1.0, atol=1e-9)

    # Control 1, target 0 does not fire when control is |0>
    c3 = Circuit(
        num_qubits=2,
        placements=[
            GatePlacement(GateType.X, targets=[0], controls=[], column=0),
            GatePlacement(GateType.CNOT, targets=[0], controls=[1], column=1),
        ],
    )
    res3 = simulate(c3)
    # Target q0 was 1, control q1 is 0 -> target stays 1, state is |01> (index 1)
    assert np.isclose(res3.probabilities[1], 1.0, atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.1", "NFR-7.7")
def test_toffoli_target_placements() -> None:
    """Toffoli with target on top, middle, and bottom wire fires only when both controls are 1."""
    configurations = [
        # (target, controls)
        (0, (1, 2)),  # top wire
        (1, (0, 2)),  # middle wire
        (2, (0, 1)),  # bottom wire
    ]

    for target, controls in configurations:
        c1, c2 = controls
        # Test all 4 control combinations: (0,0), (1,0), (0,1), (1,1)
        for val1 in (0, 1):
            for val2 in (0, 1):
                placements = []
                col = 0
                if val1 == 1:
                    placements.append(
                        GatePlacement(GateType.X, targets=[c1], controls=[], column=col)
                    )
                    col += 1
                if val2 == 1:
                    placements.append(
                        GatePlacement(GateType.X, targets=[c2], controls=[], column=col)
                    )
                    col += 1
                placements.append(
                    GatePlacement(GateType.Toffoli, targets=[target], controls=controls, column=col)
                )

                res = simulate(Circuit(num_qubits=3, placements=placements))
                # Expected target value: 1 if (val1 == 1 and val2 == 1) else 0
                expected_tgt = 1 if (val1 == 1 and val2 == 1) else 0
                expected_index = (expected_tgt << target) | (val1 << c1) | (val2 << c2)
                assert np.isclose(res.probabilities[expected_index], 1.0, atol=1e-9)


@pytest.mark.req("FR-3.3", "NFR-7.3", "NFR-7.7")
def test_three_qubit_basis_ordering() -> None:
    """3-qubit basis ordering puts highest-indexed qubit on the left: q0->'001', q2->'100'."""
    c0 = Circuit(
        num_qubits=3, placements=[GatePlacement(GateType.X, targets=[0], controls=[], column=0)]
    )
    res0 = simulate(c0)
    assert res0.basis_labels[1] == "001"
    assert np.isclose(res0.probabilities[1], 1.0, atol=1e-9)

    c2 = Circuit(
        num_qubits=3, placements=[GatePlacement(GateType.X, targets=[2], controls=[], column=0)]
    )
    res2 = simulate(c2)
    assert res2.basis_labels[4] == "100"
    assert np.isclose(res2.probabilities[4], 1.0, atol=1e-9)


@pytest.mark.req("FR-3.10", "NFR-7.7")
def test_measurement_ignored_by_simulation() -> None:
    """Measurement placed on a wire does not alter the simulated statevector."""
    c_no_meas = Circuit(
        num_qubits=2,
        placements=[GatePlacement(GateType.H, targets=[0], controls=[], column=0)],
    )
    c_with_meas = Circuit(
        num_qubits=2,
        placements=[
            GatePlacement(GateType.H, targets=[0], controls=[], column=0),
            GatePlacement(GateType.Measurement, targets=[0], controls=[], column=1),
        ],
    )

    res_no = simulate(c_no_meas)
    res_with = simulate(c_with_meas)

    assert np.allclose(res_no.statevector, res_with.statevector, atol=1e-9)
    assert np.allclose(res_no.probabilities, res_with.probabilities, atol=1e-9)


@pytest.mark.req("FR-3.9", "NFR-7.7")
def test_column_order_execution() -> None:
    """Gates execute in increasing column order: H then S differs from S then H."""
    c_hs = Circuit(
        num_qubits=1,
        placements=[
            GatePlacement(GateType.H, targets=[0], controls=[], column=0),
            GatePlacement(GateType.S, targets=[0], controls=[], column=1),
        ],
    )
    c_sh = Circuit(
        num_qubits=1,
        placements=[
            GatePlacement(GateType.S, targets=[0], controls=[], column=0),
            GatePlacement(GateType.H, targets=[0], controls=[], column=1),
        ],
    )

    res_hs = simulate(c_hs)
    res_sh = simulate(c_sh)

    assert not np.allclose(res_hs.statevector, res_sh.statevector, atol=1e-9)


@pytest.mark.req("FR-3.9", "NFR-7.3", "NFR-7.7")
def test_placement_list_order_invariance() -> None:
    """Same circuit with placements given in a different list order simulates identically."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1)
    p3 = GatePlacement(GateType.X, targets=[1], controls=[], column=2)

    c1 = Circuit(num_qubits=2, placements=[p1, p2, p3])
    c2 = Circuit(num_qubits=2, placements=[p3, p1, p2])

    res1 = simulate(c1)
    res2 = simulate(c2)

    assert np.allclose(res1.statevector, res2.statevector, atol=1e-9)
    assert np.allclose(res1.probabilities, res2.probabilities, atol=1e-9)


@pytest.mark.req("FR-3.4", "NFR-7.7")
def test_known_bloch_vectors() -> None:
    """Bloch vectors for H|0>, S H|0>, X|0>, |0>, and Bell match literal values."""
    # H|0> -> (1, 0, 0)
    res_h = simulate(
        Circuit(
            num_qubits=1, placements=[GatePlacement(GateType.H, targets=[0], controls=[], column=0)]
        )
    )
    assert np.allclose(res_h.bloch_vectors[0], (1.0, 0.0, 0.0), atol=1e-9)

    # S H|0> -> (0, 1, 0)
    res_sh = simulate(
        Circuit(
            num_qubits=1,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.S, targets=[0], controls=[], column=1),
            ],
        )
    )
    assert np.allclose(res_sh.bloch_vectors[0], (0.0, 1.0, 0.0), atol=1e-9)

    # X|0> -> (0, 0, -1)
    res_x = simulate(
        Circuit(
            num_qubits=1, placements=[GatePlacement(GateType.X, targets=[0], controls=[], column=0)]
        )
    )
    assert np.allclose(res_x.bloch_vectors[0], (0.0, 0.0, -1.0), atol=1e-9)

    # |0> -> (0, 0, 1)
    res_0 = simulate(Circuit(num_qubits=1))
    assert np.allclose(res_0.bloch_vectors[0], (0.0, 0.0, 1.0), atol=1e-9)

    # Bell q0 and q1 both (0, 0, 0)
    res_bell = simulate(
        Circuit(
            num_qubits=2,
            placements=[
                GatePlacement(GateType.H, targets=[0], controls=[], column=0),
                GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1),
            ],
        )
    )
    assert np.allclose(res_bell.bloch_vectors[0], (0.0, 0.0, 0.0), atol=1e-9)
    assert np.allclose(res_bell.bloch_vectors[1], (0.0, 0.0, 0.0), atol=1e-9)


@pytest.mark.req("FR-2.12", "NFR-3.1", "NFR-7.3")
def test_invalid_circuit_raises_and_never_invokes_aer(invalid_circuit_fixture: Circuit) -> None:
    """Invalid circuit raises InvalidCircuitError carrying error list and Aer is never invoked."""
    with patch("libqsim.simulation.engine.AerSimulator") as mock_aer:
        with pytest.raises(InvalidCircuitError) as exc_info:
            simulate(invalid_circuit_fixture)

        assert len(exc_info.value.errors) > 0
        mock_aer.assert_not_called()


@pytest.mark.req("NFR-3.1", "NFR-7.3")
def test_aer_exception_wrapped_in_simulation_error() -> None:
    """Aer exceptions are caught and wrapped in SimulationError with plain message and chained exc."""
    c = Circuit(num_qubits=1)
    with patch(
        "libqsim.simulation.engine.AerSimulator.run",
        side_effect=RuntimeError("Internal Aer simulation fault"),
    ):
        with pytest.raises(SimulationError) as exc_info:
            simulate(c)

        err = exc_info.value
        assert isinstance(err.__cause__, RuntimeError)
        # Message is plain and contains no traceback formatting
        msg = str(err)
        assert "Internal Aer simulation fault" in msg
        assert "Traceback" not in msg
        assert "\n" not in msg.strip()


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.3", "NFR-7.7")
def test_independent_oracle_cross_check() -> None:
    """Cross-check statevectors against pure-numpy independent oracle for 10 seeded random circuits."""
    rng = random.Random(1337)
    gate_types = [
        GateType.H,
        GateType.X,
        GateType.Y,
        GateType.Z,
        GateType.S,
        GateType.T,
        GateType.CNOT,
        GateType.Toffoli,
    ]

    for seed_i in range(10):
        n = rng.randint(1, 4)
        placements: list[GatePlacement] = []
        occupied: set[tuple[int, int]] = set()

        for col in range(5):
            available_wires = list(range(n))
            rng.shuffle(available_wires)

            while available_wires:
                gt = rng.choice(gate_types)
                if gt in (GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T):
                    wire = available_wires.pop()
                    placements.append(GatePlacement(gt, targets=[wire], controls=[], column=col))
                    occupied.add((wire, col))
                elif gt == GateType.CNOT and n >= 2 and len(available_wires) >= 2:
                    # Contiguous wires
                    valid_pairs = [
                        (w, w + 1)
                        for w in range(n - 1)
                        if w in available_wires and (w + 1) in available_wires
                    ]
                    if valid_pairs:
                        w1, w2 = rng.choice(valid_pairs)
                        available_wires.remove(w1)
                        available_wires.remove(w2)
                        c, t = (w1, w2) if rng.random() < 0.5 else (w2, w1)
                        placements.append(
                            GatePlacement(GateType.CNOT, targets=[t], controls=[c], column=col)
                        )
                        occupied.add((w1, col))
                        occupied.add((w2, col))
                elif gt == GateType.Toffoli and n >= 3 and len(available_wires) >= 3:
                    valid_triples = [
                        (w, w + 1, w + 2)
                        for w in range(n - 2)
                        if w in available_wires
                        and (w + 1) in available_wires
                        and (w + 2) in available_wires
                    ]
                    if valid_triples:
                        w1, w2, w3 = rng.choice(valid_triples)
                        available_wires.remove(w1)
                        available_wires.remove(w2)
                        available_wires.remove(w3)
                        wires = [w1, w2, w3]
                        rng.shuffle(wires)
                        t = wires.pop()
                        c1, c2 = sorted(wires)
                        placements.append(
                            GatePlacement(
                                GateType.Toffoli, targets=[t], controls=[c1, c2], column=col
                            )
                        )
                        occupied.add((w1, col))
                        occupied.add((w2, col))
                        occupied.add((w3, col))

        circuit = Circuit(num_qubits=n, placements=placements)
        res_engine = simulate(circuit)
        ref_sv = _oracle_simulate(circuit)

        assert np.allclose(res_engine.statevector, ref_sv, atol=1e-9), (
            f"Failed on seeded circuit {seed_i}"
        )


@pytest.mark.req("FR-3.1", "FR-3.2", "NFR-7.3", "NFR-7.7")
@pytest.mark.perf
def test_ten_qubit_smoke() -> None:
    """10-qubit circuit with 100 gates simulates and probabilities sum to 1."""
    placements: list[GatePlacement] = []
    # 50 columns with 2 single-qubit gates each = 100 gates
    for col in range(50):
        q1 = (col * 2) % 10
        q2 = (col * 2 + 1) % 10
        placements.append(GatePlacement(GateType.H, targets=[q1], controls=[], column=col))
        placements.append(GatePlacement(GateType.X, targets=[q2], controls=[], column=col))

    c = Circuit(num_qubits=10, placements=placements)
    res = simulate(c)

    assert res.num_qubits == 10
    assert len(res.statevector) == 1024
    assert len(res.probabilities) == 1024
    assert len(res.bloch_vectors) == 10
    assert np.isclose(float(np.sum(res.probabilities)), 1.0, atol=1e-9)
