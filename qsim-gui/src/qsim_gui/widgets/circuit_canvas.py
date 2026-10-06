"""Scrollable read-only circuit canvas widget with drag-and-drop placement."""

from libqsim.application.operations import OperationResult, place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QWidget
from qsim_gui.dialogs import UserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.gate_palette import decode_gate_mime
from qsim_gui.widgets.grid import GridGeometry


def handle_drop(
    session: EditorSession,
    gate_type: GateType | str,
    cell: tuple[int, int],
) -> OperationResult:
    """Pure placement helper for drop events: validates and commits on applied."""
    qubit, column = cell
    res = place_gate(session.circuit, gate_type, qubit=qubit, column=column)
    if res.status == "applied":
        session.apply(res)
    return res


class CircuitCanvas(QWidget):
    """Widget rendering quantum circuit with QPainter and supporting gate drops."""

    def __init__(
        self,
        adapter: SessionAdapter,
        geometry: GridGeometry | None = None,
        ui: UserInterface | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._geo = (
            geometry if geometry is not None else GridGeometry(cell_width=48, cell_height=48)
        )
        self._ui = ui
        self._drag_cells: list[tuple[int, int]] = []
        self.setAcceptDrops(True)

        self._update_dimensions()
        self._adapter.changed.connect(self._on_session_changed)

    @property
    def grid_geometry(self) -> GridGeometry:
        return self._geo

    def _update_dimensions(self) -> None:
        num_qubits = self._adapter.circuit.num_qubits
        w, h = self._geo.content_size(num_qubits=num_qubits, num_columns=50)
        self.setFixedSize(w, h)
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        num_qubits = self._adapter.circuit.num_qubits
        w, h = self._geo.content_size(num_qubits=num_qubits, num_columns=50)
        return QSize(w, h)

    def _on_session_changed(self) -> None:
        self._update_dimensions()
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if decode_gate_mime(event.mimeData()) is not None:
            event.acceptProposedAction()
            self._update_drag_highlight(event.position().toPoint(), event.mimeData())

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if decode_gate_mime(event.mimeData()) is not None:
            event.acceptProposedAction()
            self._update_drag_highlight(event.position().toPoint(), event.mimeData())

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        if self._drag_cells:
            self._drag_cells = []
            self.update()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._drag_cells:
            self._drag_cells = []
            self.update()

        gate_type = decode_gate_mime(event.mimeData())
        if gate_type is None:
            event.ignore()
            return

        pt = event.position().toPoint()
        cell = self._geo.point_to_cell(
            pt.x(), pt.y(), num_qubits=self._adapter.circuit.num_qubits, num_columns=50
        )
        if cell is None:
            event.ignore()
            return

        res = handle_drop(self._adapter.session, gate_type, cell)
        if res.status == "rejected" and self._ui is not None:
            self._ui.show_error("Placement Error", "\n".join(res.messages))
        event.acceptProposedAction()

    def _update_drag_highlight(self, pt: QPoint, mime_data: QMimeData) -> None:
        cell = self._geo.point_to_cell(
            pt.x(), pt.y(), num_qubits=self._adapter.circuit.num_qubits, num_columns=50
        )
        if cell is None:
            if self._drag_cells:
                self._drag_cells = []
                self.update()
            return

        gate_type = decode_gate_mime(mime_data)
        q, c = cell
        if gate_type == GateType.CNOT:
            cells = [(q, c), (q + 1, c)]
        elif gate_type == GateType.Toffoli:
            cells = [(q, c), (q + 1, c), (q + 2, c)]
        else:
            cells = [(q, c)]

        if self._drag_cells != cells:
            self._drag_cells = cells
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pal = self.palette()
        bg_color = pal.color(QPalette.ColorRole.Base)
        window_text = pal.color(QPalette.ColorRole.WindowText)
        mid_color = pal.color(QPalette.ColorRole.Mid)
        box_bg = pal.color(QPalette.ColorRole.Button)

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        num_qubits = self._adapter.circuit.num_qubits
        margins = self._geo.margins

        # 1. Draw column headers and faint vertical grid lines
        col_font = QFont(self.font())
        col_font.setPointSize(max(8, col_font.pointSize() - 2))
        painter.setFont(col_font)

        faint_grid_pen = QPen(mid_color)
        faint_color = QColor(mid_color)
        faint_color.setAlpha(45)
        faint_grid_pen.setColor(faint_color)
        faint_grid_pen.setStyle(Qt.PenStyle.DashLine)

        total_grid_height = num_qubits * self._geo.cell_height

        for c in range(50):
            cx, _ = self._geo.cell_center(0, c)
            # Column number text
            painter.setPen(mid_color)
            painter.drawText(
                QRectF(cx - 15, margins.top - 24, 30, 20),
                Qt.AlignmentFlag.AlignCenter,
                str(c),
            )
            # Vertical column separator line
            x_line = margins.left + c * self._geo.cell_width
            painter.setPen(faint_grid_pen)
            painter.drawLine(x_line, margins.top, x_line, margins.top + total_grid_height)

        # Right boundary grid line
        x_last = margins.left + 50 * self._geo.cell_width
        painter.setPen(faint_grid_pen)
        painter.drawLine(x_last, margins.top, x_last, margins.top + total_grid_height)

        # 2. Draw wire labels and horizontal wire lines
        wire_font = QFont(self.font())
        wire_font.setBold(True)
        painter.setFont(wire_font)

        wire_pen = QPen(window_text, 1.5)

        for q in range(num_qubits):
            _, cy = self._geo.cell_center(q, 0)
            # Wire label "q0", "q1", ... on the left (q0 on top)
            painter.setPen(window_text)
            painter.drawText(
                QRectF(0, cy - 12, margins.left - 12, 24),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"q{q}",
            )
            # Horizontal wire line
            painter.setPen(wire_pen)
            painter.drawLine(margins.left, cy, x_last, cy)

        # Draw drag hover highlights
        if self._drag_cells:
            highlight_color = pal.color(QPalette.ColorRole.Highlight)
            fill_color = QColor(highlight_color)
            fill_color.setAlpha(80)
            painter.setPen(QPen(highlight_color, 2.0, Qt.PenStyle.DashLine))
            painter.setBrush(fill_color)
            for q_cell, c_cell in self._drag_cells:
                if 0 <= q_cell < num_qubits and 0 <= c_cell < 50:
                    hx, hy, hw, hh = self._geo.cell_to_rect(q_cell, c_cell)
                    painter.drawRoundedRect(QRectF(hx + 2, hy + 2, hw - 4, hh - 4), 4, 4)

        # 3. Draw gate placements
        circuit = self._adapter.circuit
        for p in circuit.placements:
            if p.gate_type in (GateType.CNOT, GateType.Toffoli):
                self._draw_multi_qubit_gate(painter, p, window_text, box_bg)
            elif p.gate_type == GateType.Measurement:
                self._draw_measurement(painter, p.targets[0], p.column, window_text, box_bg)
            else:
                self._draw_single_qubit_gate(painter, p, window_text, box_bg)

    def _draw_single_qubit_gate(
        self,
        painter: QPainter,
        placement,
        text_color: QColor,
        box_bg: QColor,  # type: ignore[no-untyped-def]
    ) -> None:
        q = placement.targets[0]
        c = placement.column
        cx, cy = self._geo.cell_center(q, c)
        size = 34
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)

        # Gate box
        painter.setPen(QPen(text_color, 1.5))
        painter.setBrush(box_bg)
        painter.drawRoundedRect(rect, 4, 4)

        # Gate label
        gate_font = QFont(self.font())
        gate_font.setBold(True)
        gate_font.setPointSize(gate_font.pointSize() + 1)
        painter.setFont(gate_font)
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, placement.gate_type.value)

    def _draw_multi_qubit_gate(
        self,
        painter: QPainter,
        placement,
        line_color: QColor,
        box_bg: QColor,  # type: ignore[no-untyped-def]
    ) -> None:
        all_qubits = list(placement.controls) + list(placement.targets)
        min_q = min(all_qubits)
        max_q = max(all_qubits)
        c = placement.column

        cx, min_cy = self._geo.cell_center(min_q, c)
        _, max_cy = self._geo.cell_center(max_q, c)

        # Vertical connector line through all occupied wires
        painter.setPen(QPen(line_color, 2.0))
        painter.drawLine(cx, min_cy, cx, max_cy)

        # Control dots
        ctrl_radius = 5.0
        for ctrl_q in placement.controls:
            _, cy = self._geo.cell_center(ctrl_q, c)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(line_color)
            painter.drawEllipse(QPointF(cx, cy), ctrl_radius, ctrl_radius)

        # Target circled-plus (target can be on any wire)
        for tgt_q in placement.targets:
            _, cy = self._geo.cell_center(tgt_q, c)
            tgt_radius = 12.0
            # Outline circle
            painter.setPen(QPen(line_color, 2.0))
            painter.setBrush(box_bg)
            painter.drawEllipse(QPointF(cx, cy), tgt_radius, tgt_radius)

            # Plus lines inside circle
            painter.drawLine(cx - tgt_radius, cy, cx + tgt_radius, cy)
            painter.drawLine(cx, cy - tgt_radius, cx, cy + tgt_radius)

    def _draw_measurement(
        self, painter: QPainter, q: int, c: int, stroke_color: QColor, box_bg: QColor
    ) -> None:
        cx, cy = self._geo.cell_center(q, c)
        size = 34
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)

        # Meter box
        painter.setPen(QPen(stroke_color, 1.5))
        painter.setBrush(box_bg)
        painter.drawRoundedRect(rect, 4, 4)

        # Dial arc
        arc_rect = QRectF(cx - 11, cy - 8, 22, 16)
        painter.drawArc(arc_rect, 30 * 16, 120 * 16)

        # Dial needle pointing towards top-right
        painter.drawLine(cx, cy + 8, cx + 8, cy - 4)

        # Small arrow head on needle
        path = QPainterPath()
        path.moveTo(cx + 8, cy - 4)
        path.lineTo(cx + 4, cy - 3)
        path.lineTo(cx + 7, cy)
        path.closeSubpath()
        painter.fillPath(path, stroke_color)
