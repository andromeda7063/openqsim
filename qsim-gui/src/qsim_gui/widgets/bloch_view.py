"""Bloch sphere visualization view."""

import math

from libqsim.simulation.results import SimulationResult
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QWidget,
)
from qsim_gui.widgets.projection import BlochProjection


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
        self.setFixedSize(160, 180)
        self.setToolTip(
            f"q{self.qubit}\n"
            f"x = {self.vector[0]:.4f}\n"
            f"y = {self.vector[1]:.4f}\n"
            f"z = {self.vector[2]:.4f}\n"
            f"|r| = {math.sqrt(sum(v**2 for v in self.vector)):.4f}"
        )

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Base)
        window_text = pal.color(QPalette.ColorRole.WindowText)
        mid_color = pal.color(QPalette.ColorRole.Mid)
        highlight = pal.color(QPalette.ColorRole.Highlight)

        painter.fillRect(self.rect(), bg)

        # Title at the top: "q0", "q1", ...
        title_font = QFont(self.font())
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(window_text)
        painter.drawText(
            QRectF(0, 4, self.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            f"q{self.qubit}",
        )

        # Sphere geometry
        cx = self.width() / 2.0
        cy = (self.height() + 15) / 2.0
        radius = min(48.0, (min(self.width(), self.height() - 25)) / 2.0 - 12.0)
        proj = BlochProjection(center_x=cx, center_y=cy, radius=radius)

        # 1. Sphere outline circle
        sphere_pen = QPen(mid_color, 1.2)
        painter.setPen(sphere_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # 2. Equator ellipse (XY plane)
        equator_pen = QPen(mid_color, 1.0, Qt.PenStyle.DashLine)
        painter.setPen(equator_pen)
        painter.drawEllipse(QPointF(cx, cy), radius, radius * 0.35)

        # 3. Axes
        axis_pen = QPen(mid_color, 1.0)
        painter.setPen(axis_pen)

        # Z axis
        z_pos = proj.project(0.0, 0.0, 1.0)
        z_neg = proj.project(0.0, 0.0, -1.0)
        painter.drawLine(QPointF(*z_neg), QPointF(*z_pos))

        # X axis
        x_pos = proj.project(1.0, 0.0, 0.0)
        x_neg = proj.project(-1.0, 0.0, 0.0)
        painter.drawLine(QPointF(*x_neg), QPointF(*x_pos))

        # Y axis
        y_pos = proj.project(0.0, 1.0, 0.0)
        y_neg = proj.project(-1.0, 0.0, 0.0)
        painter.drawLine(QPointF(*y_neg), QPointF(*y_pos))

        # Axis labels
        label_font = QFont(self.font())
        label_font.setPointSize(max(7, label_font.pointSize() - 3))
        painter.setFont(label_font)
        painter.setPen(mid_color)
        painter.drawText(
            QRectF(z_pos[0] - 10, z_pos[1] - 12, 20, 12), Qt.AlignmentFlag.AlignCenter, "+Z"
        )
        painter.drawText(
            QRectF(x_pos[0] - 12, x_pos[1] + 2, 20, 12), Qt.AlignmentFlag.AlignCenter, "+X"
        )
        painter.drawText(
            QRectF(y_pos[0] + 2, y_pos[1] - 6, 20, 12), Qt.AlignmentFlag.AlignCenter, "+Y"
        )

        # 4. Bloch vector
        vx, vy = proj.project(*self.vector)
        vector_pen = QPen(highlight, 2.0)
        painter.setPen(vector_pen)
        painter.drawLine(QPointF(cx, cy), QPointF(vx, vy))

        # Endpoint dot
        dot_radius = 4.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(highlight)
        painter.drawEllipse(QPointF(vx, vy), dot_radius, dot_radius)

    def sizeHint(self) -> QSize:
        return QSize(160, 180)


class BlochView(QWidget):
    """Grid container holding Bloch sphere widgets for all circuit qubits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bloch_view")

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setSpacing(6)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._spheres: list[BlochSphereWidget] = []

    def set_simulation_result(self, result: SimulationResult | None) -> None:
        # Clear existing spheres
        for sphere in self._spheres:
            self._grid.removeWidget(sphere)
            sphere.deleteLater()
        self._spheres.clear()

        if result is None:
            return

        cols = 2 if len(result.bloch_vectors) > 4 else len(result.bloch_vectors)
        cols = max(1, min(cols, 5))

        for idx, vec in enumerate(result.bloch_vectors):
            widget = BlochSphereWidget(qubit=idx, vector=vec, parent=self)
            widget.show()
            self._spheres.append(widget)
            row = idx // cols
            col = idx % cols
            self._grid.addWidget(widget, row, col)
        self._grid.activate()
