"""Smoke and integration tests for MainWindow shell and offscreen GUI."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SimulationStatus
from libqsim.domain.models import GateType
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSplitter, QWidget
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("NFR-2.3", "NFR-6.4", "FR-7.7")
def test_main_window_construction_and_regions(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    assert window.windowTitle() == "Untitled [*] - OpenQSim"
    assert window.isWindowModified() is False

    # Check 3 regions exist in central widget
    palette_region = window.findChild(QWidget, "palette_region")
    canvas_region = window.findChild(QWidget, "canvas_region")
    results_region = window.findChild(QWidget, "results_region")

    assert palette_region is not None
    assert canvas_region is not None
    assert results_region is not None

    main_splitter = window.findChild(QSplitter, "main_splitter")
    workspace_splitter = window.findChild(QSplitter, "workspace_splitter")
    assert main_splitter is not None
    assert workspace_splitter is not None
    assert main_splitter.orientation() == Qt.Orientation.Vertical
    assert main_splitter.widget(0) is workspace_splitter
    assert main_splitter.widget(1) is results_region
    assert isinstance(window.results_panel._content_widget.layout(), QHBoxLayout)
    assert window.results_panel._bloch_view is not None
    assert window.results_panel._histogram_view is not None
    assert adapter.run().ok
    window.show()
    qapp.processEvents()
    assert results_region.height() >= 350
    assert window.results_panel._histogram_view.height() >= 220


@pytest.mark.req("FR-3.8")
def test_status_bar_indicators_and_stale_style(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    save_label = window.findChild(QLabel, "save_status_label")
    sim_label = window.findChild(QLabel, "sim_status_label")
    assert save_label is not None
    assert sim_label is not None

    # Initial clean state
    assert save_label.text() == "Save: Clean"
    assert sim_label.text() == "Simulation: None"

    # Run on clean empty circuit
    window.commands.action_run.trigger()
    assert sim_label.text() == "Simulation: Current"
    assert adapter.simulation_status == SimulationStatus.CURRENT

    # Mutate circuit to make simulation Stale and Save Dirty
    res = place_gate(session.circuit, GateType.H, qubit=0, column=0)
    adapter.apply(res)

    assert save_label.text() == "Save: Dirty"
    assert window.isWindowModified() is True
    assert sim_label.text() == "Simulation: Stale"
    assert adapter.simulation_status == SimulationStatus.STALE

    # Distinct "out of date" style must be applied
    assert sim_label.property("status") == "stale"
    assert 'QLabel#sim_status_label[status="stale"]' in qapp.styleSheet()


@pytest.mark.req("NFR-2.2")
def test_run_failure_invokes_error_dialog(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # First run successfully
    window.commands.action_run.trigger()
    assert adapter.simulation_status == SimulationStatus.CURRENT
    sim_result_before = adapter.simulation_result

    # Inject simulated failure
    def failing_simulate(circuit):
        from libqsim.simulation.engine import SimulationError

        raise SimulationError("Simulated quantum kernel failure")

    # Run failing simulation via adapter
    outcome = adapter.run(simulate_fn=failing_simulate)
    assert outcome.ok is False

    # If triggered via action with failure
    outcome_run = session.run(simulate_fn=failing_simulate)
    assert outcome_run.ok is False

    # Simulate triggering via action with failing simulate
    adapter._session.run = lambda simulate_fn=None, *, step_mode=False: outcome_run  # type: ignore[assignment]
    window.commands.action_run.trigger()

    assert len(ui.errors) == 1
    title, msg = ui.errors[0]
    assert title == "Simulation Error"
    assert "Simulated quantum kernel failure" in msg
    assert "Traceback" not in msg

    # Prior result and status remain unchanged
    assert adapter.simulation_result is sim_result_before
    assert adapter.simulation_status == SimulationStatus.CURRENT
