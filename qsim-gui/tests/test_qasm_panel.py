"""Tests for the v1.1 embedded OpenQASM editor integration."""

import os
from collections.abc import Generator

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtWidgets import QApplication
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.qasm_panel import QasmPanel


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-7.8")
def test_qasm_panel_shows_export_and_tracks_circuit_changes(qapp: QApplication) -> None:
    adapter = SessionAdapter(EditorSession())
    panel = QasmPanel(adapter, lambda _source: True)
    assert panel.editor.toPlainText().startswith('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];')

    result = place_gate(adapter.circuit, GateType.H, qubit=1, column=0)
    adapter.apply(result)
    assert "h q[1];" in panel.editor.toPlainText()
    assert panel.apply_button.isEnabled()


@pytest.mark.req("FR-7.8", "FR-6.11")
def test_qasm_panel_reports_invalid_syntax_and_unsupported_subset(qapp: QApplication) -> None:
    panel = QasmPanel(SessionAdapter(EditorSession()), lambda _source: True)

    panel.editor.setPlainText('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2]\nh q[0];\n')
    assert "Syntax error" in panel.status.text()
    assert not panel.apply_button.isEnabled()

    panel.editor.setPlainText('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nsdg q[0];\n')
    assert "unsupported or invalid" in panel.status.text()
    assert not panel.apply_button.isEnabled()


@pytest.mark.req("FR-7.8")
def test_qasm_panel_applies_valid_program_only_on_button_click(qapp: QApplication) -> None:
    applied: list[str] = []
    panel = QasmPanel(
        SessionAdapter(EditorSession()), lambda source: applied.append(source) or True
    )
    source = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nx q[0];\n'
    panel.editor.setPlainText(source)

    assert panel.apply_button.isEnabled()
    assert applied == []
    panel.apply_button.click()
    assert applied == [source]
