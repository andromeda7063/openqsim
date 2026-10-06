"""State adapter bridging headless EditorSession to Qt signals."""

from collections.abc import Callable
from pathlib import Path

from libqsim.application.operations import OperationResult
from libqsim.application.session import EditorSession, RunOutcome, SaveStatus, SimulationStatus
from libqsim.domain.models import Circuit
from libqsim.simulation.results import SimulationResult
from PySide6.QtCore import QObject, Signal


class SessionAdapter(QObject):
    """Qt adapter for EditorSession. Contains no state logic, only forwarding."""

    changed = Signal()

    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._unsubscribe: Callable[[], None] | None = None

    @property
    def session(self) -> EditorSession:
        return self._session

    @property
    def circuit(self) -> Circuit:
        return self._session.circuit

    @property
    def file_path(self) -> Path | None:
        return self._session.file_path

    @property
    def baseline(self) -> Circuit | None:
        return self._session.baseline

    @property
    def save_status(self) -> SaveStatus:
        return self._session.save_status

    @property
    def simulation_status(self) -> SimulationStatus:
        return self._session.simulation_status

    @property
    def simulation_result(self) -> SimulationResult | None:
        return self._session.simulation_result

    @property
    def can_undo(self) -> bool:
        return self._session.can_undo

    @property
    def can_redo(self) -> bool:
        return self._session.can_redo

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

    def detach(self) -> None:
        raise NotImplementedError
