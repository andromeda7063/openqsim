"""User interface protocols and implementations for modals and dialogs."""

from pathlib import Path
from typing import Protocol

from libqsim.application.guarded import UserChoice
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


class UserInterface(Protocol):
    """Abstract user interface protocol for modals and dialogs."""

    def show_error(self, title: str, message: str) -> None:
        """Display an error message using plain language without raw tracebacks."""
        ...

    def confirm(self, title: str, message: str) -> bool:
        """Display a confirmation dialog."""
        ...

    def choose_open_file(self, title: str, filter_pattern: str) -> Path | None:
        """Prompt user to choose an existing file to open."""
        ...

    def choose_save_file(
        self, title: str, filter_pattern: str, default_name: str = ""
    ) -> Path | None:
        """Prompt user to choose a target save file path."""
        ...

    def prompt_save_changes(self, title: str, message: str) -> UserChoice:
        """Prompt user about unsaved changes with Save, Don't Save, and Cancel choices."""
        ...


class QtUserInterface:
    """Qt-backed implementation of UserInterface."""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._parent = parent

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self._parent, title, message)

    def confirm(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            self._parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def choose_open_file(self, title: str, filter_pattern: str) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(self._parent, title, "", filter_pattern)
        return Path(path) if path else None

    def choose_save_file(
        self, title: str, filter_pattern: str, default_name: str = ""
    ) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(self._parent, title, default_name, filter_pattern)
        return Path(path) if path else None

    def prompt_save_changes(self, title: str, message: str) -> UserChoice:
        msg_box = QMessageBox(self._parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        save_btn = msg_box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        dont_save_btn = msg_box.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
        msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(save_btn)
        msg_box.exec()
        clicked = msg_box.clickedButton()
        if clicked == save_btn:
            return UserChoice.SAVE
        elif clicked == dont_save_btn:
            return UserChoice.DONT_SAVE
        else:
            return UserChoice.CANCEL


class StubUserInterface:
    """Test stub recording dialog invocations without opening GUI windows."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.confirms: list[tuple[str, str]] = []
        self.confirm_response: bool = True
        self.open_file_result: Path | None = None
        self.save_file_result: Path | None = None
        self.save_prompt_choices: list[UserChoice] = []
        self.save_prompt_response: UserChoice = UserChoice.SAVE
        self.save_prompts: list[tuple[str, str]] = []

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def confirm(self, title: str, message: str) -> bool:
        self.confirms.append((title, message))
        return self.confirm_response

    def choose_open_file(self, title: str, filter_pattern: str) -> Path | None:
        return self.open_file_result

    def choose_save_file(
        self, title: str, filter_pattern: str, default_name: str = ""
    ) -> Path | None:
        return self.save_file_result

    def prompt_save_changes(self, title: str, message: str) -> UserChoice:
        self.save_prompts.append((title, message))
        if self.save_prompt_choices:
            return self.save_prompt_choices.pop(0)
        return self.save_prompt_response
