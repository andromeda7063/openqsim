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
        """True if there is at least one historical snapshot to undo to."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """True if there is at least one undone snapshot to redo to."""
        return len(self._redo_stack) > 0

    def push(self, current_circuit: Circuit) -> None:
        """Record the current circuit state before a mutation, clearing redo history."""
        self._undo_stack.append(current_circuit)
        self._redo_stack.clear()

    def undo(self, current_circuit: Circuit) -> Circuit | None:
        """Move one step back in history, pushing the current circuit to redo.

        Returns the previous circuit snapshot, or None if the undo stack is empty.
        """
        if not self._undo_stack:
            return None
        self._redo_stack.append(current_circuit)
        return self._undo_stack.pop()

    def redo(self, current_circuit: Circuit) -> Circuit | None:
        """Move one step forward in history, pushing the current circuit to undo.

        Returns the next circuit snapshot, or None if the redo stack is empty.
        """
        if not self._redo_stack:
            return None
        self._undo_stack.append(current_circuit)
        return self._redo_stack.pop()

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()
