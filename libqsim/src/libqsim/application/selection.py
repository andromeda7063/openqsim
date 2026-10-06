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
    for p in circuit.placements:
        if p.column == column and qubit in p.occupied_qubits:
            return p
    return None


def gates_in_rect(
    circuit: Circuit,
    q_min: int,
    q_max: int,
    c_min: int,
    c_max: int,
) -> frozenset[GatePlacement]:
    """Return all whole gate placements that intersect the given (qubit, column) rectangle."""
    min_q, max_q = min(q_min, q_max), max(q_min, q_max)
    min_c, max_c = min(c_min, c_max), max(c_min, c_max)

    matches: list[GatePlacement] = []
    for p in circuit.placements:
        if min_c <= p.column <= max_c and any(min_q <= q <= max_q for q in p.occupied_qubits):
            matches.append(p)
    return frozenset(matches)


def select_all(
    circuit: Circuit,
) -> frozenset[GatePlacement]:
    """Return a selection containing all gate placements in the circuit."""
    return frozenset(circuit.placements)


def click_selection(
    current: frozenset[GatePlacement],
    hit: GatePlacement | None,
    ctrl: bool = False,
) -> frozenset[GatePlacement]:
    """Compute the new selection resulting from a mouse click on hit (or empty space)."""
    if hit is None:
        return current if ctrl else frozenset()

    if not ctrl:
        return frozenset({hit})

    if hit in current:
        return current - {hit}
    return current | {hit}


def marquee_selection(
    current: frozenset[GatePlacement],
    rect_gates: Iterable[GatePlacement],
    ctrl: bool = False,
) -> frozenset[GatePlacement]:
    """Compute the new selection resulting from a marquee rectangle selection."""
    rect_set = frozenset(rect_gates)
    if not ctrl:
        return rect_set
    return current ^ rect_set


def prune_selection(
    circuit: Circuit,
    selection: frozenset[GatePlacement],
) -> frozenset[GatePlacement]:
    """Prune any placements from selection that are no longer in the circuit."""
    return frozenset(p for p in selection if p in circuit.placements)
