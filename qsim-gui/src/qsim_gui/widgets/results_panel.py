"""Results panel integrating Bloch sphere view, histogram view, and stale indicator."""

from PySide6.QtWidgets import QWidget
from qsim_gui.state import SessionAdapter


class ResultsPanel(QWidget):
    """Panel containing Bloch spheres, histogram, explanatory text, and stale banner."""

    def __init__(self, adapter: SessionAdapter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._adapter = adapter
