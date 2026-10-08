import os
from collections.abc import Generator

import pytest
from libqsim.application.guarded import UserChoice
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.models import GateType
from libqsim.examples import list_examples
from PySide6.QtWidgets import QApplication
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


@pytest.mark.req("FR-5.19", "FR-5.20")
def test_examples_menu_lists_named_described_catalog(qapp: QApplication) -> None:
    window = MainWindow(adapter=SessionAdapter(EditorSession()), ui=StubUserInterface())
    assert list(window.example_actions) == [item.name for item in list_examples()]
    for item in list_examples():
        action = window.example_actions[item.name]
        assert action.toolTip() == item.description
        assert item.name in action.text() and item.description in action.text()


@pytest.mark.req("FR-5.20", "FR-5.21", "FR-5.22", "FR-5.23", "FR-5.24", "LC-18")
def test_load_example_uses_dirty_prompt_and_cancel_preserves_state(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)
    adapter.apply(place_gate(session.circuit, GateType.X, 0, 0))
    prior = session.circuit

    ui.save_prompt_choices = [UserChoice.CANCEL, UserChoice.DONT_SAVE]
    example = list_examples()[0]
    assert not window.commands.handle_load_example(example)
    assert session.circuit == prior and adapter.save_status is SaveStatus.DIRTY

    assert window.commands.handle_load_example(example)
    assert session.circuit == example.circuit
    assert session.file_path is None and session.baseline is None
    assert adapter.save_status is SaveStatus.DIRTY
    assert adapter.simulation_status is SimulationStatus.NONE
    assert not adapter.can_undo and not adapter.can_redo
    assert len(ui.save_prompts) == 2


@pytest.mark.req("FR-5.24", "FR-5.25", "LC-18")
def test_failed_save_aborts_example_load(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)
    adapter.apply(place_gate(session.circuit, GateType.X, 0, 0))
    prior = session.circuit
    ui.save_prompt_choices = [UserChoice.SAVE]
    ui.save_file_result = None

    assert not window.commands.handle_load_example(list_examples()[0])
    assert session.circuit == prior
    assert adapter.save_status is SaveStatus.DIRTY
    assert adapter.can_undo
