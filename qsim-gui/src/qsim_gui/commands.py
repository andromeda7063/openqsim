"""Command actions and shortcut bindings for the GUI."""

from collections.abc import Callable
from pathlib import Path

from libqsim.application.guarded import run_guarded
from libqsim.application.operations import (
    Clipboard,
    clear,
    copy_gates,
    delete_gates,
    paste,
)
from libqsim.application.session import SaveStatus
from libqsim.examples import CircuitExample
from libqsim.qasm.importer import QasmError, import_text
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from qsim_gui.dialogs import UserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.selection_controller import SelectionController


class CommandActions:
    """Manages QActions, shortcut bindings, and wiring to the session adapter."""

    def __init__(
        self,
        parent: QWidget,
        adapter: SessionAdapter,
        ui: UserInterface,
        selection_controller: SelectionController | None = None,
    ) -> None:
        self._parent = parent
        self._adapter = adapter
        self._ui = ui
        self._selection_controller: SelectionController | None = None
        self._clipboard: Clipboard | None = None

        # Callbacks for image export
        self.on_export_circuit_image: Callable[[Path | str | None], bool] | None = None
        self.on_export_bloch_image: Callable[[Path | str | None], bool] | None = None
        self.on_export_histogram_image: Callable[[Path | str | None], bool] | None = None

        # File actions
        self.action_new = QAction("New", parent)
        self.action_new.setShortcut(QKeySequence("Ctrl+N"))
        self.action_new.setEnabled(False)
        self.action_new.triggered.connect(self.handle_new)

        self.action_open = QAction("Open...", parent)
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_open.setEnabled(False)
        self.action_open.triggered.connect(lambda: self.handle_open())

        self.action_save = QAction("Save", parent)
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save.setEnabled(False)
        self.action_save.triggered.connect(self.handle_save)

        self.action_save_as = QAction("Save As...", parent)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.setEnabled(False)
        self.action_save_as.triggered.connect(lambda: self.handle_save_as())

        self.action_import_qasm = QAction("Import OpenQASM...", parent)
        self.action_import_qasm.setEnabled(False)
        self.action_import_qasm.triggered.connect(lambda: self.handle_import_qasm())

        self.action_export_qasm = QAction("Export OpenQASM...", parent)
        self.action_export_qasm.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export_qasm.setEnabled(False)
        self.action_export_qasm.triggered.connect(lambda: self.handle_export_qasm())

        self.action_export_image = QAction("Export Image...", parent)
        self.action_export_image.setEnabled(False)
        self.action_export_image.triggered.connect(lambda: self.handle_export_circuit_image())

        self.action_export_circuit_image = QAction("Export Circuit Diagram (PNG)...", parent)
        self.action_export_circuit_image.setEnabled(False)
        self.action_export_circuit_image.triggered.connect(
            lambda: self.handle_export_circuit_image()
        )

        self.action_export_bloch_image = QAction("Export Bloch View (PNG)...", parent)
        self.action_export_bloch_image.setEnabled(False)
        self.action_export_bloch_image.triggered.connect(lambda: self.handle_export_bloch_image())

        self.action_export_histogram_image = QAction("Export Histogram (PNG)...", parent)
        self.action_export_histogram_image.setEnabled(False)
        self.action_export_histogram_image.triggered.connect(
            lambda: self.handle_export_histogram_image()
        )

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
        self.action_copy.triggered.connect(self._handle_copy)

        self.action_paste = QAction("Paste", parent)
        self.action_paste.setShortcut(QKeySequence("Ctrl+V"))
        self.action_paste.setEnabled(False)
        self.action_paste.triggered.connect(self._handle_paste)

        self.action_delete = QAction("Delete", parent)
        self.action_delete.setShortcuts([QKeySequence("Delete"), QKeySequence("Backspace")])
        self.action_delete.setEnabled(False)
        self.action_delete.triggered.connect(self._handle_delete)

        self.action_select_all = QAction("Select All", parent)
        self.action_select_all.setShortcut(QKeySequence("Ctrl+A"))
        self.action_select_all.setEnabled(False)
        self.action_select_all.triggered.connect(self._handle_select_all)

        self.action_clear = QAction("Clear", parent)
        self.action_clear.setEnabled(False)
        self.action_clear.triggered.connect(self._handle_clear)

        self.action_change_target = QAction("Change Target", parent)
        self.action_change_target.setEnabled(False)
        self.action_change_target.triggered.connect(self._handle_change_target)

        # Simulate actions
        self.action_run = QAction("Run", parent)
        self.action_run.setEnabled(True)
        self.action_run.triggered.connect(self._handle_run)

        # Connect adapter changes to action update
        self._adapter.changed.connect(self.update_actions)

        if selection_controller is not None:
            self.set_selection_controller(selection_controller)
        else:
            self.update_actions()

    @property
    def clipboard(self) -> Clipboard | None:
        """The current in-app clipboard object."""
        return self._clipboard

    def set_selection_controller(self, controller: SelectionController) -> None:
        """Bind a selection controller and listen to selection changes."""
        self._selection_controller = controller
        self._selection_controller.subscribe(self.update_actions)
        self.update_actions()

    def update_actions(self) -> None:
        """Update action enabled states from session adapter state."""
        self.action_undo.setEnabled(self._adapter.can_undo)
        self.action_redo.setEnabled(self._adapter.can_redo)
        self.action_run.setEnabled(True)

        has_gates = len(self._adapter.circuit.placements) > 0
        self.action_select_all.setEnabled(has_gates)
        self.action_clear.setEnabled(has_gates)

        has_selection = (
            self._selection_controller is not None and len(self._selection_controller.selection) > 0
        )
        self.action_delete.setEnabled(has_selection)
        self.action_copy.setEnabled(has_selection)

        has_clipboard = self._clipboard is not None and len(self._clipboard.placements) > 0
        self.action_paste.setEnabled(has_clipboard)

        can_change_target = (
            self._selection_controller is not None
            and self._selection_controller.can_change_target()
        )
        self.action_change_target.setEnabled(can_change_target)

    def _handle_copy(self) -> None:
        if self._selection_controller is None or not self._selection_controller.selection:
            return
        clip = copy_gates(self._adapter.circuit, self._selection_controller.selection)
        if clip is not None:
            self._clipboard = clip
            self.update_actions()

    def _handle_paste(self) -> None:
        if self._clipboard is None or not self._clipboard.placements:
            return
        anchor = (
            self._selection_controller.last_clicked_cell
            if (
                self._selection_controller
                and self._selection_controller.last_clicked_cell is not None
            )
            else (0, 0)
        )
        res = paste(
            self._adapter.circuit,
            self._clipboard,
            anchor_qubit=anchor[0],
            anchor_column=anchor[1],
        )
        if res.status == "applied":
            self._adapter.apply(res)
        elif res.status == "rejected":
            self._ui.show_error("Paste Error", "\n".join(res.messages))

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

    def _handle_delete(self) -> None:
        if self._selection_controller is None or not self._selection_controller.selection:
            return
        res = delete_gates(self._adapter.circuit, self._selection_controller.selection)
        if res.status == "applied":
            self._adapter.apply(res)
            self._selection_controller.clear_selection()
        elif res.status == "rejected":
            self._ui.show_error("Delete Error", "\n".join(res.messages))

    def _handle_select_all(self) -> None:
        if self._selection_controller is not None:
            self._selection_controller.select_all(self._adapter.circuit)

    def _handle_clear(self) -> None:
        res = clear(self._adapter.circuit)
        if res.status == "applied":
            self._adapter.apply(res)
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
        elif res.status == "rejected":
            self._ui.show_error("Clear Error", "\n".join(res.messages))

    def _handle_change_target(self) -> None:
        if self._selection_controller is None or not self._selection_controller.can_change_target():
            return
        res = self._selection_controller.change_target_selected(self._adapter.circuit)
        if res.status == "applied":
            self._adapter.apply(res)
            self._selection_controller.follow_move(res)
        elif res.status == "rejected":
            self._ui.show_error("Change Target Error", "\n".join(res.messages))

    def enable_file_actions(self, enabled: bool = True) -> None:
        """Enable or disable file and export actions."""
        self.action_new.setEnabled(enabled)
        self.action_open.setEnabled(enabled)
        self.action_save.setEnabled(enabled)
        self.action_save_as.setEnabled(enabled)
        self.action_import_qasm.setEnabled(enabled)
        self.action_export_qasm.setEnabled(enabled)
        self.action_export_image.setEnabled(enabled)
        self.action_export_circuit_image.setEnabled(enabled)
        self.action_export_bloch_image.setEnabled(enabled)
        self.action_export_histogram_image.setEnabled(enabled)

    def handle_new(self) -> bool:
        """Create a new circuit, prompting if session is dirty."""
        success = False

        def action() -> bool:
            nonlocal success
            self._adapter.session.new()
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
            success = True
            return True

        choice = None
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes",
                "Save changes before creating a new circuit?",
            )
        guarded_ok = run_guarded(self._adapter.session, choice, self.handle_save, action)
        return guarded_ok and success

    def handle_load_example(self, example: CircuitExample) -> bool:
        """Load a built-in example as a new unsaved session."""
        success = False

        def action() -> bool:
            nonlocal success
            outcome = self._adapter.session.load_example(example)
            if not outcome.ok:
                self._ui.show_error("Load Example Error", outcome.message)
                return False
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
            success = True
            return True

        choice = None
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes", "Save changes before loading an example?"
            )
        guarded_ok = run_guarded(self._adapter.session, choice, self.handle_save, action)
        return guarded_ok and success

    def handle_open(self, path: Path | str | None = None) -> bool:
        """Open a .qcs file, prompting if session is dirty."""
        success = False

        def action() -> bool:
            nonlocal success
            target_path = (
                Path(path)
                if path is not None
                else self._ui.choose_open_file(
                    "Open Circuit", "OpenQSim Circuit (*.qcs);;All Files (*)"
                )
            )
            if target_path is None:
                return False
            outcome = self._adapter.session.open(target_path)
            if not outcome.ok:
                self._ui.show_error("Open Error", outcome.message)
                return False
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
            success = True
            return True

        choice = None
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes",
                "Save changes before opening another circuit?",
            )
        guarded_ok = run_guarded(self._adapter.session, choice, self.handle_save, action)
        return guarded_ok and success

    def handle_save(self) -> bool:
        """Save the session, prompting for path if none is set."""
        if self._adapter.file_path is None:
            return self.handle_save_as()
        outcome = self._adapter.session.save()
        if not outcome.ok:
            self._ui.show_error("Save Error", outcome.message)
            return False
        return True

    def handle_save_as(self, path: Path | str | None = None) -> bool:
        """Save session to a specific or user-selected path."""
        target_path = (
            Path(path)
            if path is not None
            else self._ui.choose_save_file(
                "Save Circuit As",
                "OpenQSim Circuit (*.qcs);;All Files (*)",
                default_name="circuit.qcs",
            )
        )
        if target_path is None:
            return False
        outcome = self._adapter.session.save_as(target_path)
        if not outcome.ok:
            self._ui.show_error("Save Error", outcome.message)
            return False
        return True

    def handle_import_qasm(self, path: Path | str | None = None) -> bool:
        """Import OpenQASM 2.0 file, prompting if session is dirty."""
        success = False

        def action() -> bool:
            nonlocal success
            target_path = (
                Path(path)
                if path is not None
                else self._ui.choose_open_file(
                    "Import OpenQASM", "OpenQASM (*.qasm);;All Files (*)"
                )
            )
            if target_path is None:
                return False
            outcome = self._adapter.session.import_qasm(target_path)
            if not outcome.ok:
                self._ui.show_error("Import Error", outcome.message)
                return False
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
            success = True
            return True

        choice = None
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes",
                "Save changes before importing OpenQASM?",
            )
        guarded_ok = run_guarded(self._adapter.session, choice, self.handle_save, action)
        return guarded_ok and success

    def handle_apply_qasm(self, source: str) -> bool:
        """Apply valid OpenQASM text, prompting before discarding a dirty session."""
        try:
            circuit = import_text(source)
        except QasmError as exc:
            self._ui.show_error("Import Error", str(exc))
            return False

        def action() -> bool:
            self._adapter.session.establish_imported(circuit)
            if self._selection_controller is not None:
                self._selection_controller.clear_selection()
            return True

        choice = None
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes",
                "Save changes before applying OpenQASM?",
            )
        return run_guarded(self._adapter.session, choice, self.handle_save, action)

    def handle_export_qasm(self, path: Path | str | None = None) -> bool:
        """Export circuit to OpenQASM 2.0 file."""
        target_path = (
            Path(path)
            if path is not None
            else self._ui.choose_save_file(
                "Export OpenQASM",
                "OpenQASM (*.qasm);;All Files (*)",
                default_name="circuit.qasm",
            )
        )
        if target_path is None:
            return False
        outcome = self._adapter.session.export_qasm(target_path)
        if not outcome.ok:
            self._ui.show_error("Export Error", outcome.message)
            return False
        return True

    def handle_export_circuit_image(self, path: Path | str | None = None) -> bool:
        """Export circuit diagram to PNG file."""
        if self.on_export_circuit_image is not None:
            return self.on_export_circuit_image(path)
        return False

    def handle_export_bloch_image(self, path: Path | str | None = None) -> bool:
        """Export Bloch view to PNG file."""
        if self.on_export_bloch_image is not None:
            return self.on_export_bloch_image(path)
        return False

    def handle_export_histogram_image(self, path: Path | str | None = None) -> bool:
        """Export histogram view to PNG file."""
        if self.on_export_histogram_image is not None:
            return self.on_export_histogram_image(path)
        return False
