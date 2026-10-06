"""Headless guarded action execution for dirty session lifecycle prompts."""

from collections.abc import Callable
from enum import Enum, auto

from libqsim.application.session import EditorSession, SaveStatus

__all__ = ["UserChoice", "run_guarded"]


class UserChoice(Enum):
    """User response when prompted about unsaved changes."""

    SAVE = auto()
    DONT_SAVE = auto()
    CANCEL = auto()


def run_guarded(
    session: EditorSession,
    choice: UserChoice | None,
    save_fn: Callable[[], bool],
    action_fn: Callable[[], bool | None],
) -> bool:
    """Execute an action guarded by SaveStatus, implementing LC-12 to LC-15.

    If session is Clean: runs action_fn and returns True.
    If session is Dirty:
      - SAVE: calls save_fn; if save succeeds, runs action_fn and returns True;
        if save fails or is cancelled, leaves state unchanged and returns False.
      - DONT_SAVE: runs action_fn and returns True (if action fails, nothing is discarded).
      - CANCEL: does nothing and returns False.
    """
    if session.save_status == SaveStatus.CLEAN:
        action_fn()
        return True

    if choice == UserChoice.SAVE:
        saved = save_fn()
        if not saved:
            return False
        action_fn()
        return True

    if choice == UserChoice.DONT_SAVE:
        action_fn()
        return True

    # UserChoice.CANCEL or None
    return False
