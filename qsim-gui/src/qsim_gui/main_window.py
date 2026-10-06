"""Main window of the OpenQSim application."""

from libqsim.application.operations import plan_resize, resize
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QToolBar,
    QWidget,
)

from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import QtUserInterface, UserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import GatePalette
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
        if adapter is None:
            adapter = SessionAdapter(EditorSession())
        self._adapter = adapter
        self._ui = ui if ui is not None else QtUserInterface(self)
        self._commands = CommandActions(self, self._adapter, self._ui)

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
        file_menu.addSeparator()
        file_menu.addAction(self._commands.action_import_qasm)
        file_menu.addAction(self._commands.action_export_qasm)
        file_menu.addAction(self._commands.action_export_image)

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

        # Simulate menu
        simulate_menu = menubar.addMenu("&Simulate")
        simulate_menu.addAction(self._commands.action_run)

        # Help menu placeholder
        self._help_menu: QMenu = menubar.addMenu("&Help")

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("main_toolbar")
        self.addToolBar(toolbar)

        toolbar.addAction(self._commands.action_new)
        toolbar.addAction(self._commands.action_open)
        toolbar.addAction(self._commands.action_save)
        toolbar.addAction(self._commands.action_save_as)
        toolbar.addSeparator()
        toolbar.addAction(self._commands.action_undo)
        toolbar.addAction(self._commands.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self._commands.action_run)
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

        self._canvas_scroll = QScrollArea(self)
        self._canvas_scroll.setObjectName("canvas_region")
        self._canvas_scroll.setWidget(self._canvas)
        self._canvas_scroll.setWidgetResizable(False)

        self._results_panel = ResultsPanel(adapter=self._adapter, parent=self)
        self._results_panel.setObjectName("results_region")

        layout.addWidget(self._palette, 1)
        layout.addWidget(self._canvas_scroll, 4)
        layout.addWidget(self._results_panel, 3)

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        status_bar.setObjectName("status_bar")
        self.setStatusBar(status_bar)

        self._save_status_label = QLabel("Save: Clean", self)
        self._save_status_label.setObjectName("save_status_label")

        self._sim_status_label = QLabel("Simulation: None", self)
        self._sim_status_label.setObjectName("sim_status_label")

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
            self._save_status_label.setStyleSheet(
                "color: #c96000; font-weight: bold; padding: 2px 6px;"
            )
        else:
            self._save_status_label.setText("Save: Clean")
            self._save_status_label.setStyleSheet("color: inherit; padding: 2px 6px;")

        # Simulation status indicator
        sim_status = self._adapter.simulation_status
        if sim_status == SimulationStatus.STALE:
            self._sim_status_label.setText("Simulation: Stale")
            self._sim_status_label.setStyleSheet(
                "color: #990000; font-weight: bold; background-color: #ffd6d6; "
                "border: 1px solid #cc0000; border-radius: 3px; padding: 2px 6px;"
            )
        elif sim_status == SimulationStatus.CURRENT:
            self._sim_status_label.setText("Simulation: Current")
            self._sim_status_label.setStyleSheet(
                "color: #007700; font-weight: bold; padding: 2px 6px;"
            )
        else:
            self._sim_status_label.setText("Simulation: None")
            self._sim_status_label.setStyleSheet("color: inherit; padding: 2px 6px;")
