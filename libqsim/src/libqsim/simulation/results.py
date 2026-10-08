"""Simulation results and computational basis representations."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


def basis_labels(n: int) -> list[str]:
    """Return a list of 2**n computational-basis bit strings.

    Index i has the highest-indexed qubit on the left and qubit 0 on the right
    (e.g., for n=2, index 1 is '01').
    """
    if not (1 <= n <= 10):
        raise ValueError(f"num_qubits {n} is out of range; must be between 1 and 10.")
    return [format(i, f"0{n}b") for i in range(1 << n)]


@dataclass(frozen=True)
class SimulationResult:
    """An immutable container for statevector simulation results."""

    num_qubits: int
    statevector: npt.NDArray[np.complex128]
    probabilities: npt.NDArray[np.float64]
    bloch_vectors: tuple[tuple[float, float, float], ...]

    def __post_init__(self) -> None:
        """Mark underlying numpy arrays as read-only."""
        self.statevector.flags.writeable = False
        self.probabilities.flags.writeable = False

    @property
    def basis_labels(self) -> list[str]:
        """Return the basis state labels corresponding to the simulated circuit."""
        return basis_labels(self.num_qubits)


@dataclass(frozen=True)
class SimulationSnapshot:
    """Display data for the initial state or the result after one column."""

    num_qubits: int
    column: int | None
    probabilities: npt.NDArray[np.float64]
    bloch_vectors: tuple[tuple[float, float, float], ...]

    def __post_init__(self) -> None:
        self.probabilities.flags.writeable = False

    @property
    def basis_labels(self) -> list[str]:
        """Return basis labels in Qiskit-compatible order."""
        return basis_labels(self.num_qubits)


def snapshot_from_statevector(
    num_qubits: int,
    column: int | None,
    statevector: npt.NDArray[np.complex128],
) -> SimulationSnapshot:
    """Build display-only data for a statevector."""
    from libqsim.simulation.bloch import compute_bloch_vectors

    probabilities = np.asarray(statevector.real**2 + statevector.imag**2, dtype=np.float64)
    return SimulationSnapshot(
        num_qubits=num_qubits,
        column=column,
        probabilities=probabilities,
        bloch_vectors=compute_bloch_vectors(statevector, num_qubits),
    )
