"""Gate palette widget with draggable quantum gates."""

from libqsim.domain.models import GateType
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QWidget

GATE_MIME_TYPE = "application/x-openqsim-gate"


def encode_gate_mime(gate_type: GateType) -> QMimeData:
    raise NotImplementedError


def decode_gate_mime(mime_data: QMimeData) -> GateType | None:
    raise NotImplementedError


class GatePalette(QWidget):
    """Palette holding draggable gate buttons with tooltips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gate_palette")

    def items(self) -> list[tuple[GateType, str]]:
        raise NotImplementedError
