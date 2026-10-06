"""Gate palette widget with draggable quantum gates."""

from libqsim.domain.models import GateType
from PySide6.QtCore import QByteArray, QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

GATE_MIME_TYPE = "application/x-openqsim-gate"

GATE_TOOLTIPS: dict[GateType, str] = {
    GateType.H: "Hadamard gate: creates equal superposition state (|0⟩ -> (|0⟩+|1⟩)/√2)",
    GateType.X: "Pauli-X gate: bit flip (|0⟩ <-> |1⟩)",
    GateType.Y: "Pauli-Y gate: bit and phase flip (|0⟩ -> i|1⟩, |1⟩ -> -i|0⟩)",
    GateType.Z: "Pauli-Z gate: phase flip (|1⟩ -> -|1⟩)",
    GateType.S: "Phase gate: π/2 phase rotation (S = √Z)",
    GateType.T: "π/8 gate: π/4 phase rotation (T = √S)",
    GateType.CNOT: "Controlled-NOT gate: flips target qubit when control is |1⟩",
    GateType.Toffoli: "Controlled-Controlled-NOT gate: flips target when both controls are |1⟩",
    GateType.Measurement: "Measurement marker: visual readout of qubit wire (ignored in statevector simulation)",
}


def encode_gate_mime(gate_type: GateType) -> QMimeData:
    """Encode GateType into custom QMimeData payload."""
    mime = QMimeData()
    mime.setData(GATE_MIME_TYPE, QByteArray(gate_type.value.encode("utf-8")))
    return mime


def decode_gate_mime(mime_data: QMimeData) -> GateType | None:
    """Decode GateType from custom QMimeData payload or None if invalid."""
    if not mime_data.hasFormat(GATE_MIME_TYPE):
        return None
    raw = bytes(mime_data.data(GATE_MIME_TYPE)).decode("utf-8")
    try:
        return GateType(raw)
    except ValueError:
        return None


class DraggableGateButton(QPushButton):
    """Button representing a gate in the palette that can be dragged onto the canvas."""

    def __init__(self, gate_type: GateType, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(gate_type.value, parent)
        self.gate_type = gate_type
        self.setToolTip(tooltip)
        self.setMinimumHeight(38)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        font = QFont(self.font())
        font.setBold(True)
        self.setFont(font)
        self._drag_start_pos: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance >= QApplication.startDragDistance():
            drag = QDrag(self)
            mime = encode_gate_mime(self.gate_type)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
            self._drag_start_pos = None


class GatePalette(QWidget):
    """Palette holding draggable gate buttons with tooltips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gate_palette")
        self._buttons: list[DraggableGateButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("Gates", self)
        title_font = QFont(self.font())
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        for gate_type, tooltip in self.items():
            btn = DraggableGateButton(gate_type, tooltip, self)
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

    def items(self) -> list[tuple[GateType, str]]:
        """Return list of (GateType, tooltip) for all 9 supported gates."""
        return [(gt, GATE_TOOLTIPS[gt]) for gt in GATE_TOOLTIPS]
