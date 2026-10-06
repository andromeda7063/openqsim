"""Simulation results and computational basis representations."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


def basis_labels(n: int) -> list[str]:
    """Return a list of 2**n computational-basis bit strings."""
    raise NotImplementedError


@dataclass(frozen=True)
class SimulationResult:
    """An immutable container for statevector simulation results."""

    num_qubits: int
    statevector: npt.NDArray[np.complex128]
    probabilities: npt.NDArray[np.float64]
    bloch_vectors: tuple[tuple[float, float, float], ...]

    @property
    def basis_labels(self) -> list[str]:
        """Return the basis state labels corresponding to the simulated circuit."""
        raise NotImplementedError
