"""Bloch sphere visualization view."""

from libqsim.simulation.results import SimulationResult
from PySide6.QtWidgets import QWidget


class BlochSphereWidget(QWidget):
    """Single qubit Bloch sphere drawing."""

    def __init__(
        self,
        qubit: int,
        vector: tuple[float, float, float],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.qubit = qubit
        self.vector = vector


class BlochView(QWidget):
    """Grid container holding Bloch sphere widgets for all circuit qubits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def set_simulation_result(self, result: SimulationResult | None) -> None:
        pass
