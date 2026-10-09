"""Main window of the OpenQSim application."""

from pathlib import Path

from libqsim.application.guarded import run_guarded
from libqsim.application.operations import plan_resize, resize
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.examples import list_examples
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QImage
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import QtUserInterface, UserInterface
from qsim_gui.help import HelpWindow, open_help_window
from qsim_gui.preferences import PreferencesDialog
from qsim_gui.state import SessionAdapter
from qsim_gui.theme import Theme, apply_theme
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import GatePalette
from qsim_gui.widgets.qasm_panel import QasmPanel
from qsim_gui.widgets.results_panel import ResultsPanel


class MainWindow(QMainWindow):
    """OpenQSim application main window."""

    def __init__(
        self,
        adapter: SessionAdapter | None = None,
        ui: UserInterface | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = QSettings("OpenQSim", "OpenQSim")
        self._theme = self._read_theme()
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self._theme)
        if adapter is None:
            adapter = SessionAdapter(EditorSession())
        self._adapter = adapter
        self._ui = ui if ui is not None else QtUserInterface(self)
        self._help_windows: list[HelpWindow] = []
        self._commands = CommandActions(self, self._adapter, self._ui)
        self._commands.on_export_circuit_image = self.export_circuit_image
        self._commands.on_export_bloch_image = self.export_bloch_image
        self._commands.on_export_histogram_image = self.export_histogram_image
        self._commands.enable_file_actions(True)

        self._setup_ui()
        self._adapter.changed.connect(self._on_session_changed)
        self._on_session_changed()

    @property
    def adapter(self) -> SessionAdapter:
        return self._adapter

    @property
    def commands(self) -> CommandActions:
        return self._commands

    @property
    def ui(self) -> UserInterface:
        return self._ui

    @property
    def canvas(self) -> CircuitCanvas:
        return self._canvas

    @property
    def palette(self) -> GatePalette:
        return self._palette

    @property
    def results_panel(self) -> ResultsPanel:
        return self._results_panel

    @property
    def help_windows(self) -> list[HelpWindow]:
        return self._help_windows

    def _open_help(self, doc_key: str, title: str) -> HelpWindow:
        win = open_help_window(doc_key, title, parent=self)
        self._help_windows.append(win)
        return win

    def _setup_ui(self) -> None:
        self._setup_menus()
        self._setup_toolbar()
        self._setup_central_regions()
        self._setup_status_bar()
        self.resize(1920, 1080)

    def _setup_menus(self) -> None:
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self._commands.action_new)
        file_menu.addAction(self._commands.action_open)
        file_menu.addAction(self._commands.action_save)
        file_menu.addAction(self._commands.action_save_as)
        examples_menu = menubar.addMenu("&Examples")
        self.example_actions: dict[str, QAction] = {}
        for example in list_examples():
            action = QAction(f"{example.name} — {example.description}", self)
            action.setToolTip(example.description)
            action.setStatusTip(example.description)
            action.triggered.connect(
                lambda checked=False, item=example: self._commands.handle_load_example(item)
            )
            examples_menu.addAction(action)
            self.example_actions[example.name] = action
        file_menu.addSeparator()
        file_menu.addAction(self._commands.action_import_qasm)
        file_menu.addAction(self._commands.action_export_qasm)

        export_image_menu = QMenu("Export &Image", self)
        export_image_menu.addAction(self._commands.action_export_circuit_image)
        export_image_menu.addAction(self._commands.action_export_bloch_image)
        export_image_menu.addAction(self._commands.action_export_histogram_image)
        file_menu.addMenu(export_image_menu)
        self._commands.action_export_image.setMenu(export_image_menu)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self._commands.action_undo)
        edit_menu.addAction(self._commands.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self._commands.action_copy)
        edit_menu.addAction(self._commands.action_paste)
        edit_menu.addAction(self._commands.action_delete)
        edit_menu.addAction(self._commands.action_select_all)
        edit_menu.addAction(self._commands.action_clear)
        edit_menu.addSeparator()
        edit_menu.addAction(self._commands.action_change_target)
        edit_menu.addSeparator()
        self.action_preferences = QAction("Preferences...", self)
        self.action_preferences.setObjectName("action_preferences")
        self.action_preferences.triggered.connect(self._open_preferences)
        edit_menu.addAction(self.action_preferences)

        # Simulate menu
        simulate_menu = menubar.addMenu("&Simulate")
        simulate_menu.addAction(self._commands.action_run)
        simulate_menu.addAction(self._commands.action_step_run)

        # Help menu
        self._help_menu: QMenu = menubar.addMenu("&Help")
        self.action_help_quick_start = QAction("Quick Start", self)
        self.action_help_quick_start.triggered.connect(
            lambda: self._open_help("quick-start", "Quick Start")
        )
        self._help_menu.addAction(self.action_help_quick_start)

        self.action_help_qcs = QAction("QCS Format", self)
        self.action_help_qcs.triggered.connect(lambda: self._open_help("qcs-format", "QCS Format"))
        self._help_menu.addAction(self.action_help_qcs)

        self.action_help_qasm = QAction("OpenQASM Support", self)
        self.action_help_qasm.triggered.connect(
            lambda: self._open_help("qasm-support", "OpenQASM Support")
        )
        self._help_menu.addAction(self.action_help_qasm)

        self._help_menu.addSeparator()

        self.action_help_about = QAction("About OpenQSim", self)
        self.action_help_about.triggered.connect(lambda: self._open_help("about", "About OpenQSim"))
        self._help_menu.addAction(self.action_help_about)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("main_toolbar")
        self.addToolBar(toolbar)

        toolbar_actions = (
            (self._commands.action_new, "file-plus"),
            (self._commands.action_open, "folder-open"),
            (self._commands.action_save, "save"),
            (self._commands.action_save_as, "file-pen"),
        )
        history_actions = (
            (self._commands.action_undo, "undo-2"),
            (self._commands.action_redo, "redo-2"),
        )
        icon_directory = Path(__file__).parent / "assets" / "icons"
        for action, icon_name in toolbar_actions:
            self._add_icon_action(toolbar, action, icon_directory / f"{icon_name}.svg")

        toolbar.addSeparator()
        for action, icon_name in history_actions:
            self._add_icon_action(toolbar, action, icon_directory / f"{icon_name}.svg")
        toolbar.addSeparator()
        self._add_icon_action(toolbar, self._commands.action_run, icon_directory / "play.svg")
        self._add_icon_action(
            toolbar, self._commands.action_step_run, icon_directory / "step-forward.svg"
        )
        toolbar.addSeparator()
        toolbar.addAction(self._commands.action_export_qasm)
        toolbar.addAction(self._commands.action_export_image)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Qubits: "))
        self._qubit_spin = QSpinBox(self)
        self._qubit_spin.setObjectName("qubit_spin_box")
        self._qubit_spin.setRange(1, 10)
        self._qubit_spin.setValue(self._adapter.circuit.num_qubits)
        self._qubit_spin.valueChanged.connect(self._on_qubit_count_changed)
        toolbar.addWidget(self._qubit_spin)

    @staticmethod
    def _add_icon_action(toolbar: QToolBar, action: QAction, icon_path: Path) -> None:
        action.setIcon(QIcon(str(icon_path)))
        action.setToolTip(action.text())
        toolbar.addAction(action)
        button = toolbar.widgetForAction(action)
        if button is not None:
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setAccessibleName(action.text().removesuffix("..."))

    def _setup_central_regions(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Three regions: gate palette, scrollable canvas, results panel
        self._palette = GatePalette(parent=self)
        self._palette.setObjectName("palette_region")

        self._canvas = CircuitCanvas(
            adapter=self._adapter,
            ui=self._ui,
            commands=self._commands,
            parent=self,
        )
        self._canvas.setObjectName("circuit_canvas")
        self._commands.set_selection_controller(self._canvas.selection_controller)
        self._commands.on_paste_applied = self._canvas.scroll_selection_into_view

        self._canvas_scroll = QScrollArea(self)
        self._canvas_scroll.setObjectName("canvas_region")
        self._canvas_scroll.setWidget(self._canvas)
        self._canvas_scroll.setWidgetResizable(False)

        self._results_panel = ResultsPanel(adapter=self._adapter, parent=self)
        self._results_panel.setObjectName("results_region")

        self._qasm_panel = QasmPanel(
            adapter=self._adapter,
            on_apply=self._commands.handle_apply_qasm,
            parent=self,
        )

        workspace = QSplitter(Qt.Orientation.Horizontal, central_widget)
        workspace.setObjectName("workspace_splitter")
        workspace.addWidget(self._palette)
        workspace.addWidget(self._canvas_scroll)
        workspace.addWidget(self._qasm_panel)
        workspace.setSizes([60, 1200, 380])

        regions = QSplitter(Qt.Orientation.Vertical, central_widget)
        regions.setObjectName("main_splitter")
        regions.addWidget(workspace)
        regions.addWidget(self._results_panel)
        regions.setSizes([600, 400])
        self._results_panel.setMinimumHeight(350)

        layout.addWidget(regions)

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        status_bar.setObjectName("status_bar")
        self.setStatusBar(status_bar)

        self._save_status_label = QLabel("Save: Clean", self)
        self._save_status_label.setObjectName("save_status_label")
        self._save_status_label.setProperty("status", "clean")

        self._sim_status_label = QLabel("Simulation: None", self)
        self._sim_status_label.setObjectName("sim_status_label")
        self._sim_status_label.setProperty("status", "none")

        status_bar.addPermanentWidget(self._save_status_label)
        status_bar.addPermanentWidget(self._sim_status_label)

    def _on_qubit_count_changed(self, n: int) -> None:
        curr_n = self._adapter.circuit.num_qubits
        if n == curr_n:
            return
        if n > curr_n:
            res = resize(self._adapter.circuit, n)
            if res.status == "applied":
                self._adapter.apply(res)
            elif res.status == "rejected":
                self._ui.show_error("Resize Error", "\n".join(res.messages))
                self._sync_qubit_spin()
        else:  # n < curr_n
            plan = plan_resize(self._adapter.circuit, n)
            if plan.needs_confirmation:
                msg = (
                    f"Decreasing the qubit count to {n} will delete "
                    f"{len(plan.affected)} affected gate(s). Proceed?"
                )
                confirmed = self._ui.confirm("Confirm Resize", msg)
                if not confirmed:
                    self._sync_qubit_spin()
                    return
                res = resize(self._adapter.circuit, n, confirmed=True)
            else:
                res = resize(self._adapter.circuit, n)
            if res.status == "applied":
                self._adapter.apply(res)
            elif res.status == "rejected":
                self._ui.show_error("Resize Error", "\n".join(res.messages))
                self._sync_qubit_spin()

    def _read_theme(self) -> Theme:
        try:
            return Theme(self._settings.value("appearance/theme", Theme.DARK.value))
        except ValueError:
            return Theme.DARK

    @property
    def theme(self) -> Theme:
        return self._theme

    def _open_preferences(self) -> None:
        dialog = PreferencesDialog(self._theme, self)
        if dialog.exec() == PreferencesDialog.DialogCode.Accepted:
            self._theme = dialog.selected_theme
            self._settings.setValue("appearance/theme", self._theme.value)
            self._settings.sync()
            app = QApplication.instance()
            if app is not None:
                apply_theme(app, self._theme)

    def _sync_qubit_spin(self) -> None:
        if hasattr(self, "_qubit_spin"):
            self._qubit_spin.blockSignals(True)
            self._qubit_spin.setValue(self._adapter.circuit.num_qubits)
            self._qubit_spin.blockSignals(False)

    def _on_session_changed(self) -> None:
        self._sync_qubit_spin()

        # Window title
        file_name = (
            self._adapter.file_path.name if self._adapter.file_path is not None else "Untitled"
        )
        self.setWindowTitle(f"{file_name} [*] - OpenQSim")
        self.setWindowModified(self._adapter.save_status == SaveStatus.DIRTY)

        # Save status indicator
        if self._adapter.save_status == SaveStatus.DIRTY:
            self._save_status_label.setText("Save: Dirty")
            self._save_status_label.setProperty("status", "dirty")
        else:
            self._save_status_label.setText("Save: Clean")
            self._save_status_label.setProperty("status", "clean")
        self._save_status_label.style().unpolish(self._save_status_label)
        self._save_status_label.style().polish(self._save_status_label)

        # Simulation status indicator
        sim_status = self._adapter.simulation_status
        if sim_status == SimulationStatus.STALE:
            self._sim_status_label.setText("Simulation: Stale")
            self._sim_status_label.setProperty("status", "stale")
        elif sim_status == SimulationStatus.CURRENT:
            self._sim_status_label.setText("Simulation: Current")
            self._sim_status_label.setProperty("status", "current")
        else:
            self._sim_status_label.setText("Simulation: None")
            self._sim_status_label.setProperty("status", "none")
        self._sim_status_label.style().unpolish(self._sim_status_label)
        self._sim_status_label.style().polish(self._sim_status_label)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event guarded by SaveStatus."""
        if self._adapter.save_status == SaveStatus.DIRTY:
            choice = self._ui.prompt_save_changes(
                "Unsaved Changes",
                "Save changes before closing OpenQSim?",
            )
            success = run_guarded(
                self._adapter.session,
                choice,
                self._commands.handle_save,
                lambda: None,
            )
            if success:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def export_circuit_image(self, path: Path | str | None = None) -> bool:
        """Export the currently revealed circuit canvas as a PNG image."""
        if path is None:
            chosen = self._ui.choose_save_file(
                "Export Circuit Diagram",
                "PNG Image (*.png);;All Files (*)",
                default_name="circuit.png",
            )
            if chosen is None:
                return False
            path = chosen
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            canvas_size = self._canvas.size()
            image = QImage(canvas_size, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            self._canvas.render(image)
            if not image.save(str(target), "PNG"):
                raise OSError(f"Failed to write image to {target}")
            return True
        except OSError as exc:
            self._ui.show_error("Export Error", f"Failed to export circuit image: {exc}")
            return False

    def export_bloch_image(self, path: Path | str | None = None) -> bool:
        """Export the Bloch sphere view as a PNG image."""
        if path is None:
            chosen = self._ui.choose_save_file(
                "Export Bloch View",
                "PNG Image (*.png);;All Files (*)",
                default_name="bloch.png",
            )
            if chosen is None:
                return False
            path = chosen
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            bloch_widget = self._results_panel._bloch_view
            layout = bloch_widget.layout()
            hint = layout.sizeHint() if layout is not None else bloch_widget.sizeHint()
            w = max(hint.width(), bloch_widget.width(), 320)
            h = max(hint.height(), bloch_widget.height(), 200)
            orig_size = bloch_widget.size()
            bloch_widget.resize(w, h)
            image = QImage(QSize(w, h), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            bloch_widget.render(image)
            bloch_widget.resize(orig_size)
            if not image.save(str(target), "PNG"):
                raise OSError(f"Failed to write image to {target}")
            return True
        except OSError as exc:
            self._ui.show_error("Export Error", f"Failed to export Bloch view image: {exc}")
            return False

    def export_histogram_image(self, path: Path | str | None = None) -> bool:
        """Export the histogram view as a PNG image."""
        if path is None:
            chosen = self._ui.choose_save_file(
                "Export Histogram View",
                "PNG Image (*.png);;All Files (*)",
                default_name="histogram.png",
            )
            if chosen is None:
                return False
            path = chosen
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            hist_widget = self._results_panel._histogram_view
            w = max(hist_widget.width(), 640)
            h = max(hist_widget.height(), 320)
            orig_size = hist_widget.size()
            hist_widget.resize(w, h)
            image = QImage(QSize(w, h), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            hist_widget.render(image)
            hist_widget.resize(orig_size)
            if not image.save(str(target), "PNG"):
                raise OSError(f"Failed to write image to {target}")
            return True
        except OSError as exc:
            self._ui.show_error("Export Error", f"Failed to export histogram image: {exc}")
            return False
