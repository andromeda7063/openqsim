"""Main window of the OpenQSim application."""

from libqsim.application.session import EditorSession
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
)

from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import QtUserInterface, UserInterface
from qsim_gui.state import SessionAdapter


class MainWindow(QMainWindow):
    """OpenQSim application main window."""

    def __init__(
        self,
        adapter: SessionAdapter | None = None,
        ui: UserInterface | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if adapter is None:
            adapter = SessionAdapter(EditorSession())
        self._adapter = adapter
        self._ui = ui if ui is not None else QtUserInterface(self)
        self._commands = CommandActions(self, self._adapter, self._ui)

    @property
    def adapter(self) -> SessionAdapter:
        return self._adapter

    @property
    def commands(self) -> CommandActions:
        return self._commands

    @property
    def ui(self) -> UserInterface:
        return self._ui
