"""Pure layout calculation and widget for computational basis probability histogram."""

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget


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
    raise NotImplementedError


class HistogramView(QWidget):
    """Widget displaying computational-basis state probability histogram."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
