"""Tests for domain models: GatePlacement and Circuit."""

from dataclasses import FrozenInstanceError

import pytest
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


@pytest.mark.req("FR-1.4", "FR-1.5", "FR-1.6")
def test_gate_placement_normalizes_controls_and_targets() -> None:
    """GatePlacement stores targets and controls as sorted tuples."""
    p1 = GatePlacement(GateType.CNOT, targets=[1], controls=[2, 0], column=0)
    p2 = GatePlacement(GateType.CNOT, targets=(1,), controls=(0, 2), column=0)

    assert p1.targets == (1,)
    assert p1.controls == (0, 2)
    assert p1 == p2
    assert hash(p1) == hash(p2)

    # Multi-target ordering normalization
    p3 = GatePlacement(GateType.X, targets=[3, 1], controls=[], column=1)
    assert p3.targets == (1, 3)


@pytest.mark.req("FR-1.4", "FR-1.5")
def test_gate_placement_occupied_qubits() -> None:
    """occupied_qubits returns a sorted tuple of targets + controls, preserving duplicates."""
    p = GatePlacement(GateType.Toffoli, targets=[2], controls=[1, 0], column=0)
    assert p.occupied_qubits == (0, 1, 2)

    # Duplicates preserved
    p_dup = GatePlacement(GateType.CNOT, targets=[1], controls=[1], column=0)
    assert p_dup.occupied_qubits == (1, 1)


@pytest.mark.req("FR-1.4", "FR-1.5")
def test_gate_placement_lowest_occupied_qubit() -> None:
    """lowest_occupied_qubit returns the lowest-indexed occupied wire or None if empty."""
    p = GatePlacement(GateType.CNOT, targets=[2], controls=[1], column=3)
    assert p.lowest_occupied_qubit == 1

    p_empty = GatePlacement(GateType.X, targets=[], controls=[], column=0)
    assert p_empty.lowest_occupied_qubit is None


@pytest.mark.req("FR-1.4")
def test_gate_placement_frozen() -> None:
    """Mutating any field on GatePlacement raises FrozenInstanceError."""
    p = GatePlacement(GateType.H, targets=[0], controls=[], column=0)

    with pytest.raises(FrozenInstanceError):
        p.column = 5  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        p.gate_type = GateType.X  # type: ignore[misc]


@pytest.mark.req("FR-1.4")
def test_gate_placement_invalid_data_does_not_raise() -> None:
    """GatePlacement constructs without raising on boundary or semantic violations."""
    p = GatePlacement("NonexistentGate", targets=[-1, 5], controls=[-3], column=99)
    assert p.column == 99
    assert p.targets == (-1, 5)
    assert p.controls == (-3,)
    assert p.occupied_qubits == (-3, -1, 5)
    assert p.lowest_occupied_qubit == -3


@pytest.mark.req("FR-1.1")
def test_circuit_placements_stored_as_tuple() -> None:
    """Circuit stores placements as a tuple and defaults to empty."""
    c_empty = Circuit(num_qubits=2)
    assert c_empty.placements == ()

    p = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    c = Circuit(num_qubits=2, placements=[p])
    assert isinstance(c.placements, tuple)
    assert c.placements == (p,)


@pytest.mark.req("FR-1.1", "FR-1.6")
def test_circuit_equality_and_hash_ignore_placement_order() -> None:
    """Circuits with identical placements in different order are equal and share hashes."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.X, targets=[1], controls=[], column=1)

    c1 = Circuit(num_qubits=2, placements=[p1, p2])
    c2 = Circuit(num_qubits=2, placements=[p2, p1])

    assert c1 == c2
    assert hash(c1) == hash(c2)

    # Different num_qubits are not equal
    c3 = Circuit(num_qubits=3, placements=[p1, p2])
    assert c1 != c3


@pytest.mark.req("FR-1.6")
def test_canonical_placements_deterministic_hand_checked_ordering() -> None:
    """canonical_placements sorts by (column, lowest occupied qubit, gate_type value, targets, controls)."""
    p_meas = GatePlacement(GateType.Measurement, targets=[1], controls=[], column=5)
    p_cnot2 = GatePlacement(GateType.CNOT, targets=[2], controls=[1], column=2)
    p_cnot1 = GatePlacement(GateType.CNOT, targets=[0], controls=[1], column=2)
    p_toff = GatePlacement(GateType.Toffoli, targets=[2], controls=[1, 0], column=1)
    p_z0 = GatePlacement(GateType.Z, targets=[0], controls=[], column=0)
    p_h0 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p_x1 = GatePlacement(GateType.X, targets=[1], controls=[], column=0)

    # Shuffled input order
    circuit = Circuit(
        num_qubits=3,
        placements=[p_meas, p_cnot2, p_toff, p_z0, p_h0, p_cnot1, p_x1],
    )

    expected = (
        p_h0,  # col 0, lowest 0, gate "H" < "Z"
        p_z0,  # col 0, lowest 0, gate "Z"
        p_x1,  # col 0, lowest 1
        p_toff,  # col 1, lowest 0
        p_cnot1,  # col 2, lowest 0
        p_cnot2,  # col 2, lowest 1
        p_meas,  # col 5, lowest 1
    )

    assert circuit.canonical_placements() == expected


@pytest.mark.req("FR-1.1")
def test_circuit_frozen_and_non_mutating_helpers() -> None:
    """Circuit is frozen; with_placements and with_num_qubits return new instances."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.X, targets=[1], controls=[], column=1)
    c = Circuit(num_qubits=2, placements=[p1])

    with pytest.raises(FrozenInstanceError):
        c.num_qubits = 4  # type: ignore[misc]

    c_new_placements = c.with_placements([p2])
    assert c_new_placements.placements == (p2,)
    assert c.placements == (p1,)
    assert c_new_placements.num_qubits == c.num_qubits
    assert c_new_placements is not c

    c_new_qubits = c.with_num_qubits(5)
    assert c_new_qubits.num_qubits == 5
    assert c.num_qubits == 2
    assert c_new_qubits.placements == c.placements
    assert c_new_qubits is not c


@pytest.mark.req("FR-1.1")
def test_circuit_invalid_data_does_not_raise() -> None:
    """Constructing Circuit with invalid parameters does not raise exceptions."""
    p_invalid = GatePlacement("InvalidGate", targets=[-1], controls=[], column=999)
    c = Circuit(num_qubits=-5, placements=[p_invalid])
    assert c.num_qubits == -5
    assert c.placements == (p_invalid,)
    assert c.canonical_placements() == (p_invalid,)
