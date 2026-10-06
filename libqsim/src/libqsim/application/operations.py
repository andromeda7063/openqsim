"""Circuit editing operations and mutation results."""

from dataclasses import dataclass
from typing import Literal

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement

__all__ = [
    "OperationResult",
    "ResizePlan",
    "change_target",
    "clear",
    "delete_gates",
    "place_gate",
    "plan_resize",
    "resize",
]


@dataclass(frozen=True)
class OperationResult:
    """An immutable result of an editing mutation or operation."""

    status: Literal["applied", "noop", "rejected"]
    circuit: Circuit
    messages: tuple[str, ...] = ()
    touched: tuple[GatePlacement, ...] = ()


@dataclass(frozen=True)
class ResizePlan:
    """An immutable plan describing the impact of a requested circuit resize."""

    requested: int
    affected: tuple[GatePlacement, ...]
    needs_confirmation: bool


def place_gate(
    circuit: Circuit,
    gate_type: GateType | str,
    qubit: int,
    column: int,
) -> OperationResult:
    """Place a gate in the circuit using candidate/commit mutation validation."""
    raise NotImplementedError


def delete_gates(
    circuit: Circuit,
    placements: tuple[GatePlacement, ...]
    | list[GatePlacement]
    | set[GatePlacement]
    | frozenset[GatePlacement],
) -> OperationResult:
    """Delete the specified placements from the circuit."""
    raise NotImplementedError


def clear(circuit: Circuit) -> OperationResult:
    """Clear all gate placements from the circuit."""
    raise NotImplementedError


def change_target(
    circuit: Circuit,
    placement: GatePlacement,
) -> OperationResult:
    """Cycle or swap target and control assignments for a CNOT or Toffoli gate."""
    raise NotImplementedError


def plan_resize(
    circuit: Circuit,
    n: int,
) -> ResizePlan:
    """Analyze the impact of resizing the circuit to n qubits."""
    raise NotImplementedError


def resize(
    circuit: Circuit,
    n: int,
    confirmed: bool = False,
) -> OperationResult:
    """Resize the circuit qubit count to n, optionally deleting affected gates if confirmed."""
    raise NotImplementedError
