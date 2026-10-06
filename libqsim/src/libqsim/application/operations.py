"""Circuit editing operations and mutation results."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import validate

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
    """Place a gate in the circuit using candidate/commit mutation validation.

    Single-qubit gates and measurements occupy (qubit, column).
    CNOT placed at wire w defaults to control w, target w+1.
    Toffoli placed at wire w defaults to controls w, w+1, target w+2.
    """
    if isinstance(gate_type, str):
        try:
            gt = GateType(gate_type)
        except ValueError:
            return OperationResult(
                status="rejected",
                circuit=circuit,
                messages=(f"Unknown gate type: '{gate_type}'.",),
                touched=(),
            )
    else:
        gt = gate_type

    if gt == GateType.CNOT:
        controls: tuple[int, ...] = (qubit,)
        targets: tuple[int, ...] = (qubit + 1,)
    elif gt == GateType.Toffoli:
        controls = (qubit, qubit + 1)
        targets = (qubit + 2,)
    else:
        controls = ()
        targets = (qubit,)

    placement = GatePlacement(
        gate_type=gt,
        targets=targets,
        controls=controls,
        column=column,
    )

    candidate = circuit.with_placements((*circuit.placements, placement))
    errors = validate(candidate)
    if errors:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=tuple(e.message for e in errors),
            touched=(),
        )

    return OperationResult(
        status="applied",
        circuit=candidate,
        messages=(),
        touched=(placement,),
    )


def delete_gates(
    circuit: Circuit,
    placements: Iterable[GatePlacement],
) -> OperationResult:
    """Delete the specified placements from the circuit."""
    to_delete = set(placements).intersection(circuit.placements)
    if not to_delete:
        return OperationResult(
            status="noop",
            circuit=circuit,
            messages=(),
            touched=(),
        )

    cand_placements = tuple(p for p in circuit.placements if p not in to_delete)
    candidate = circuit.with_placements(cand_placements)
    errors = validate(candidate)
    if errors:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=tuple(e.message for e in errors),
            touched=(),
        )

    return OperationResult(
        status="applied",
        circuit=candidate,
        messages=(),
        touched=(),
    )


def clear(circuit: Circuit) -> OperationResult:
    """Clear all gate placements from the circuit."""
    if not circuit.placements:
        return OperationResult(
            status="noop",
            circuit=circuit,
            messages=(),
            touched=(),
        )

    candidate = circuit.with_placements(())
    errors = validate(candidate)
    if errors:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=tuple(e.message for e in errors),
            touched=(),
        )

    return OperationResult(
        status="applied",
        circuit=candidate,
        messages=(),
        touched=(),
    )


def change_target(
    circuit: Circuit,
    placement: GatePlacement,
) -> OperationResult:
    """Cycle or swap target and control assignments for a CNOT or Toffoli gate."""
    if placement not in circuit.placements:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=("Gate placement not found in circuit.",),
            touched=(),
        )

    if placement.gate_type not in (GateType.CNOT, GateType.Toffoli):
        gt_name = (
            placement.gate_type.value
            if hasattr(placement.gate_type, "value")
            else str(placement.gate_type)
        )
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=(
                f"Change target is only supported for CNOT and Toffoli gates, got {gt_name}.",
            ),
            touched=(),
        )

    if placement.gate_type == GateType.CNOT:
        new_targets = placement.controls
        new_controls = placement.targets
        new_placement = GatePlacement(
            gate_type=GateType.CNOT,
            targets=new_targets,
            controls=new_controls,
            column=placement.column,
        )
    else:  # Toffoli
        occupied = sorted(placement.occupied_qubits)
        curr_target = placement.targets[0]
        if curr_target == occupied[0]:  # top -> middle
            new_target = occupied[1]
            new_controls = (occupied[0], occupied[2])
        elif curr_target == occupied[1]:  # middle -> bottom
            new_target = occupied[2]
            new_controls = (occupied[0], occupied[1])
        else:  # bottom -> top
            new_target = occupied[0]
            new_controls = (occupied[1], occupied[2])

        new_placement = GatePlacement(
            gate_type=GateType.Toffoli,
            targets=(new_target,),
            controls=new_controls,
            column=placement.column,
        )

    cand_placements = tuple(new_placement if p == placement else p for p in circuit.placements)
    candidate = circuit.with_placements(cand_placements)
    errors = validate(candidate)
    if errors:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=tuple(e.message for e in errors),
            touched=(),
        )

    return OperationResult(
        status="applied",
        circuit=candidate,
        messages=(),
        touched=(new_placement,),
    )


def plan_resize(
    circuit: Circuit,
    n: int,
) -> ResizePlan:
    """Analyze the impact of resizing the circuit to n qubits."""
    affected = tuple(
        p for p in circuit.canonical_placements() if any(q >= n for q in p.occupied_qubits)
    )
    needs_confirmation = len(affected) > 0 and n < circuit.num_qubits
    return ResizePlan(
        requested=n,
        affected=affected,
        needs_confirmation=needs_confirmation,
    )


def resize(
    circuit: Circuit,
    n: int,
    confirmed: bool = False,
) -> OperationResult:
    """Resize the circuit qubit count to n, optionally deleting affected gates if confirmed."""
    if not (1 <= n <= 10):
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=(
                f"Qubit count {n} is out of range; must be between 1 and 10 qubits inclusive.",
            ),
            touched=(),
        )

    if n == circuit.num_qubits:
        return OperationResult(
            status="noop",
            circuit=circuit,
            messages=(),
            touched=(),
        )

    if n > circuit.num_qubits:
        candidate = circuit.with_num_qubits(n)
        errors = validate(candidate)
        if errors:
            return OperationResult(
                status="rejected",
                circuit=circuit,
                messages=tuple(e.message for e in errors),
                touched=(),
            )
        return OperationResult(
            status="applied",
            circuit=candidate,
            messages=(),
            touched=(),
        )

    # n < circuit.num_qubits
    plan = plan_resize(circuit, n)
    if plan.needs_confirmation and not confirmed:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=("Decreasing qubit count will remove affected gates; confirmation required.",),
            touched=(),
        )

    if confirmed:
        affected_set = set(plan.affected)
        cand_placements = tuple(p for p in circuit.placements if p not in affected_set)
        candidate = Circuit(num_qubits=n, placements=cand_placements)
    else:
        candidate = circuit.with_num_qubits(n)

    errors = validate(candidate)
    if errors:
        return OperationResult(
            status="rejected",
            circuit=circuit,
            messages=tuple(e.message for e in errors),
            touched=(),
        )

    return OperationResult(
        status="applied",
        circuit=candidate,
        messages=(),
        touched=(),
    )
