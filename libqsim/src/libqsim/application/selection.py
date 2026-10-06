"""Selection query, geometry, and selection state operations."""

from collections.abc import Iterable

from libqsim.domain.models import Circuit, GatePlacement

__all__ = [
    "click_selection",
    "gate_at",
    "gates_in_rect",
    "marquee_selection",
    "prune_selection",
    "select_all",
]


def gate_at(
    circuit: Circuit,
    qubit: int,
    column: int,
) -> GatePlacement | None:
    """Return the gate occupying (qubit, column), or None if empty."""
    raise NotImplementedError


def gates_in_rect(
    circuit: Circuit,
    q_min: int,
    q_max: int,
    c_min: int,
    c_max: int,
) -> frozenset[GatePlacement]:
    """Return all whole gate placements that intersect the given (qubit, column) rectangle."""
    raise NotImplementedError


def select_all(
    circuit: Circuit,
) -> frozenset[GatePlacement]:
    """Return a selection containing all gate placements in the circuit."""
    raise NotImplementedError


def click_selection(
    current: frozenset[GatePlacement],
    hit: GatePlacement | None,
    ctrl: bool = False,
) -> frozenset[GatePlacement]:
    """Compute the new selection resulting from a mouse click on hit (or empty space)."""
    raise NotImplementedError


def marquee_selection(
    current: frozenset[GatePlacement],
    rect_gates: Iterable[GatePlacement],
    ctrl: bool = False,
) -> frozenset[GatePlacement]:
    """Compute the new selection resulting from a marquee rectangle selection."""
    raise NotImplementedError


def prune_selection(
    circuit: Circuit,
    selection: frozenset[GatePlacement],
) -> frozenset[GatePlacement]:
    """Prune any placements from selection that are no longer in the circuit."""
    raise NotImplementedError
