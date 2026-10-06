"""Simulation layer for OpenQSim: Qiskit Aer adapter, statevector, and Bloch calculation."""

from libqsim.simulation.bloch import (
    bloch_vector_from_density_matrix,
    compute_bloch_vectors,
    reduced_density_matrix,
)
from libqsim.simulation.engine import (
    InvalidCircuitError,
    SimulationError,
    simulate,
)
from libqsim.simulation.results import (
    SimulationResult,
    basis_labels,
)

__all__ = [
    "InvalidCircuitError",
    "SimulationError",
    "SimulationResult",
    "basis_labels",
    "bloch_vector_from_density_matrix",
    "compute_bloch_vectors",
    "reduced_density_matrix",
    "simulate",
]
