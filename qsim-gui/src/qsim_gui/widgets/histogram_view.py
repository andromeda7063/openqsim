"""Pure layout calculation and widget for computational basis probability histogram."""

import math
from dataclasses import dataclass

from libqsim.simulation.results import SimulationSnapshot
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QMouseEvent, QPainter, QPalette, QPen
from PySide6.QtWidgets import QToolTip, QWidget


@dataclass(frozen=True)
class BarLayout:
    index: int
    label: str
    probability: float
    x: float
    y: float
    width: float
    height: float
    show_label: bool


def compute_histogram_layout(
    probabilities: list[float],
    width: float,
    height: float,
    margin_left: float = 40.0,
    margin_right: float = 20.0,
    margin_top: float = 20.0,
    margin_bottom: float = 35.0,
    min_label_width: float = 26.0,
) -> list[BarLayout]:
    """Calculate 2D bar layout positions for probability histogram."""
    num_states = len(probabilities)
    if num_states == 0:
        return []

    n = max(1, round(math.log2(num_states)))
    labels = [format(i, f"0{n}b") for i in range(num_states)]

    plot_width = max(1.0, width - margin_left - margin_right)
    plot_height = max(1.0, height - margin_top - margin_bottom)

    step = plot_width / num_states
    bar_width = max(1.0, step * 0.8)
    gap = step * 0.2

    show_label = bar_width >= min_label_width

    layouts: list[BarLayout] = []
    for i in range(num_states):
        prob = max(0.0, min(1.0, float(probabilities[i])))
        bar_h = plot_height * prob
        bx = margin_left + i * step + gap / 2.0
        by = margin_top + plot_height - bar_h

        layouts.append(
            BarLayout(
                index=i,
                label=labels[i],
                probability=prob,
                x=bx,
                y=by,
                width=bar_width,
                height=bar_h,
                show_label=show_label,
            )
        )
    return layouts


class HistogramView(QWidget):
    """Widget displaying computational-basis state probability histogram with hover tooltips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("histogram_view")
        self.setMouseTracking(True)
        self.setMinimumSize(320, 220)

        self._result: SimulationSnapshot | None = None
        self._bars: list[BarLayout] = []

    @property
    def bar_count(self) -> int:
        return len(self._bars)

    def set_result(self, result: SimulationSnapshot | None) -> None:
        self._result = result
        self._recompute_layout()
        self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._recompute_layout()

    def _recompute_layout(self) -> None:
        if self._result is None or len(self._result.probabilities) == 0:
            self._bars = []
            return
        probs = [float(p) for p in self._result.probabilities]
        self._bars = compute_histogram_layout(probs, width=self.width(), height=self.height())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        for bar in self._bars:
            rect = QRectF(bar.x, bar.y, bar.width, bar.height)
            # Expand hover hit area to include entire column strip
            col_rect = QRectF(bar.x, 20.0, bar.width, self.height() - 55.0)
            if rect.contains(pos) or col_rect.contains(pos):
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"|{bar.label}⟩: {bar.probability:.4f}",
                    self,
                )
                return
        QToolTip.hideText()
        super().mouseMoveEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Base)
        text_color = pal.color(QPalette.ColorRole.WindowText)
        mid_color = pal.color(QPalette.ColorRole.Mid)
        bar_fill = pal.color(QPalette.ColorRole.Highlight)

        painter.fillRect(self.rect(), bg)

        if not self._bars:
            painter.setPen(mid_color)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No simulation data",
            )
            return

        margin_left = 40.0
        margin_bottom = 35.0
        plot_bottom = self.height() - margin_bottom
        plot_top = 20.0
        plot_right = self.width() - 20.0

        # Draw axes
        axis_pen = QPen(mid_color, 1.0)
        painter.setPen(axis_pen)
        # Baseline (X-axis)
        painter.drawLine(margin_left, plot_bottom, plot_right, plot_bottom)
        # Y-axis
        painter.drawLine(margin_left, plot_top, margin_left, plot_bottom)

        # Y-axis ticks and labels (0.0, 0.5, 1.0)
        tick_font = QFont(self.font())
        tick_font.setPointSize(max(7, tick_font.pointSize() - 2))
        painter.setFont(tick_font)
        painter.setPen(mid_color)
        painter.drawText(
            QRectF(0, plot_bottom - 10, margin_left - 4, 20), Qt.AlignmentFlag.AlignRight, "0.0"
        )
        painter.drawText(
            QRectF(0, (plot_top + plot_bottom) / 2 - 10, margin_left - 4, 20),
            Qt.AlignmentFlag.AlignRight,
            "0.5",
        )
        painter.drawText(
            QRectF(0, plot_top - 10, margin_left - 4, 20), Qt.AlignmentFlag.AlignRight, "1.0"
        )

        # Total probability indicator in top-right
        total_prob = sum(b.probability for b in self._bars)
        painter.drawText(
            QRectF(plot_right - 100, 4, 100, 16),
            Qt.AlignmentFlag.AlignRight,
            f"Total: {total_prob:.3f}",
        )

        # Draw bars and labels
        label_font = QFont(self.font())
        label_font.setPointSize(max(7, label_font.pointSize() - 2))
        painter.setFont(label_font)

        bar_pen = QPen(text_color, 1.0)
        painter.setBrush(bar_fill)

        for bar in self._bars:
            if bar.height > 0:
                rect = QRectF(bar.x, bar.y, bar.width, bar.height)
                painter.setPen(bar_pen)
                painter.drawRect(rect)

            if bar.show_label:
                painter.setPen(text_color)
                painter.drawText(
                    QRectF(bar.x - 2, plot_bottom + 4, bar.width + 4, 20),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    bar.label,
                )
