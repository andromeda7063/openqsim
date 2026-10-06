"""Tests for offline documentation, Help viewer, and offline security constraints."""

import ast
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.help import (
    DOC_MAPPING,
    HelpWindow,
    open_help_window,
    resolve_doc_path,
)
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.gate_palette import GATE_TOOLTIPS, GatePalette
from qsim_gui.widgets.results_panel import ResultsPanel


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-7.5")
def test_resolver_finds_all_docs() -> None:
    for key in DOC_MAPPING:
        doc_path = resolve_doc_path(key)
        assert doc_path.exists(), f"Document '{key}' at {doc_path} does not exist"
        assert doc_path.is_file()
        assert doc_path.stat().st_size > 0


@pytest.mark.req("FR-7.1", "FR-7.2", "FR-7.5")
def test_each_help_page_opens_and_contains_title(qapp: QApplication) -> None:
    pages = [
        ("quick-start", "Quick Start", "Quick Start"),
        ("qcs-format", "QCS Format", "QCS"),
        ("qasm-support", "OpenQASM Support", "OpenQASM"),
        ("about", "About", "About OpenQSim"),
    ]

    for key, menu_title, expected_text in pages:
        win: HelpWindow = open_help_window(key, menu_title)
        assert win.isVisible() or win.isWindow()
        # Verify QTextBrowser settings
        assert win.browser.openExternalLinks() is False
        assert win.browser.openLinks() is False
        assert win.browser.isReadOnly() is True

        text = win.browser.toPlainText()
        assert expected_text in text, f"Expected '{expected_text}' in page '{key}' text"
        win.close()


@pytest.mark.req("FR-7.1", "FR-7.5")
def test_main_window_help_menu_actions(qapp: QApplication) -> None:
    ui = StubUserInterface()
    window = MainWindow(ui=ui)

    assert hasattr(window, "action_help_quick_start")
    assert hasattr(window, "action_help_qcs")
    assert hasattr(window, "action_help_qasm")
    assert hasattr(window, "action_help_about")

    # Trigger each menu action
    window.action_help_quick_start.trigger()
    window.action_help_qcs.trigger()
    window.action_help_qasm.trigger()
    window.action_help_about.trigger()

    assert len(window.help_windows) == 4
    for hw in window.help_windows:
        assert isinstance(hw, HelpWindow)
        assert hw.browser.toPlainText()


@pytest.mark.req("FR-7.3", "FR-7.4", "FR-4.14")
def test_palette_and_results_explanations_exist(qapp: QApplication) -> None:
    palette = GatePalette()
    assert len(palette._buttons) == len(GATE_TOOLTIPS)
    for btn in palette._buttons:
        assert btn.toolTip(), f"Gate button '{btn.text()}' missing tooltip"
        assert len(btn.toolTip()) > 5

    from libqsim.application.session import EditorSession

    session = EditorSession()
    adapter = SessionAdapter(session)
    results = ResultsPanel(adapter=adapter)

    # Check stale banner and explanation labels
    assert results._stale_banner.text()
    assert hasattr(results, "_bloch_view")
    assert hasattr(results, "_histogram_view")
    # Verify explanation labels exist in children
    labels = [
        c.text() for c in results.findChildren(results.__class__.__bases__[0]) if hasattr(c, "text")
    ]
    text_blob = " ".join(labels)
    assert "Bloch" in text_blob
    assert "Histogram" in text_blob or "Probabilities" in text_blob


@pytest.mark.req("NFR-4.1")
def test_no_network_modules_imported() -> None:
    forbidden_modules = {
        "requests",
        "urllib",
        "urllib.request",
        "http",
        "http.client",
        "socket",
        "aiohttp",
        "httpx",
        "telemetry",
    }

    src_dirs = [
        Path(__file__).resolve().parents[2] / "src",  # qsim-gui/src
        Path(__file__).resolve().parents[3] / "libqsim" / "src",  # libqsim/src
    ]

    for src_dir in src_dirs:
        for py_file in src_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split(".")[0]
                        assert (
                            alias.name not in forbidden_modules and base not in forbidden_modules
                        ), f"Forbidden module '{alias.name}' imported in {py_file}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    base = node.module.split(".")[0]
                    assert node.module not in forbidden_modules and base not in forbidden_modules, (
                        f"Forbidden module '{node.module}' imported in {py_file}"
                    )
