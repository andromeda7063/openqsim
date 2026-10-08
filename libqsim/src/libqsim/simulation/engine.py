"""Qiskit Aer simulation engine adapter."""

import numpy as np
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit_aer import AerSimulator  # type: ignore[import-untyped]

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import ValidationError, validate
from libqsim.simulation.bloch import compute_bloch_vectors
from libqsim.simulation.results import (
    SimulationResult,
    SimulationSnapshot,
    snapshot_from_statevector,
)

__all__ = [
    "AerSimulator",
    "InvalidCircuitError",
    "SimulationError",
    "simulate",
    "simulate_trace",
    "simulate_with_trace",
]


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
    return _result_from_statevector(circuit, _run(circuit, trace=False)[-1][1])


def simulate_trace(circuit: Circuit) -> tuple[SimulationSnapshot, ...]:
    """Simulate once and return display snapshots at initial and occupied columns."""
    return tuple(
        snapshot_from_statevector(circuit.num_qubits, column, statevector)
        for column, statevector in _run(circuit, trace=True)
    )


def simulate_with_trace(
    circuit: Circuit,
) -> tuple[SimulationResult, tuple[SimulationSnapshot, ...]]:
    """Return the final result and display trace from one Aer execution."""
    states = _run(circuit, trace=True)
    result = _result_from_statevector(circuit, states[-1][1])
    snapshots = tuple(
        snapshot_from_statevector(circuit.num_qubits, column, statevector)
        for column, statevector in states
    )
    return result, snapshots


def _run(circuit: Circuit, *, trace: bool) -> list[tuple[int | None, np.ndarray]]:
    errors = validate(circuit)
    if errors:
        raise InvalidCircuitError(errors)

    try:
        qc = QuantumCircuit(circuit.num_qubits)

        placements_by_column: dict[int, list[GatePlacement]] = {}
        for p in circuit.canonical_placements():
            placements_by_column.setdefault(p.column, []).append(p)

        labels: list[tuple[int | None, str]] = []
        if trace:
            qc.save_statevector(label="initial")
            labels.append((None, "initial"))
        for column, placements in sorted(placements_by_column.items()):
            for p in placements:
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

            if trace:
                label = f"column_{column}"
                qc.save_statevector(label=label)
                labels.append((column, label))
        if not trace:
            qc.save_statevector(label="final")
            labels.append((None, "final"))
        sim = AerSimulator(method="statevector")
        job = sim.run(qc)
        result = job.result()

        states = [
            (column, np.asarray(result.data(0)[label], dtype=np.complex128))
            for column, label in labels
        ]
    except Exception as exc:
        msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        raise SimulationError(f"Simulation failed: {msg}") from exc

    return states


def _result_from_statevector(circuit: Circuit, statevector: np.ndarray) -> SimulationResult:
    probabilities = np.asarray(statevector.real**2 + statevector.imag**2, dtype=np.float64)
    prob_sum = float(np.sum(probabilities))
    if abs(prob_sum - 1.0) > 1e-9:
        raise SimulationError(f"Statevector probabilities do not sum to 1: sum={prob_sum}")
    return SimulationResult(
        circuit.num_qubits,
        statevector,
        probabilities,
        compute_bloch_vectors(statevector, circuit.num_qubits),
    )
