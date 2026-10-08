"""Results panel integrating Bloch sphere view, histogram view, and stale indicator."""

from libqsim.application.session import SimulationStatus
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.bloch_view import BlochView
from qsim_gui.widgets.histogram_view import HistogramView


class ResultsPanel(QWidget):
    """Panel containing Bloch spheres, histogram, explanatory text, and stale banner."""

    def __init__(self, adapter: SessionAdapter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("results_panel")
        self._adapter = adapter

        self._setup_ui()
        self._adapter.changed.connect(self._on_session_changed)
        self._on_session_changed()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Stale banner
        self._stale_banner = QLabel("Results are out of date. Run again.", self)
        self._stale_banner.setObjectName("stale_banner")
        self._stale_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stale_banner.setStyleSheet(
            "background-color: #ffd6d6; color: #990000; font-weight: bold; "
            "padding: 6px; border: 1px solid #cc0000; border-radius: 4px;"
        )
        self._stale_banner.setVisible(False)
        layout.addWidget(self._stale_banner)

        # Empty state label
        self._empty_label = QLabel(
            "No simulation results yet.\nBuild a circuit and click Run to simulate.", self
        )
        self._empty_label.setObjectName("empty_state_label")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #666; padding: 40px; font-size: 13px;")
        layout.addWidget(self._empty_label)

        # Content container
        self._content_widget = QWidget(self)
        content_layout = QHBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        bloch_section = QWidget(self._content_widget)
        bloch_layout = QVBoxLayout(bloch_section)
        bloch_layout.setContentsMargins(0, 0, 0, 0)
        bloch_layout.setSpacing(4)

        # Bloch section header & explanation (FR-4.14)
        bloch_header = QLabel("Bloch Spheres (Single-Qubit Reduced States)", bloch_section)
        bloch_header_font = QFont(self.font())
        bloch_header_font.setBold(True)
        bloch_header.setFont(bloch_header_font)
        bloch_layout.addWidget(bloch_header)

        bloch_exp = QLabel(
            "Each sphere visualises one qubit's state. Pure states lie on the surface (|r| = 1). "
            "Entangled or mixed states appear inside the sphere (|r| < 1), with maximally entangled qubits at center.",
            bloch_section,
        )
        bloch_exp.setObjectName("explanation_label")
        bloch_exp.setWordWrap(True)
        bloch_exp.setStyleSheet("color: #555; font-size: 11px;")
        bloch_layout.addWidget(bloch_exp)

        # Bloch view in scroll area
        self._bloch_view = BlochView(bloch_section)
        bloch_scroll = QScrollArea(bloch_section)
        bloch_scroll.setWidget(self._bloch_view)
        bloch_scroll.setWidgetResizable(True)
        bloch_scroll.setMinimumHeight(180)
        bloch_layout.addWidget(bloch_scroll, 1)
        content_layout.addWidget(bloch_section, 1)

        sep = QFrame(self._content_widget)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(sep)

        histogram_section = QWidget(self._content_widget)
        histogram_layout = QVBoxLayout(histogram_section)
        histogram_layout.setContentsMargins(0, 0, 0, 0)
        histogram_layout.setSpacing(4)

        # Histogram section header & explanation (FR-4.14)
        hist_header = QLabel("Computational-Basis Probabilities", histogram_section)
        hist_header.setFont(bloch_header_font)
        histogram_layout.addWidget(hist_header)

        hist_exp = QLabel(
            "Histogram shows full computational-basis state distribution (highest qubit on left). "
            "Probabilities are normalized to sum to 1.0. Hover over bars for exact values.",
            histogram_section,
        )
        hist_exp.setObjectName("explanation_label")
        hist_exp.setWordWrap(True)
        hist_exp.setStyleSheet("color: #555; font-size: 11px;")
        histogram_layout.addWidget(hist_exp)

        # Histogram view
        self._histogram_view = HistogramView(histogram_section)
        histogram_layout.addWidget(self._histogram_view, 1)
        content_layout.addWidget(histogram_section, 1)

        layout.addWidget(self._content_widget)
        self._content_widget.setVisible(False)

    def _on_session_changed(self) -> None:
        sim_status = self._adapter.simulation_status
        result = self._adapter.simulation_result

        # Update stale banner
        self._stale_banner.setVisible(sim_status == SimulationStatus.STALE)

        if result is not None:
            self._empty_label.setVisible(False)
            self._content_widget.setVisible(True)
            self._bloch_view.set_simulation_result(result)
            self._histogram_view.set_result(result)
        else:
            self._empty_label.setVisible(True)
            self._content_widget.setVisible(False)
            self._bloch_view.set_simulation_result(None)
            self._histogram_view.set_result(None)
