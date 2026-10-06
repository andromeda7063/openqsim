"""Headless editor session managing circuit lifecycle, history, and simulation state."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from libqsim.application.history import History
from libqsim.application.operations import OperationResult
from libqsim.domain.models import Circuit
from libqsim.domain.validation import validate
from libqsim.persistence.qcs import QcsError, read, write
from libqsim.simulation.engine import (
    InvalidCircuitError,
    SimulationError,
)
from libqsim.simulation.engine import (
    simulate as default_simulate,
)
from libqsim.simulation.results import SimulationResult

__all__ = [
    "EditorSession",
    "IoOutcome",
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


@dataclass(frozen=True)
class IoOutcome:
    """Outcome of an IO operation (open, save, save_as)."""

    ok: bool
    message: str = ""
    needs_path: bool = False


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
        """The current circuit definition."""
        return self._circuit

    @property
    def file_path(self) -> Path | None:
        """The current session file path, or None if unsaved/unassociated."""
        return self._file_path

    @property
    def baseline(self) -> Circuit | None:
        """The saved baseline circuit definition, or None if session has no baseline."""
        return self._baseline

    @property
    def save_status(self) -> SaveStatus:
        """Save status dynamically computed against the saved baseline."""
        if self._baseline is not None and self._circuit == self._baseline:
            return SaveStatus.CLEAN
        return SaveStatus.DIRTY

    @property
    def simulation_status(self) -> SimulationStatus:
        """Simulation status of the session."""
        if self._simulation_result is None:
            return SimulationStatus.NONE
        return self._simulation_status

    @property
    def simulation_result(self) -> SimulationResult | None:
        """The currently retained simulation result, if any."""
        return self._simulation_result

    @property
    def can_undo(self) -> bool:
        """True if an undo operation is available."""
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        """True if a redo operation is available."""
        return self._history.can_redo

    def apply(self, result: OperationResult) -> bool:
        """Apply an editing operation result to the session.

        On 'applied': commits once to history, updates circuit, clears redo,
        marks existing simulation result STALE, and notifies subscribers.
        On 'noop' or 'rejected': leaves session completely unchanged.
        """
        if result.status != "applied":
            return False
        self._history.push(self._circuit)
        self._circuit = result.circuit
        if self._simulation_result is not None:
            self._simulation_status = SimulationStatus.STALE
        self._notify()
        return True

    def undo(self) -> bool:
        """Undo the last circuit mutation."""
        prev = self._history.undo(self._circuit)
        if prev is None:
            return False
        self._circuit = prev
        if self._simulation_result is not None:
            self._simulation_status = SimulationStatus.STALE
        self._notify()
        return True

    def redo(self) -> bool:
        """Redo the previously undone circuit mutation."""
        nxt = self._history.redo(self._circuit)
        if nxt is None:
            return False
        self._circuit = nxt
        if self._simulation_result is not None:
            self._simulation_status = SimulationStatus.STALE
        self._notify()
        return True

    def run(
        self,
        simulate_fn: Callable[[Circuit], SimulationResult] | None = None,
    ) -> RunOutcome:
        """Validate and simulate the current circuit synchronously.

        Validates first; if invalid, simulation is not invoked.
        On success, replaces the simulation result and sets SimulationStatus to CURRENT.
        On failure, leaves existing result and simulation status unchanged.
        """
        sim = simulate_fn if simulate_fn is not None else default_simulate
        errors = validate(self._circuit)
        if errors:
            return RunOutcome(ok=False, messages=tuple(e.message for e in errors))

        try:
            res = sim(self._circuit)
        except (InvalidCircuitError, SimulationError) as exc:
            return RunOutcome(ok=False, messages=(str(exc),))

        self._simulation_result = res
        self._simulation_status = SimulationStatus.CURRENT
        self._notify()
        return RunOutcome(ok=True)

    def new(self) -> None:
        """Reset session to a new empty 2-qubit circuit with clean baseline and empty history."""
        self._circuit = Circuit(num_qubits=2)
        self._baseline = self._circuit
        self._file_path = None
        self._simulation_result = None
        self._simulation_status = SimulationStatus.NONE
        self._history.clear()
        self._notify()

    def establish_loaded(self, circuit: Circuit, path: Path) -> None:
        """Establish a loaded circuit and file path as the clean baseline."""
        self._circuit = circuit
        self._baseline = circuit
        self._file_path = path
        self._simulation_result = None
        self._simulation_status = SimulationStatus.NONE
        self._history.clear()
        self._notify()

    def establish_imported(self, circuit: Circuit) -> None:
        """Establish an imported circuit as an unsaved session with no baseline."""
        self._circuit = circuit
        self._baseline = None
        self._file_path = None
        self._simulation_result = None
        self._simulation_status = SimulationStatus.NONE
        self._history.clear()
        self._notify()

    def mark_saved(self, path: Path | None = None) -> None:
        """Establish the current circuit as the clean baseline and optionally update file path."""
        self._baseline = self._circuit
        if path is not None:
            self._file_path = path
        self._notify()

    def save(self) -> IoOutcome:
        """Save the session to its current file path."""
        if self._file_path is None:
            return IoOutcome(ok=False, message="No file path specified", needs_path=True)
        return self.save_as(self._file_path)

    def save_as(self, path: Path | str) -> IoOutcome:
        """Save the session to the specified file path."""
        target_path = Path(path)
        try:
            write(target_path, self._circuit)
        except QcsError as exc:
            return IoOutcome(ok=False, message=str(exc))
        self.mark_saved(target_path)
        return IoOutcome(ok=True)

    def open(self, path: Path | str) -> IoOutcome:
        """Open a QCS file and establish it as the session circuit."""
        target_path = Path(path)
        try:
            loaded_circuit = read(target_path)
        except QcsError as exc:
            return IoOutcome(ok=False, message=str(exc))
        self.establish_loaded(loaded_circuit, target_path)
        return IoOutcome(ok=True)

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to session state changes. Returns an unsubscribe callable."""
        self._subscribers.append(callback)
        return lambda: self.unsubscribe(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        """Unsubscribe a callback from session state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        """Notify all subscribers of a state change."""
        for callback in list(self._subscribers):
            callback()
