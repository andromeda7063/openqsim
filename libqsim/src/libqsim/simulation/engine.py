"""Qiskit Aer simulation engine adapter."""

from qiskit_aer import AerSimulator  # type: ignore[import-untyped]

from libqsim.domain.models import Circuit
from libqsim.domain.validation import ValidationError
from libqsim.simulation.results import SimulationResult

__all__ = ["AerSimulator", "InvalidCircuitError", "SimulationError", "simulate"]


class SimulationError(Exception):
    """Raised when circuit simulation fails."""


class InvalidCircuitError(Exception):
    """Raised when attempting to simulate an invalid circuit."""

    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = errors
        error_msgs = "; ".join(e.message for e in errors)
        super().__init__(f"Circuit validation failed: {error_msgs}")


def simulate(circuit: Circuit) -> SimulationResult:
    """Simulate a valid Circuit and return a SimulationResult."""
    raise NotImplementedError
