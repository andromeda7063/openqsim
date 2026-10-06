"""Unit tests for reduced density matrices and Bloch vector calculation (FR-3.4, NFR-7.7)."""

import numpy as np
import pytest
from libqsim.simulation.bloch import (
    bloch_vector_from_density_matrix,
    compute_bloch_vectors,
    reduced_density_matrix,
)


@pytest.mark.req("FR-3.4", "NFR-7.7")
def test_bloch_vectors_known_pure_states() -> None:
    """Single-qubit pure states match literal known Bloch vectors."""
    # |0> -> (0, 0, 1)
    sv_0 = np.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)
    b_0 = compute_bloch_vectors(sv_0, 1)
    assert len(b_0) == 1
    assert np.allclose(b_0[0], (0.0, 0.0, 1.0), atol=1e-9)

    # X|0> = |1> -> (0, 0, -1)
    sv_1 = np.array([0.0 + 0.0j, 1.0 + 0.0j], dtype=np.complex128)
    b_1 = compute_bloch_vectors(sv_1, 1)
    assert len(b_1) == 1
    assert np.allclose(b_1[0], (0.0, 0.0, -1.0), atol=1e-9)

    # H|0> = |+> -> (1, 0, 0)
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    sv_plus = np.array([inv_sqrt2 + 0.0j, inv_sqrt2 + 0.0j], dtype=np.complex128)
    b_plus = compute_bloch_vectors(sv_plus, 1)
    assert len(b_plus) == 1
    assert np.allclose(b_plus[0], (1.0, 0.0, 0.0), atol=1e-9)

    # S H|0> = |R> = (|0> + i|1>)/sqrt2 -> (0, 1, 0)
    sv_r = np.array([inv_sqrt2 + 0.0j, 0.0 + 1.0j * inv_sqrt2], dtype=np.complex128)
    b_r = compute_bloch_vectors(sv_r, 1)
    assert len(b_r) == 1
    assert np.allclose(b_r[0], (0.0, 1.0, 0.0), atol=1e-9)


@pytest.mark.req("FR-3.4", "NFR-7.7")
def test_bloch_vectors_bell_state_maximally_mixed() -> None:
    """Maximally entangled Bell state has zero Bloch vector on both qubits."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    # Bell state (|00> + |11>) / sqrt2: index 0 and 3 are 1/sqrt2
    sv_bell = np.array(
        [inv_sqrt2 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, inv_sqrt2 + 0.0j], dtype=np.complex128
    )
    b_bell = compute_bloch_vectors(sv_bell, 2)
    assert len(b_bell) == 2
    assert np.allclose(b_bell[0], (0.0, 0.0, 0.0), atol=1e-9)
    assert np.allclose(b_bell[1], (0.0, 0.0, 0.0), atol=1e-9)


@pytest.mark.req("FR-3.4", "NFR-7.7")
def test_bloch_vectors_three_qubit_product_state() -> None:
    """3-qubit product state |q2 q1 q0> = |1> (x) |0> (x) |+> gives expected individual vectors."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    # q0 is |+> -> (1, 0, 0)
    # q1 is |0> -> (0, 0, 1)
    # q2 is |1> -> (0, 0, -1)
    # State |q2 q1 q0> = (|100> + |101>)/sqrt2 = (|4> + |5>)/sqrt2
    sv = np.zeros(8, dtype=np.complex128)
    sv[4] = inv_sqrt2
    sv[5] = inv_sqrt2

    b = compute_bloch_vectors(sv, 3)
    assert len(b) == 3
    assert np.allclose(b[0], (1.0, 0.0, 0.0), atol=1e-9)  # q0
    assert np.allclose(b[1], (0.0, 0.0, 1.0), atol=1e-9)  # q1
    assert np.allclose(b[2], (0.0, 0.0, -1.0), atol=1e-9)  # q2


@pytest.mark.req("FR-3.4")
def test_reduced_density_matrix_properties() -> None:
    """Reduced density matrix is 2x2, Hermitian, and has trace 1."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    sv_bell = np.array(
        [inv_sqrt2 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, inv_sqrt2 + 0.0j], dtype=np.complex128
    )

    rho0 = reduced_density_matrix(sv_bell, 2, 0)
    assert rho0.shape == (2, 2)
    assert np.allclose(rho0, rho0.conj().T, atol=1e-9)
    assert np.isclose(float(np.real(np.trace(rho0))), 1.0, atol=1e-9)
    # Maximally mixed state is I/2
    assert np.allclose(rho0, 0.5 * np.eye(2), atol=1e-9)


@pytest.mark.req("FR-3.4")
def test_bloch_bounds_and_dimension_validation() -> None:
    """compute_bloch_vectors and reduced_density_matrix validate inputs."""
    sv_2 = np.zeros(4, dtype=np.complex128)
    sv_2[0] = 1.0

    with pytest.raises(ValueError):
        reduced_density_matrix(sv_2, 2, -1)

    with pytest.raises(ValueError):
        reduced_density_matrix(sv_2, 2, 2)

    with pytest.raises(ValueError):
        # Mismatched length: array length 4 but num_qubits=1 expects 2
        compute_bloch_vectors(sv_2, 1)

    with pytest.raises(ValueError):
        # Invalid 2x2 shape for density matrix
        bloch_vector_from_density_matrix(np.zeros((3, 3), dtype=np.complex128))
