"""Scrollable read-only circuit canvas widget."""

from PySide6.QtWidgets import QWidget
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.grid import GridGeometry


class CircuitCanvas(QWidget):
    """Widget rendering quantum circuit with QPainter."""

    def __init__(
        self,
        adapter: SessionAdapter,
        geometry: GridGeometry | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._geo = geometry if geometry is not None else GridGeometry()

    @property
    def grid_geometry(self) -> GridGeometry:
        return self._geo
