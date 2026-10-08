"""Independently rotatable wireframe Bloch spheres."""

import math
from itertools import pairwise

from libqsim.simulation.results import SimulationSnapshot
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPalette, QPen
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget
from qsim_gui.widgets.projection import BlochProjection

DEFAULT_YAW = math.radians(130.0)
DEFAULT_ELEVATION = math.radians(25.0)


class BlochSphereWidget(QWidget):
    """One qubit's Bloch vector and independent camera orientation."""

    def __init__(
        self,
        qubit: int,
        vector: tuple[float, float, float],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.qubit = qubit
        self.vector = vector
        self.yaw = DEFAULT_YAW
        self.elevation = DEFAULT_ELEVATION
        self._drag_pos: QPointF | None = None
        self.setFixedSize(176, 218)
        self._reset_button = QPushButton("Reset View", self)
        self._reset_button.setObjectName("reset_view_button")
        self._reset_button.setGeometry(31, 187, 114, 25)
        self._reset_button.clicked.connect(self.reset_view)
        self.set_vector(vector)

    def set_vector(self, vector: tuple[float, float, float]) -> None:
        self.vector = vector
        self.setToolTip(
            f"q{self.qubit}\n"
            f"x = {vector[0]:.4f}\n"
            f"y = {vector[1]:.4f}\n"
            f"z = {vector[2]:.4f}\n"
            f"|r| = {math.sqrt(sum(v**2 for v in vector)):.4f}"
        )
        self.update()

    def reset_view(self) -> None:
        self.yaw = DEFAULT_YAW
        self.elevation = DEFAULT_ELEVATION
        self.update()

    def _projection(self) -> BlochProjection:
        return BlochProjection(88.0, 93.0, 50.0, self.yaw, self.elevation)

    def _inside_sphere(self, pos: QPointF) -> bool:
        return (pos.x() - 88.0) ** 2 + (pos.y() - 93.0) ** 2 <= 50.0**2

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._inside_sphere(event.position()):
            self._drag_pos = event.position()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self._drag_pos
            self.yaw += delta.x() * 0.012
            self.elevation = max(-1.48, min(1.48, self.elevation + delta.y() * 0.012))
            self._drag_pos = event.position()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._drag_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        background = pal.color(QPalette.ColorRole.Base)
        text_color = pal.color(QPalette.ColorRole.WindowText)
        wire_color = QColor(text_color)
        wire_color.setAlpha(125)
        vector_color = pal.color(QPalette.ColorRole.Highlight)
        painter.fillRect(self.rect(), background)

        title_font = QFont(self.font())
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(text_color)
        painter.drawText(QRectF(0, 3, 176, 20), Qt.AlignmentFlag.AlignCenter, f"q{self.qubit}")

        proj = self._projection()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Latitude and longitude circles are segmented by depth. Rear segments
        # are dashed; front segments are solid at every camera angle.
        curves: list[list[tuple[float, float, float]]] = []
        for z in (0.0,):
            r = math.sqrt(1.0 - z * z)
            curves.append(
                [
                    (r * math.cos(t), r * math.sin(t), z)
                    for t in (2 * math.pi * i / 96 for i in range(97))
                ]
            )
        for azimuth in (0.0, math.pi / 2.0):
            curves.append(
                [
                    (
                        math.sin(t) * math.cos(azimuth),
                        math.sin(t) * math.sin(azimuth),
                        math.cos(t),
                    )
                    for t in (2 * math.pi * i / 96 for i in range(97))
                ]
            )
        for curve in curves:
            for a, b in pairwise(curve):
                depth = (proj.view_coordinates(*a)[2] + proj.view_coordinates(*b)[2]) / 2.0
                style = Qt.PenStyle.SolidLine if depth >= 0 else Qt.PenStyle.DashLine
                painter.setPen(QPen(wire_color, 1.0, style))
                painter.drawLine(QPointF(*proj.project(*a)), QPointF(*proj.project(*b)))

        painter.setPen(QPen(wire_color, 1.25))
        painter.drawEllipse(QPointF(88, 93), 50, 50)

        labels = (("+X", (1.0, 0.0, 0.0)), ("+Y", (0.0, 1.0, 0.0)), ("+Z", (0.0, 0.0, 1.0)))
        for _, axis in labels:
            negative = tuple(-v for v in axis)
            for endpoint in (negative, axis):
                style = (
                    Qt.PenStyle.SolidLine
                    if proj.view_coordinates(*endpoint)[2] >= 0
                    else Qt.PenStyle.DashLine
                )
                painter.setPen(QPen(text_color, 1.1, style))
                painter.drawLine(QPointF(88, 93), QPointF(*proj.project(*endpoint)))

        label_font = QFont(self.font())
        label_font.setPointSize(max(9, label_font.pointSize() - 1))
        painter.setFont(label_font)
        painter.setPen(text_color)
        for label, axis in labels:
            px, py = proj.project(*axis)
            length = max(1.0, math.hypot(px - 88.0, py - 93.0))
            px += 13.0 * (px - 88.0) / length
            py += 13.0 * (py - 93.0) / length
            rect = QRectF(max(2.0, min(150.0, px - 12.0)), max(24.0, min(143.0, py - 8.0)), 24, 16)
            painter.fillRect(rect, background)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        vx, vy = proj.project(*self.vector)
        painter.setPen(QPen(vector_color, 3.0))
        painter.drawLine(QPointF(88, 93), QPointF(vx, vy))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(vector_color)
        painter.drawEllipse(QPointF(vx, vy), 4.0, 4.0)

        painter.setFont(self.font())
        painter.setPen(text_color)
        x, y, z = self.vector
        painter.drawText(
            QRectF(0, 158, 176, 19),
            Qt.AlignmentFlag.AlignCenter,
            f"({x:+.3f}, {y:+.3f}, {z:+.3f})",
        )

    def sizeHint(self) -> QSize:
        return QSize(176, 218)


class BlochView(QWidget):
    """Grid of Bloch spheres; snapshot updates retain their view angles."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bloch_view")
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setSpacing(6)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._spheres: list[BlochSphereWidget] = []

    def set_simulation_result(self, result: SimulationSnapshot | None) -> None:
        if result is None or len(result.bloch_vectors) != len(self._spheres):
            for sphere in self._spheres:
                self._grid.removeWidget(sphere)
                sphere.deleteLater()
            self._spheres.clear()
        if result is None:
            return

        cols = 2 if len(result.bloch_vectors) > 4 else len(result.bloch_vectors)
        cols = max(1, min(cols, 5))
        for idx, vec in enumerate(result.bloch_vectors):
            if idx < len(self._spheres):
                self._spheres[idx].set_vector(vec)
                continue
            widget = BlochSphereWidget(qubit=idx, vector=vec, parent=self)
            self._spheres.append(widget)
            self._grid.addWidget(widget, idx // cols, idx % cols)
            widget.show()
        self._grid.activate()
