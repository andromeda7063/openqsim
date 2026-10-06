"""Domain models for quantum circuit representation."""

from collections.abc import Iterable
from dataclasses import dataclass

from libqsim.domain.gates import GateType


def _placement_sort_key(
    p: "GatePlacement",
) -> tuple[int, int | float, str, tuple[int, ...], tuple[int, ...]]:
    lowest = p.lowest_occupied_qubit if p.lowest_occupied_qubit is not None else -float("inf")
    gt_val = p.gate_type.value if hasattr(p.gate_type, "value") else str(p.gate_type)
    return (p.column, lowest, gt_val, p.targets, p.controls)


@dataclass(frozen=True)
class GatePlacement:
    """An immutable placement of a gate on specific qubits and an editor column."""

    gate_type: GateType
    targets: tuple[int, ...]
    controls: tuple[int, ...]
    column: int

    def __init__(
        self,
        gate_type: GateType | str,
        targets: Iterable[int],
        controls: Iterable[int],
        column: int,
    ) -> None:
        if isinstance(gate_type, str) and not isinstance(gate_type, GateType):
            try:
                gate_type = GateType(gate_type)
            except ValueError:
                pass
        object.__setattr__(self, "gate_type", gate_type)
        object.__setattr__(self, "targets", tuple(sorted(targets)))
        object.__setattr__(self, "controls", tuple(sorted(controls)))
        object.__setattr__(self, "column", column)

    @property
    def occupied_qubits(self) -> tuple[int, ...]:
        """Return a sorted tuple of all target and control qubits, preserving duplicates."""
        return tuple(sorted(self.targets + self.controls))

    @property
    def lowest_occupied_qubit(self) -> int | None:
        """Return the lowest-indexed occupied qubit, or None if no qubits are occupied."""
        return self.occupied_qubits[0] if self.occupied_qubits else None


@dataclass(frozen=True, eq=False)
class Circuit:
    """An immutable quantum circuit containing a qubit count and gate placements."""

    num_qubits: int
    placements: tuple[GatePlacement, ...]

    def __init__(
        self,
        num_qubits: int,
        placements: Iterable[GatePlacement] = (),
    ) -> None:
        object.__setattr__(self, "num_qubits", num_qubits)
        object.__setattr__(self, "placements", tuple(placements))

    def canonical_placements(self) -> tuple[GatePlacement, ...]:
        """Return placements sorted deterministically.

        Placements are ordered by (column, lowest occupied qubit, gate_type value,
        targets, controls).
        """
        return tuple(sorted(self.placements, key=_placement_sort_key))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Circuit):
            return False
        return (
            self.num_qubits == other.num_qubits
            and self.canonical_placements() == other.canonical_placements()
        )

    def __hash__(self) -> int:
        return hash((self.num_qubits, self.canonical_placements()))

    def with_placements(self, placements: Iterable[GatePlacement]) -> "Circuit":
        """Return a new Circuit with the given placements, keeping num_qubits unchanged."""
        return Circuit(num_qubits=self.num_qubits, placements=placements)

    def with_num_qubits(self, num_qubits: int) -> "Circuit":
        """Return a new Circuit with the given qubit count, keeping placements unchanged."""
        return Circuit(num_qubits=num_qubits, placements=self.placements)
