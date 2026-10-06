"""Tests for gate definitions, arities, and action matrices."""

import numpy as np
import pytest
from libqsim.domain.gates import GATE_ARITY, GateType, matrix
from qiskit.circuit.library import (  # type: ignore[import-untyped]
    HGate,
    SGate,
    TGate,
    XGate,
    YGate,
    ZGate,
)


def test_gate_type_values_and_round_trip() -> None:
    """GateType members match the exact required string values and round-trip."""
    expected_members = {
        "H": "H",
        "X": "X",
        "Y": "Y",
        "Z": "Z",
        "S": "S",
        "T": "T",
        "CNOT": "CNOT",
        "Toffoli": "Toffoli",
        "Measurement": "Measurement",
    }
    assert len(GateType) == 9
    for name, value in expected_members.items():
        member = GateType[name]
        assert member.value == value
        assert GateType(value) is member
        assert member == value

    # GateType("Toffoli") explicitly works
    assert GateType("Toffoli") is GateType.Toffoli


def test_gate_type_unknown_string_raises() -> None:
    """Constructing GateType with an unknown string raises ValueError."""
    with pytest.raises(ValueError):
        GateType("UNKNOWN")

    with pytest.raises(ValueError):
        GateType("cnot")  # Case sensitivity


def test_gate_arity_table() -> None:
    """GATE_ARITY defines (num_targets, num_controls) for all 9 supported gate types."""
    assert len(GATE_ARITY) == 9

    single_qubit_gates = [
        GateType.H,
        GateType.X,
        GateType.Y,
        GateType.Z,
        GateType.S,
        GateType.T,
        GateType.Measurement,
    ]
    for gt in single_qubit_gates:
        assert GATE_ARITY[gt] == (1, 0)

    assert GATE_ARITY[GateType.CNOT] == (1, 1)
    assert GATE_ARITY[GateType.Toffoli] == (1, 2)


def test_matrices_match_literal_references() -> None:
    """Matrices match literal complex reference matrices."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    ref_h = np.array(
        [[inv_sqrt2, inv_sqrt2], [inv_sqrt2, -inv_sqrt2]],
        dtype=np.complex128,
    )
    ref_x = np.array(
        [[0.0, 1.0], [1.0, 0.0]],
        dtype=np.complex128,
    )
    ref_y = np.array(
        [[0.0, -1.0j], [1.0j, 0.0]],
        dtype=np.complex128,
    )
    ref_z = np.array(
        [[1.0, 0.0], [0.0, -1.0]],
        dtype=np.complex128,
    )
    ref_s = np.array(
        [[1.0, 0.0], [0.0, 1.0j]],
        dtype=np.complex128,
    )
    ref_t = np.array(
        [[1.0, 0.0], [0.0, (1.0 + 1.0j) * inv_sqrt2]],
        dtype=np.complex128,
    )

    mat_h = matrix(GateType.H)
    assert mat_h is not None
    assert np.allclose(mat_h, ref_h, atol=1e-9)

    mat_x = matrix(GateType.X)
    assert mat_x is not None
    assert np.allclose(mat_x, ref_x, atol=1e-9)

    mat_y = matrix(GateType.Y)
    assert mat_y is not None
    assert np.allclose(mat_y, ref_y, atol=1e-9)

    mat_z = matrix(GateType.Z)
    assert mat_z is not None
    assert np.allclose(mat_z, ref_z, atol=1e-9)

    mat_s = matrix(GateType.S)
    assert mat_s is not None
    assert np.allclose(mat_s, ref_s, atol=1e-9)

    mat_t = matrix(GateType.T)
    assert mat_t is not None
    assert np.allclose(mat_t, ref_t, atol=1e-9)


def test_matrices_match_qiskit_definitions() -> None:
    """Single-qubit gate matrices match Qiskit's own to_matrix() definitions."""
    mat_h = matrix(GateType.H)
    assert mat_h is not None
    assert np.allclose(mat_h, HGate().to_matrix(), atol=1e-9)

    mat_x = matrix(GateType.X)
    assert mat_x is not None
    assert np.allclose(mat_x, XGate().to_matrix(), atol=1e-9)

    mat_y = matrix(GateType.Y)
    assert mat_y is not None
    assert np.allclose(mat_y, YGate().to_matrix(), atol=1e-9)

    mat_z = matrix(GateType.Z)
    assert mat_z is not None
    assert np.allclose(mat_z, ZGate().to_matrix(), atol=1e-9)

    mat_s = matrix(GateType.S)
    assert mat_s is not None
    assert np.allclose(mat_s, SGate().to_matrix(), atol=1e-9)

    mat_t = matrix(GateType.T)
    assert mat_t is not None
    assert np.allclose(mat_t, TGate().to_matrix(), atol=1e-9)


def test_multi_qubit_and_measurement_matrices() -> None:
    """CNOT and Toffoli return the X matrix; Measurement returns None."""
    x_matrix = XGate().to_matrix()
    cnot_mat = matrix(GateType.CNOT)
    toffoli_mat = matrix(GateType.Toffoli)

    assert cnot_mat is not None
    assert toffoli_mat is not None
    assert np.allclose(cnot_mat, x_matrix, atol=1e-9)
    assert np.allclose(toffoli_mat, x_matrix, atol=1e-9)

    assert matrix(GateType.Measurement) is None


def test_matrix_returns_defensive_copy() -> None:
    """Mutating the returned matrix does not modify internal cached matrices."""
    m1 = matrix(GateType.X)
    assert m1 is not None
    m1[0, 0] = 99.0 + 99.0j

    m2 = matrix(GateType.X)
    assert m2 is not None
    assert m2[0, 0] == 0.0 + 0.0j
