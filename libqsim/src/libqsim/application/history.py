"""Undo/redo history tracking for Circuit snapshots."""

from libqsim.domain.models import Circuit

__all__ = ["History"]


class History:
    """Manages undo and redo stacks of Circuit snapshots."""

    def __init__(self) -> None:
        self._undo_stack: list[Circuit] = []
        self._redo_stack: list[Circuit] = []

    @property
    def can_undo(self) -> bool:
        raise NotImplementedError

    @property
    def can_redo(self) -> bool:
        raise NotImplementedError

    def push(self, current_circuit: Circuit) -> None:
        """Record the current circuit state before a mutation, clearing redo history."""
        raise NotImplementedError

    def undo(self, current_circuit: Circuit) -> Circuit | None:
        """Move one step back in history, pushing the current circuit to redo."""
        raise NotImplementedError

    def redo(self, current_circuit: Circuit) -> Circuit | None:
        """Move one step forward in history, pushing the current circuit to undo."""
        raise NotImplementedError

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        raise NotImplementedError
