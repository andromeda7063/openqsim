"""Headless guarded action execution for dirty session lifecycle prompts."""

from collections.abc import Callable
from enum import Enum, auto

from libqsim.application.session import EditorSession

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

    Returns True if the action was executed, False otherwise.
    """
    raise NotImplementedError
