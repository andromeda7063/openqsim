"""Reduced density matrix and Bloch vector calculations."""

import numpy as np
import numpy.typing as npt


def reduced_density_matrix(
    statevector: npt.NDArray[np.complex128],
    num_qubits: int,
    qubit: int,
) -> npt.NDArray[np.complex128]:
    """Compute the 2x2 reduced density matrix for a target qubit via partial trace."""
    raise NotImplementedError


def bloch_vector_from_density_matrix(
    rho: npt.NDArray[np.complex128],
) -> tuple[float, float, float]:
    """Compute the (x, y, z) Bloch vector from a 2x2 density matrix."""
    raise NotImplementedError


def compute_bloch_vectors(
    statevector: npt.NDArray[np.complex128],
    num_qubits: int,
) -> tuple[tuple[float, float, float], ...]:
    """Compute reduced Bloch vectors for all qubits in the statevector."""
    raise NotImplementedError
