"""Command actions and shortcut bindings for the GUI."""

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from qsim_gui.dialogs import UserInterface
from qsim_gui.state import SessionAdapter


class CommandActions:
    """Manages QActions, shortcut bindings, and wiring to the session adapter."""

    def __init__(
        self,
        parent: QWidget,
        adapter: SessionAdapter,
        ui: UserInterface,
    ) -> None:
        self._parent = parent
        self._adapter = adapter
        self._ui = ui

        # File actions
        self.action_new = QAction("New", parent)
        self.action_new.setShortcut(QKeySequence("Ctrl+N"))
        self.action_new.setEnabled(False)

        self.action_open = QAction("Open...", parent)
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_open.setEnabled(False)

        self.action_save = QAction("Save", parent)
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save.setEnabled(False)

        self.action_save_as = QAction("Save As...", parent)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.setEnabled(False)

        self.action_import_qasm = QAction("Import OpenQASM...", parent)
        self.action_import_qasm.setEnabled(False)

        self.action_export_qasm = QAction("Export OpenQASM...", parent)
        self.action_export_qasm.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export_qasm.setEnabled(False)

        self.action_export_image = QAction("Export Image...", parent)
        self.action_export_image.setEnabled(False)

        # Edit actions
        self.action_undo = QAction("Undo", parent)
        self.action_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.action_undo.setEnabled(self._adapter.can_undo)
        self.action_undo.triggered.connect(self._handle_undo)

        self.action_redo = QAction("Redo", parent)
        self.action_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.action_redo.setEnabled(self._adapter.can_redo)
        self.action_redo.triggered.connect(self._handle_redo)

        self.action_copy = QAction("Copy", parent)
        self.action_copy.setShortcut(QKeySequence("Ctrl+C"))
        self.action_copy.setEnabled(False)

        self.action_paste = QAction("Paste", parent)
        self.action_paste.setShortcut(QKeySequence("Ctrl+V"))
        self.action_paste.setEnabled(False)

        self.action_delete = QAction("Delete", parent)
        self.action_delete.setShortcuts([QKeySequence("Delete"), QKeySequence("Backspace")])
        self.action_delete.setEnabled(False)

        self.action_select_all = QAction("Select All", parent)
        self.action_select_all.setShortcut(QKeySequence("Ctrl+A"))
        self.action_select_all.setEnabled(False)

        # Simulate actions
        self.action_run = QAction("Run", parent)
        self.action_run.setEnabled(True)
        self.action_run.triggered.connect(self._handle_run)

        # Connect adapter changes to action update
        self._adapter.changed.connect(self.update_actions)

    def update_actions(self) -> None:
        """Update action enabled states from session adapter state."""
        self.action_undo.setEnabled(self._adapter.can_undo)
        self.action_redo.setEnabled(self._adapter.can_redo)
        self.action_run.setEnabled(True)

    def _handle_undo(self) -> None:
        self._adapter.undo()

    def _handle_redo(self) -> None:
        self._adapter.redo()

    def _handle_run(self) -> None:
        outcome = self._adapter.run()
        if not outcome.ok:
            error_text = (
                "\n".join(outcome.messages) if outcome.messages else "Simulation execution failed."
            )
            self._ui.show_error("Simulation Error", error_text)
