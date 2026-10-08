"""Tests for persisted theme preferences and flat application appearance."""

import os
from collections.abc import Generator

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QDialog
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.preferences import PreferencesDialog
from qsim_gui.theme import Theme, apply_theme


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    settings = QSettings("OpenQSim", "OpenQSim")
    settings.clear()
    settings.sync()
    yield app  # type: ignore[misc]
    settings.clear()
    settings.sync()


@pytest.mark.req("FR-7.10")
def test_both_themes_use_dark_palette_and_distinct_accents(qapp: QApplication) -> None:
    apply_theme(qapp, Theme.DARK)
    assert qapp.palette().color(QPalette.ColorRole.Base).name() == "#101217"
    assert "#58a6ff" in qapp.styleSheet()

    apply_theme(qapp, Theme.DARK_PURPLE)
    assert qapp.palette().color(QPalette.ColorRole.Base).name() == "#101217"
    assert "#a78bfa" in qapp.styleSheet()


@pytest.mark.req("FR-7.9", "FR-7.10")
def test_preferences_lists_themes_and_saves_selected_theme(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(ui=StubUserInterface())
    assert window.theme == Theme.DARK

    def accept_with_purple(dialog: PreferencesDialog) -> QDialog.DialogCode:
        dialog.theme_picker.setCurrentText(Theme.DARK_PURPLE.value)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(PreferencesDialog, "exec", accept_with_purple)
    window.action_preferences.trigger()

    assert window.theme == Theme.DARK_PURPLE
    assert window._settings.value("appearance/theme") == Theme.DARK_PURPLE.value
    assert "#a78bfa" in qapp.styleSheet()

    reopened = MainWindow(ui=StubUserInterface())
    assert reopened.theme == Theme.DARK_PURPLE


@pytest.mark.req("FR-7.9")
def test_preferences_cancel_does_not_change_theme(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(ui=StubUserInterface())
    assert window.theme == Theme.DARK

    def reject_preferences(dialog: PreferencesDialog) -> QDialog.DialogCode:
        assert [dialog.theme_picker.itemText(i) for i in range(dialog.theme_picker.count())] == [
            Theme.DARK.value,
            Theme.DARK_PURPLE.value,
        ]
        dialog.theme_picker.setCurrentText(Theme.DARK_PURPLE.value)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(PreferencesDialog, "exec", reject_preferences)
    window.action_preferences.trigger()

    assert window.theme == Theme.DARK
    assert window._settings.value("appearance/theme") is None
