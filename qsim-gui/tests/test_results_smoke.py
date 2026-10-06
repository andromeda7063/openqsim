"""Smoke and integration tests for results panel, Bloch spheres, and histogram."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SimulationStatus
from libqsim.domain.models import GateType
from PySide6.QtWidgets import QApplication, QLabel
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.bloch_view import BlochSphereWidget, BlochView
from qsim_gui.widgets.histogram_view import HistogramView
from qsim_gui.widgets.results_panel import ResultsPanel


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-4.1", "FR-4.2", "FR-4.6", "FR-4.7", "FR-4.10", "FR-4.14", "NFR-1.1", "NFR-6.2")
def test_bell_state_run_results_panel(qapp: QApplication) -> None:
    session = EditorSession()
    # Bell state: H on 0, CNOT with control 0, target 1
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))

    adapter = SessionAdapter(session)
    panel = ResultsPanel(adapter=adapter)
    panel.show()

    # Before run: empty state label visible
    empty_label = panel.findChild(QLabel, "empty_state_label")
    assert empty_label is not None
    assert not empty_label.isHidden()

    # Run simulation
    outcome = adapter.run()
    assert outcome.ok is True
    assert adapter.simulation_status == SimulationStatus.CURRENT

    # After run: 2 spheres and histogram with 4 bars
    bloch_view = panel.findChild(BlochView)
    assert bloch_view is not None
    spheres = bloch_view.findChildren(BlochSphereWidget)
    assert len(spheres) == 2

    # Spheres titled "q0" and "q1"
    titles = [s.qubit for s in spheres]
    assert sorted(titles) == [0, 1]

    hist_view = panel.findChild(HistogramView)
    assert hist_view is not None
    assert hist_view.bar_count == 4

    # Explanatory text exists
    assert len(panel.findChildren(QLabel, "explanation_label")) >= 2


@pytest.mark.req("FR-3.8", "FR-4.10")
def test_stale_banner_appears_after_mutation(qapp: QApplication) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter = SessionAdapter(session)
    panel = ResultsPanel(adapter=adapter)
    panel.show()

    adapter.run()
    stale_banner = panel.findChild(QLabel, "stale_banner")
    assert stale_banner is not None
    assert stale_banner.isHidden() is True

    # Mutate circuit
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=1, column=1))
    assert adapter.simulation_status == SimulationStatus.STALE
    assert stale_banner.isHidden() is False
    assert "Results are out of date" in stale_banner.text()


@pytest.mark.req("FR-3.12")
def test_failing_run_preserves_previous_result_and_status(qapp: QApplication) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Initial successful run
    window.commands.action_run.trigger()
    assert adapter.simulation_status == SimulationStatus.CURRENT
    prev_result = adapter.simulation_result
    assert prev_result is not None

    # Mutate to make stale
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=1, column=1))
    assert adapter.simulation_status == SimulationStatus.STALE

    # Inject failure
    def failing_sim(circuit):
        from libqsim.simulation.engine import SimulationError

        raise SimulationError("Forced kernel error")

    outcome = session.run(simulate_fn=failing_sim)
    assert outcome.ok is False

    # Verify session retains previous result and stays STALE
    assert adapter.simulation_result is prev_result
    assert adapter.simulation_status == SimulationStatus.STALE
