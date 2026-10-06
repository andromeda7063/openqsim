"""Unit tests for simulation results and basis state labels (FR-3.3, NFR-7.3, NFR-7.7)."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from libqsim.simulation.results import SimulationResult, basis_labels


@pytest.mark.req("FR-3.3")
def test_basis_labels_values_and_ordering() -> None:
    """basis_labels generates strings with highest-indexed qubit on the left."""
    # 1 qubit
    assert basis_labels(1) == ["0", "1"]

    # 2 qubits: index 1 is "01" (q1=0, q0=1)
    labels_2 = basis_labels(2)
    assert labels_2 == ["00", "01", "10", "11"]
    assert labels_2[1] == "01"

    # 3 qubits: index 1 is "001", index 4 is "100"
    labels_3 = basis_labels(3)
    assert len(labels_3) == 8
    assert labels_3[1] == "001"
    assert labels_3[4] == "100"
    assert labels_3 == ["000", "001", "010", "011", "100", "101", "110", "111"]


@pytest.mark.req("FR-3.3")
def test_basis_labels_bounds_validation() -> None:
    """basis_labels raises ValueError for n not in 1..10."""
    with pytest.raises(ValueError):
        basis_labels(0)

    with pytest.raises(ValueError):
        basis_labels(-1)

    with pytest.raises(ValueError):
        basis_labels(11)


@pytest.mark.req("NFR-7.3")
def test_simulation_result_frozen_and_read_only() -> None:
    """SimulationResult is frozen and arrays are marked read-only."""
    sv = np.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)
    probs = np.array([1.0, 0.0], dtype=np.float64)
    bloch = ((0.0, 0.0, 1.0),)

    res = SimulationResult(
        num_qubits=1,
        statevector=sv,
        probabilities=probs,
        bloch_vectors=bloch,
    )

    assert res.num_qubits == 1
    assert np.allclose(res.statevector, sv, atol=1e-9)
    assert np.allclose(res.probabilities, probs, atol=1e-9)
    assert res.bloch_vectors == ((0.0, 0.0, 1.0),)
    assert res.basis_labels == ["0", "1"]

    # Dataclass is frozen
    with pytest.raises(FrozenInstanceError):
        res.num_qubits = 2  # type: ignore[misc]

    # Underlying numpy arrays are read-only
    with pytest.raises(ValueError):
        res.statevector[0] = 99.0 + 0.0j

    with pytest.raises(ValueError):
        res.probabilities[0] = 99.0


@pytest.mark.req("FR-3.3", "NFR-7.7")
def test_simulation_result_probabilities_tolerance() -> None:
    """Probabilities must sum to 1 within 1e-9 tolerance."""
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    sv = np.array([inv_sqrt2 + 0.0j, inv_sqrt2 + 0.0j], dtype=np.complex128)
    probs = np.array([0.5, 0.5], dtype=np.float64)
    bloch = ((1.0, 0.0, 0.0),)

    res = SimulationResult(
        num_qubits=1,
        statevector=sv,
        probabilities=probs,
        bloch_vectors=bloch,
    )

    assert abs(float(np.sum(res.probabilities)) - 1.0) <= 1e-9
