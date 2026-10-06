"""Tests for OpenQASM 2.0 importer, exporter, and independent Qiskit oracle."""

import random

import numpy as np
import pytest
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.qasm.exporter import export_text
from libqsim.qasm.importer import QasmError, import_text
from libqsim.simulation.engine import simulate
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.quantum_info import Statevector  # type: ignore[import-untyped]


@pytest.mark.req("FR-6.13")
def test_bell_circuit_export_literal() -> None:
    c = Circuit(
        2,
        [
            GatePlacement(GateType.H, [0], [], 0),
            GatePlacement(GateType.CNOT, [1], [0], 1),
        ],
    )
    expected = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n'
    assert export_text(c) == expected


@pytest.mark.req("FR-6.14", "FR-6.15")
def test_ordering_example_from_doc() -> None:
    # From docs/qasm-support.md Ordering Example:
    # column 0: H on q1
    # column 0: X on q0
    # column 1: CNOT, control q0, target q1
    c = Circuit(
        2,
        [
            GatePlacement(GateType.H, [1], [], 0),
            GatePlacement(GateType.X, [0], [], 0),
            GatePlacement(GateType.CNOT, [1], [0], 1),
        ],
    )
    expected = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nx q[0];\nh q[1];\ncx q[0],q[1];\n'
    assert export_text(c) == expected


@pytest.mark.req("FR-6.1", "FR-6.2", "FR-6.13")
def test_measurement_export_and_import() -> None:
    c = Circuit(
        2,
        [
            GatePlacement(GateType.H, [0], [], 0),
            GatePlacement(GateType.Measurement, [0], [], 1),
        ],
    )
    text = export_text(c)
    expected = (
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "qreg q[2];\n"
        "creg c[2];\n"
        "h q[0];\n"
        "measure q[0] -> c[0];\n"
    )
    assert text == expected
    imported = import_text(text)
    assert imported.num_qubits == 2
    assert len(imported.placements) == 2


@pytest.mark.req("FR-6.4", "FR-6.5")
def test_import_export_import_roundtrip_preserves_semantics() -> None:
    c1 = Circuit(
        3,
        [
            GatePlacement(GateType.H, [0], [], 0),
            GatePlacement(GateType.X, [1], [], 0),
            GatePlacement(GateType.CNOT, [1], [0], 2),
            GatePlacement(GateType.Toffoli, [2], [0, 1], 5),
            GatePlacement(GateType.S, [2], [], 6),
            GatePlacement(GateType.T, [0], [], 7),
        ],
    )
    exported = export_text(c1)
    imported = import_text(exported)
    assert imported.num_qubits == c1.num_qubits
    sim1 = simulate(c1)
    sim2 = simulate(imported)
    assert np.allclose(sim1.statevector, sim2.statevector, atol=1e-9)


@pytest.mark.req("FR-6.3", "FR-6.13", "NFR-5.4", "NFR-7.6")
def test_qiskit_independent_oracle() -> None:
    import qiskit.qasm2  # type: ignore[import-untyped]

    rng = random.Random(12345)
    gates_1q = [GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T]

    for _ in range(30):
        num_qubits = rng.randint(2, 4)
        placements: list[GatePlacement] = []
        occupied: set[tuple[int, int]] = set()

        col = 0
        for _ in range(6):
            q = rng.randint(0, num_qubits - 1)
            if (q, col) not in occupied:
                gt = rng.choice(gates_1q)
                placements.append(GatePlacement(gt, [q], [], col))
                occupied.add((q, col))
            col += 1

        # Add a CNOT
        c_wire = rng.randint(0, num_qubits - 2)
        t_wire = c_wire + 1
        if rng.choice([True, False]):
            c_wire, t_wire = t_wire, c_wire
        placements.append(GatePlacement(GateType.CNOT, [t_wire], [c_wire], col))
        col += 1

        circuit = Circuit(num_qubits, placements)
        qasm_str = export_text(circuit)

        # Qiskit parse and simulate
        qc = qiskit.qasm2.loads(qasm_str)
        sv_qiskit = np.asarray(Statevector.from_instruction(qc).data, dtype=np.complex128)

        # libqsim simulate
        sim_res = simulate(circuit)
        assert np.allclose(sim_res.statevector, sv_qiskit, atol=1e-9)

    # Hand-built Qiskit circuits
    # cx(0, 1)
    qc1 = QuantumCircuit(2)
    qc1.h(0)
    qc1.cx(0, 1)
    c_imp1 = import_text(qiskit.qasm2.dumps(qc1))
    sv1_expected = np.asarray(Statevector.from_instruction(qc1).data, dtype=np.complex128)
    assert np.allclose(simulate(c_imp1).statevector, sv1_expected, atol=1e-9)

    # cx(1, 0)
    qc2 = QuantumCircuit(2)
    qc2.h(1)
    qc2.cx(1, 0)
    c_imp2 = import_text(qiskit.qasm2.dumps(qc2))
    sv2_expected = np.asarray(Statevector.from_instruction(qc2).data, dtype=np.complex128)
    assert np.allclose(simulate(c_imp2).statevector, sv2_expected, atol=1e-9)

    # ccx(0, 2, 1) -> target is 1 (middle wire), controls are 0 and 2
    qc3 = QuantumCircuit(3)
    qc3.h(0)
    qc3.h(2)
    qc3.ccx(0, 2, 1)
    c_imp3 = import_text(qiskit.qasm2.dumps(qc3))
    sv3_expected = np.asarray(Statevector.from_instruction(qc3).data, dtype=np.complex128)
    assert np.allclose(simulate(c_imp3).statevector, sv3_expected, atol=1e-9)


@pytest.mark.req(
    "FR-6.6",
    "FR-6.7",
    "FR-6.8",
    "FR-6.9",
    "FR-6.10",
    "FR-6.16",
    "NFR-3.1",
)
@pytest.mark.parametrize(
    ("bad_qasm", "construct", "line_num"),
    [
        ('include "qelib1.inc";\nqreg q[2];\n', "OPENQASM 2.0", 1),
        ("OPENQASM 2.0;\nqreg q[2];\nh q[0];\n", "include", 2),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg foo[2];\n', "foo", 3),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[0];\n', "qreg", 3),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[11];\n', "10 qubits", 3),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nqreg q2[2];\n', "second qreg", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q;\n', "whole-register", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nsdg q[0];\n', "sdg", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ntdg q[0];\n', "tdg", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nrx(0.5) q[0];\n', "rx", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nrz(0.5) q[0];\n', "rz", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nbarrier q[0];\n', "barrier", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nreset q[0];\n', "reset", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nopaque foo q;\n', "opaque", 4),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ngate mygate a { h a; }\n',
            "gate",
            4,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nif (c==1) h q[0];\n',
            "if",
            5,
        ),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[5];\n', "out-of-range", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncx q[0],q[0];\n', "repeated", 4),
        ('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncx q[0],q[2];\n', "contiguous", 4),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[4];\nccx q[0],q[1],q[3];\n',
            "contiguous",
            4,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[1];\nmeasure q[0] -> c[0];\n',
            "classical register",
            4,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nmeasure q[0] -> c[0];\n',
            "classical register",
            4,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nmeasure q[0] -> c[1];\n',
            "mapping",
            5,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nmeasure q[0] -> c[0];\nmeasure q[0] -> c[0];\n',
            "second measure",
            6,
        ),
        (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nmeasure q[0] -> c[0];\nx q[0];\n',
            "after measurement",
            6,
        ),
    ],
)
def test_rejected_constructs_name_construct_and_line_number(
    bad_qasm: str,
    construct: str,
    line_num: int,
) -> None:
    with pytest.raises(QasmError) as exc_info:
        import_text(bad_qasm)
    msg = str(exc_info.value)
    assert construct.lower() in msg.lower()
    assert f"line {line_num}" in msg.lower()


@pytest.mark.req("FR-6.16")
def test_operation_count_limit_50_accepted_51_rejected() -> None:
    # 50 single-qubit gates
    ops_50 = ["OPENQASM 2.0;", 'include "qelib1.inc";', "qreg q[1];"] + ["h q[0];"] * 50
    c50 = import_text("\n".join(ops_50))
    assert len(c50.placements) == 50

    # 51 single-qubit gates
    ops_51 = ["OPENQASM 2.0;", 'include "qelib1.inc";', "qreg q[1];"] + ["h q[0];"] * 51
    with pytest.raises(QasmError) as exc:
        import_text("\n".join(ops_51))
    assert "50" in str(exc.value) or "limit" in str(exc.value).lower()
