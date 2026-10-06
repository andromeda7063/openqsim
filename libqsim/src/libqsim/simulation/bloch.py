"""Reduced density matrix and Bloch vector calculations via partial trace and Pauli expectations."""

import numpy as np
import numpy.typing as npt


def reduced_density_matrix(
    statevector: npt.NDArray[np.complex128],
    num_qubits: int,
    qubit: int,
) -> npt.NDArray[np.complex128]:
    """Compute the 2x2 reduced density matrix for a target qubit via partial trace.

    Qubit 0 is the least-significant bit (LSB) in Qiskit statevector ordering.
    """
    if not (1 <= num_qubits <= 10):
        raise ValueError(f"num_qubits {num_qubits} is out of range; must be between 1 and 10.")
    if not (0 <= qubit < num_qubits):
        raise ValueError(f"qubit index {qubit} is out of range for {num_qubits}-qubit statevector.")

    expected_len = 1 << num_qubits
    if statevector.size != expected_len:
        raise ValueError(
            f"Statevector size {statevector.size} does not match 2**{num_qubits} = {expected_len}."
        )

    # In C-order numpy array, qubit 0 (LSB) is the last axis (axis n-1).
    # Qubit q corresponds to axis (num_qubits - 1 - q).
    target_axis = num_qubits - 1 - qubit
    tensor = statevector.reshape((2,) * num_qubits)
    reordered = np.moveaxis(tensor, target_axis, 0)
    flattened_other = reordered.reshape(2, 1 << (num_qubits - 1))

    # Partial trace rho = M @ M^dagger
    rho: npt.NDArray[np.complex128] = flattened_other @ flattened_other.conj().T
    return rho


def bloch_vector_from_density_matrix(
    rho: npt.NDArray[np.complex128],
) -> tuple[float, float, float]:
    """Compute the (x, y, z) Bloch vector from a 2x2 density matrix."""
    if rho.shape != (2, 2):
        raise ValueError(f"Expected 2x2 density matrix, got shape {rho.shape}.")

    # Pauli expectation values:
    # Tr(rho * X) = 2 * Re(rho[0, 1])
    # Tr(rho * Y) = 2 * Im(rho[1, 0]) = -2 * Im(rho[0, 1])
    # Tr(rho * Z) = Re(rho[0, 0] - rho[1, 1])
    rx = float(2.0 * np.real(rho[0, 1]))
    ry = float(2.0 * np.imag(rho[1, 0]))
    rz = float(np.real(rho[0, 0] - rho[1, 1]))

    return (rx, ry, rz)


def compute_bloch_vectors(
    statevector: npt.NDArray[np.complex128],
    num_qubits: int,
) -> tuple[tuple[float, float, float], ...]:
    """Compute reduced Bloch vectors for all qubits in the statevector.

    Returns a tuple of (x, y, z) coordinates where index corresponds to qubit wire.
    """
    if not (1 <= num_qubits <= 10):
        raise ValueError(f"num_qubits {num_qubits} is out of range; must be between 1 and 10.")

    expected_len = 1 << num_qubits
    if statevector.size != expected_len:
        raise ValueError(
            f"Statevector size {statevector.size} does not match 2**{num_qubits} = {expected_len}."
        )

    vectors: list[tuple[float, float, float]] = []
    for q in range(num_qubits):
        rho = reduced_density_matrix(statevector, num_qubits, q)
        vec = bloch_vector_from_density_matrix(rho)
        vectors.append(vec)

    return tuple(vectors)
