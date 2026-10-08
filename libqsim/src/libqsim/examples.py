"""Built-in example circuits available without external files or network access."""

from dataclasses import dataclass

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import validate


@dataclass(frozen=True)
class CircuitExample:
    """A named, documented example circuit."""

    name: str
    description: str
    circuit: Circuit


_CATALOG = (
    CircuitExample(
        "Bell state",
        "Create a two-qubit entangled state with H and CNOT.",
        Circuit(
            2, (GatePlacement(GateType.H, (0,), (), 0), GatePlacement(GateType.CNOT, (1,), (0,), 1))
        ),
    ),
    CircuitExample(
        "GHZ state",
        "Extend entanglement across three qubits with two CNOT gates.",
        Circuit(
            3,
            (
                GatePlacement(GateType.H, (0,), (), 0),
                GatePlacement(GateType.CNOT, (1,), (0,), 1),
                GatePlacement(GateType.CNOT, (2,), (1,), 2),
            ),
        ),
    ),
    CircuitExample(
        "Interference",
        "Applying H twice returns the qubit to its initial state.",
        Circuit(
            1, (GatePlacement(GateType.H, (0,), (), 0), GatePlacement(GateType.H, (0,), (), 1))
        ),
    ),
    CircuitExample(
        "Phase demonstration",
        "Z, S, and T change phase; the final H converts phase into probabilities.",
        Circuit(
            1,
            (
                GatePlacement(GateType.H, (0,), (), 0),
                GatePlacement(GateType.Z, (0,), (), 1),
                GatePlacement(GateType.S, (0,), (), 2),
                GatePlacement(GateType.T, (0,), (), 3),
                GatePlacement(GateType.H, (0,), (), 4),
            ),
        ),
    ),
    CircuitExample(
        "Toffoli demonstration",
        "Two controls flip a middle-wire target after both controls are set to 1.",
        Circuit(
            3,
            (
                GatePlacement(GateType.X, (0,), (), 0),
                GatePlacement(GateType.X, (2,), (), 0),
                GatePlacement(GateType.Toffoli, (1,), (0, 2), 1),
            ),
        ),
    ),
)


def list_examples() -> tuple[CircuitExample, ...]:
    """Return the fixed built-in example catalog in display order."""
    return _CATALOG


def get_example(name: str) -> CircuitExample:
    """Return a catalog example by exact name."""
    for example in _CATALOG:
        if example.name == name:
            return example
    raise KeyError(name)


def validate_examples() -> tuple[str, ...]:
    """Return names of examples that fail normal circuit validation."""
    return tuple(example.name for example in _CATALOG if validate(example.circuit))
