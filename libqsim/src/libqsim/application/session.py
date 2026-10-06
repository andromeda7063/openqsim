"""Headless editor session managing circuit lifecycle, history, and simulation state."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from libqsim.application.history import History
from libqsim.application.operations import OperationResult
from libqsim.domain.models import Circuit
from libqsim.simulation.results import SimulationResult

__all__ = [
    "EditorSession",
    "RunOutcome",
    "SaveStatus",
    "SimulationStatus",
]


class SaveStatus(Enum):
    """Save status of an editor session relative to its saved baseline."""

    CLEAN = auto()
    DIRTY = auto()


class SimulationStatus(Enum):
    """Simulation status of an editor session."""

    NONE = auto()
    CURRENT = auto()
    STALE = auto()


@dataclass(frozen=True)
class RunOutcome:
    """Outcome of running a simulation through the editor session."""

    ok: bool
    messages: tuple[str, ...] = ()


class EditorSession:
    """Headless editor session managing state transitions, history, and simulation."""

    def __init__(self) -> None:
        self._circuit: Circuit = Circuit(num_qubits=2)
        self._baseline: Circuit | None = self._circuit
        self._file_path: Path | None = None
        self._simulation_result: SimulationResult | None = None
        self._simulation_status: SimulationStatus = SimulationStatus.NONE
        self._history: History = History()
        self._subscribers: list[Callable[[], None]] = []

    @property
    def circuit(self) -> Circuit:
        raise NotImplementedError

    @property
    def file_path(self) -> Path | None:
        raise NotImplementedError

    @property
    def baseline(self) -> Circuit | None:
        raise NotImplementedError

    @property
    def save_status(self) -> SaveStatus:
        raise NotImplementedError

    @property
    def simulation_status(self) -> SimulationStatus:
        raise NotImplementedError

    @property
    def simulation_result(self) -> SimulationResult | None:
        raise NotImplementedError

    @property
    def can_undo(self) -> bool:
        raise NotImplementedError

    @property
    def can_redo(self) -> bool:
        raise NotImplementedError

    def apply(self, result: OperationResult) -> bool:
        raise NotImplementedError

    def undo(self) -> bool:
        raise NotImplementedError

    def redo(self) -> bool:
        raise NotImplementedError

    def run(
        self,
        simulate_fn: Callable[[Circuit], SimulationResult] | None = None,
    ) -> RunOutcome:
        raise NotImplementedError

    def new(self) -> None:
        raise NotImplementedError

    def establish_loaded(self, circuit: Circuit, path: Path) -> None:
        raise NotImplementedError

    def establish_imported(self, circuit: Circuit) -> None:
        raise NotImplementedError

    def mark_saved(self, path: Path | None = None) -> None:
        raise NotImplementedError

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        raise NotImplementedError

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        raise NotImplementedError
