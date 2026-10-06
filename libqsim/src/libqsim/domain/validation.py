"""Circuit structural validation for OpenQSim."""

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from libqsim.domain.gates import GATE_ARITY, GateType
from libqsim.domain.models import Circuit, GatePlacement


class ValidationErrorCode(str, Enum):
    """Machine-readable validation error codes."""

    CIRCUIT_SIZE_OUT_OF_RANGE = "CIRCUIT_SIZE_OUT_OF_RANGE"
    COLUMN_OUT_OF_RANGE = "COLUMN_OUT_OF_RANGE"
    QUBIT_INDEX_OUT_OF_RANGE = "QUBIT_INDEX_OUT_OF_RANGE"
    INVALID_GATE_ARITY = "INVALID_GATE_ARITY"
    DUPLICATE_QUBIT_REFERENCE = "DUPLICATE_QUBIT_REFERENCE"
    NON_CONTIGUOUS_QUBITS = "NON_CONTIGUOUS_QUBITS"
    WIRE_COLUMN_COLLISION = "WIRE_COLUMN_COLLISION"
    DUPLICATE_MEASUREMENT = "DUPLICATE_MEASUREMENT"
    GATE_AFTER_MEASUREMENT = "GATE_AFTER_MEASUREMENT"


@dataclass(frozen=True)
class ValidationError:
    """An immutable validation error with an error code, message, and optional placement."""

    code: ValidationErrorCode
    message: str
    placement: GatePlacement | None = None

    @property
    def offending_placement(self) -> GatePlacement | None:
        """Alias for placement to identify the offending gate placement."""
        return self.placement


def validate(circuit: Circuit) -> list[ValidationError]:
    """Validate a quantum circuit against OpenQSim domain rules.

    Returns an empty list if the circuit is valid, or a list of ValidationError
    instances identifying violations in deterministic order.
    """
    errors: list[ValidationError] = []

    # 1. Circuit-level check: num_qubits in 1..10
    if not (1 <= circuit.num_qubits <= 10):
        errors.append(
            ValidationError(
                code=ValidationErrorCode.CIRCUIT_SIZE_OUT_OF_RANGE,
                message=(
                    f"Circuit qubit count {circuit.num_qubits} is out of range; "
                    "must be between 1 and 10 qubits inclusive."
                ),
                placement=None,
            )
        )

    # Placements are evaluated in canonical order to ensure determinism under shuffling
    canonical_placements = circuit.canonical_placements()

    # Track which placements have out-of-range bounds (qubits or columns)
    # Cascade rule: an out-of-range placement produces its own error and
    # no contiguity or collision errors derived from it.
    out_of_range_placements: set[GatePlacement] = set()

    # 2. Intrinsic placement checks
    for p in canonical_placements:
        is_out_of_range = False

        # Qubit bounds check: targets and controls must be in 0..num_qubits-1
        all_referenced_qubits = p.targets + p.controls
        has_invalid_qubit = any(q < 0 or q >= circuit.num_qubits for q in all_referenced_qubits)
        if has_invalid_qubit:
            is_out_of_range = True
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE,
                    message=(
                        f"Gate {p.gate_type} at column {p.column} references qubit index outside "
                        f"0..{circuit.num_qubits - 1}: targets={p.targets}, controls={p.controls}."
                    ),
                    placement=p,
                )
            )

        # Column bounds check: column must be in 0..49
        if not (0 <= p.column <= 49):
            is_out_of_range = True
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.COLUMN_OUT_OF_RANGE,
                    message=(
                        f"Gate {p.gate_type} has column index {p.column} outside editor range 0..49."
                    ),
                    placement=p,
                )
            )

        if is_out_of_range:
            out_of_range_placements.add(p)

        # Arity check
        expected_arity = GATE_ARITY.get(p.gate_type)
        has_valid_arity = False
        if expected_arity is not None:
            exp_targets, exp_controls = expected_arity
            if len(p.targets) != exp_targets or len(p.controls) != exp_controls:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.INVALID_GATE_ARITY,
                        message=(
                            f"Gate {p.gate_type} requires {exp_targets} target(s) and "
                            f"{exp_controls} control(s), but got {len(p.targets)} target(s) and "
                            f"{len(p.controls)} control(s)."
                        ),
                        placement=p,
                    )
                )
            else:
                has_valid_arity = True
        else:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.INVALID_GATE_ARITY,
                    message=f"Gate type {p.gate_type} is not a recognized supported gate.",
                    placement=p,
                )
            )

        # Duplicate qubit references within placement
        has_duplicate_qubits = len(all_referenced_qubits) != len(set(all_referenced_qubits))
        if has_duplicate_qubits:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.DUPLICATE_QUBIT_REFERENCE,
                    message=(
                        f"Gate {p.gate_type} at column {p.column} contains duplicate qubit references: "
                        f"targets={p.targets}, controls={p.controls}."
                    ),
                    placement=p,
                )
            )

        # Contiguity check for CNOT and Toffoli
        # Cascade rule: do NOT emit contiguity error if placement is out-of-range,
        # has wrong arity, or contains duplicate qubits.
        if (
            p.gate_type in (GateType.CNOT, GateType.Toffoli)
            and not is_out_of_range
            and has_valid_arity
            and not has_duplicate_qubits
        ):
            occupied = p.occupied_qubits
            if occupied:
                is_contiguous = (max(occupied) - min(occupied)) == (len(occupied) - 1)
                if not is_contiguous:
                    errors.append(
                        ValidationError(
                            code=ValidationErrorCode.NON_CONTIGUOUS_QUBITS,
                            message=(
                                f"Multi-qubit gate {p.gate_type} at column {p.column} must occupy "
                                f"contiguous qubit wires, but occupies wires {occupied}."
                            ),
                            placement=p,
                        )
                    )

    # 3. Wire/column collision checks (multi-placement relational)
    # Cascade rule: out-of-range placements are excluded from collision checks.
    cell_to_placements: dict[tuple[int, int], list[GatePlacement]] = defaultdict(list)
    for p in canonical_placements:
        if p in out_of_range_placements:
            continue
        for wire in set(p.occupied_qubits):
            cell_to_placements[(wire, p.column)].append(p)

    colliding_placements: set[GatePlacement] = set()
    for placements_at_cell in cell_to_placements.values():
        if len(placements_at_cell) > 1:
            for p in placements_at_cell:
                colliding_placements.add(p)

    # Symmetric cardinality: each colliding placement receives a collision error,
    # emitted in canonical order for determinism.
    for p in canonical_placements:
        if p in colliding_placements:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.WIRE_COLUMN_COLLISION,
                    message=(
                        f"Gate {p.gate_type} at column {p.column} collides with another gate on "
                        f"one or more occupied wires {p.occupied_qubits}."
                    ),
                    placement=p,
                )
            )

    # 4. Measurement rule checks
    # Cascade rule: out-of-range placements are excluded from measurement checks.
    # Check per wire in increasing column order.
    # Each qubit may contain at most one Measurement, and it must be the final operation.
    wire_placements: dict[int, list[GatePlacement]] = defaultdict(list)
    for p in canonical_placements:
        if p in out_of_range_placements:
            continue
        for wire in set(p.occupied_qubits):
            wire_placements[wire].append(p)

    # Collect duplicate measurements and gates after measurement, deduplicated per placement
    duplicate_measurements: set[GatePlacement] = set()
    gates_after_measurement: set[GatePlacement] = set()

    for wire in range(max(0, circuit.num_qubits)):
        placements_on_wire = wire_placements.get(wire, [])
        # Sort wire operations by column
        sorted_on_wire = sorted(placements_on_wire, key=lambda pl: pl.column)

        first_measurement: GatePlacement | None = None
        for pl in sorted_on_wire:
            if pl.gate_type == GateType.Measurement:
                if first_measurement is None:
                    first_measurement = pl
                elif pl.column > first_measurement.column:
                    # Subsequent measurement on the same wire
                    duplicate_measurements.add(pl)
            else:
                if first_measurement is not None and pl.column > first_measurement.column:
                    # Non-measurement gate placed after a Measurement on this wire
                    gates_after_measurement.add(pl)

    # Emit measurement errors in canonical placement order for determinism
    for p in canonical_placements:
        if p in duplicate_measurements:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.DUPLICATE_MEASUREMENT,
                    message=(
                        f"Measurement at column {p.column} on wire {p.targets} is invalid; "
                        "a qubit may contain at most one Measurement."
                    ),
                    placement=p,
                )
            )
        if p in gates_after_measurement:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.GATE_AFTER_MEASUREMENT,
                    message=(
                        f"Gate {p.gate_type} at column {p.column} is placed after a Measurement "
                        "on an occupied qubit wire; Measurement must be the final operation on its wire."
                    ),
                    placement=p,
                )
            )

    return errors
