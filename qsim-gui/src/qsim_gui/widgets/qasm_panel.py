"""Live OpenQASM editor with syntax and supported-subset feedback."""

from collections.abc import Callable

from libqsim.qasm.exporter import export_text
from libqsim.qasm.importer import QasmError, import_text
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
from qiskit import qasm2
from qiskit.qasm2 import QASM2Error
from qsim_gui.state import SessionAdapter


class QasmPanel(QWidget):
    """Display the circuit as OpenQASM and apply valid edited programs."""

    def __init__(
        self,
        adapter: SessionAdapter,
        on_apply: Callable[[str], bool],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("qasm_region")
        self._adapter = adapter
        self._on_apply = on_apply
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("OpenQASM 2.0", self)
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("qasm_editor")
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(" "))
        self.editor.textChanged.connect(self._validate_text)
        layout.addWidget(self.editor, 1)

        self.status = QLabel(self)
        self.status.setObjectName("qasm_status")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(34)
        layout.addWidget(self.status)

        self.apply_button = QPushButton("Apply to Circuit", self)
        self.apply_button.setObjectName("apply_qasm_button")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply_text)
        layout.addWidget(self.apply_button)

        self._adapter.changed.connect(self._sync_from_circuit)
        self._sync_from_circuit()

    def _sync_from_circuit(self) -> None:
        self._updating = True
        self.editor.setPlainText(export_text(self._adapter.circuit))
        self._updating = False
        self._validate_text()

    def _validate_text(self) -> None:
        if self._updating:
            return
        source = self.editor.toPlainText()
        if not source.strip():
            self.status.setText("Enter OpenQASM 2.0 to check it.")
            self.status.setStyleSheet("color: #666;")
            self.apply_button.setEnabled(False)
            return
        try:
            qasm2.loads(source, strict=True)
        except QASM2Error as exc:
            self.status.setText(f"Syntax error: {exc}")
            self.status.setStyleSheet("color: #990000;")
            self.apply_button.setEnabled(False)
            return

        try:
            import_text(source)
        except QasmError as exc:
            self.status.setText(f"Syntax valid; unsupported or invalid OpenQSim program: {exc}")
            self.status.setStyleSheet("color: #9a6500;")
            self.apply_button.setEnabled(False)
            return

        self.status.setText("OpenQASM syntax and supported subset are valid.")
        self.status.setStyleSheet("color: #007700;")
        self.apply_button.setEnabled(True)

    def _apply_text(self) -> None:
        self._on_apply(self.editor.toPlainText())
