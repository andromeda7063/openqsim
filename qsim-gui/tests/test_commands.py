"""Tests for CommandActions and shortcut bindings."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QWidget
from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.31")
def test_undo_action_shortcut_and_lifecycle(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_undo.shortcut().matches(QKeySequence("Ctrl+Z"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_undo.isEnabled() is False

    # Apply a mutation
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert commands.action_undo.isEnabled() is True

    # Trigger undo
    commands.action_undo.trigger()
    assert len(adapter.circuit.placements) == 0
    assert commands.action_undo.isEnabled() is False


@pytest.mark.req("FR-1.32")
def test_redo_action_shortcut_and_lifecycle(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_redo.shortcut().matches(QKeySequence("Ctrl+Y"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_redo.isEnabled() is False

    # Apply mutation and undo
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.undo()
    assert commands.action_redo.isEnabled() is True

    # Trigger redo
    commands.action_redo.trigger()
    assert len(adapter.circuit.placements) == 1
    assert commands.action_redo.isEnabled() is False


@pytest.mark.req("FR-1.33")
def test_copy_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_copy.shortcut().matches(QKeySequence("Ctrl+C"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_copy.isEnabled() is False


@pytest.mark.req("FR-1.34")
def test_paste_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_paste.shortcut().matches(QKeySequence("Ctrl+V"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_paste.isEnabled() is False


@pytest.mark.req("FR-1.35")
def test_delete_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    shortcuts = commands.action_delete.shortcuts()
    assert any(
        s.matches(QKeySequence("Delete")) == QKeySequence.SequenceMatch.ExactMatch
        for s in shortcuts
    )
    assert any(
        s.matches(QKeySequence("Backspace")) == QKeySequence.SequenceMatch.ExactMatch
        for s in shortcuts
    )
    assert commands.action_delete.isEnabled() is False


@pytest.mark.req("FR-1.36")
def test_select_all_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_select_all.shortcut().matches(QKeySequence("Ctrl+A"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_select_all.isEnabled() is False


@pytest.mark.req("FR-1.39")
def test_save_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_save.shortcut().matches(QKeySequence("Ctrl+S"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_save.isEnabled() is False


@pytest.mark.req("FR-1.40")
def test_open_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_open.shortcut().matches(QKeySequence("Ctrl+O"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_open.isEnabled() is False


@pytest.mark.req("FR-1.41")
def test_new_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_new.shortcut().matches(QKeySequence("Ctrl+N"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_new.isEnabled() is False


@pytest.mark.req("FR-1.42")
def test_save_as_action_shortcut_and_disabled(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_save_as.shortcut().matches(QKeySequence("Ctrl+Shift+S"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_save_as.isEnabled() is False


@pytest.mark.req("FR-1.43")
def test_export_qasm_and_export_image_shortcuts(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    widget = QWidget()
    commands = CommandActions(widget, adapter, ui)

    assert (
        commands.action_export_qasm.shortcut().matches(QKeySequence("Ctrl+E"))
        == QKeySequence.SequenceMatch.ExactMatch
    )
    assert commands.action_export_qasm.isEnabled() is False
    assert commands.action_export_image.shortcut().isEmpty()
    assert commands.action_export_image.isEnabled() is False
