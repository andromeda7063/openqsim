"""Qiskit Aer simulation engine adapter."""

import numpy as np
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit_aer import AerSimulator  # type: ignore[import-untyped]

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit
from libqsim.domain.validation import ValidationError, validate
from libqsim.simulation.bloch import compute_bloch_vectors
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
    """Simulate a valid Circuit and return a SimulationResult.

    Validates the circuit first; raises InvalidCircuitError if validation fails.
    Builds a Qiskit QuantumCircuit executed with AerSimulator(method="statevector").
    """
    errors = validate(circuit)
    if errors:
        raise InvalidCircuitError(errors)

    try:
        qc = QuantumCircuit(circuit.num_qubits)

        for p in circuit.canonical_placements():
            gt = p.gate_type
            if gt == GateType.Measurement:
                continue
            elif gt == GateType.H:
                qc.h(p.targets[0])
            elif gt == GateType.X:
                qc.x(p.targets[0])
            elif gt == GateType.Y:
                qc.y(p.targets[0])
            elif gt == GateType.Z:
                qc.z(p.targets[0])
            elif gt == GateType.S:
                qc.s(p.targets[0])
            elif gt == GateType.T:
                qc.t(p.targets[0])
            elif gt == GateType.CNOT:
                qc.cx(p.controls[0], p.targets[0])
            elif gt == GateType.Toffoli:
                sorted_ctrls = sorted(p.controls)
                qc.ccx(sorted_ctrls[0], sorted_ctrls[1], p.targets[0])

        qc.save_statevector()
        sim = AerSimulator(method="statevector")
        job = sim.run(qc)
        result = job.result()

        raw_sv = result.get_statevector(qc)
        statevector = np.asarray(raw_sv.data, dtype=np.complex128)
    except Exception as exc:
        msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        raise SimulationError(f"Simulation failed: {msg}") from exc

    probabilities = np.asarray(
        statevector.real**2 + statevector.imag**2,
        dtype=np.float64,
    )
    prob_sum = float(np.sum(probabilities))
    if abs(prob_sum - 1.0) > 1e-9:
        raise SimulationError(f"Statevector probabilities do not sum to 1: sum={prob_sum}")

    bloch_vectors = compute_bloch_vectors(statevector, circuit.num_qubits)

    return SimulationResult(
        num_qubits=circuit.num_qubits,
        statevector=statevector,
        probabilities=probabilities,
        bloch_vectors=bloch_vectors,
    )
