"""User interface protocols and implementations for modals and dialogs."""

from pathlib import Path
from typing import Protocol

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


class StubUserInterface:
    """Test stub recording dialog invocations without opening GUI windows."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.confirms: list[tuple[str, str]] = []
        self.confirm_response: bool = True
        self.open_file_result: Path | None = None
        self.save_file_result: Path | None = None

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
