"""Scrollable read-only circuit canvas widget with drag-and-drop placement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from libqsim.application.operations import OperationResult, delete_gates, place_gate
from libqsim.application.selection import gate_at
from libqsim.application.session import EditorSession
from libqsim.domain.models import GatePlacement, GateType
from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QMenu, QWidget
from qsim_gui.dialogs import UserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.gate_palette import decode_gate_mime
from qsim_gui.widgets.grid import GridGeometry
from qsim_gui.widgets.selection_controller import SelectionController

if TYPE_CHECKING:
    from qsim_gui.commands import CommandActions


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
        controller: SelectionController | None = None,
        commands: CommandActions | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._geo = (
            geometry if geometry is not None else GridGeometry(cell_width=48, cell_height=48)
        )
        self._ui = ui
        self._commands = commands
        self._controller = controller if controller is not None else SelectionController()
        self._controller.subscribe(self.update)
        self._drag_cells: list[tuple[int, int]] = []
        self._marquee_pixel_start: QPoint | None = None
        self._marquee_pixel_current: QPoint | None = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._update_dimensions()
        self._adapter.changed.connect(self._on_session_changed)

    @property
    def selection_controller(self) -> SelectionController:
        return self._controller

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
        self._controller.prune(self._adapter.circuit)
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

    def scroll_selection_into_view(self) -> None:
        """Scroll the scroll area so the current selection is visible."""
        if not self._controller.selection:
            return
        all_qubits = [q for p in self._controller.selection for q in p.occupied_qubits]
        all_cols = [p.column for p in self._controller.selection]
        min_q, max_q = min(all_qubits), max(all_qubits)
        min_c, max_c = min(all_cols), max(all_cols)
        x0, y0, _, _ = self._geo.cell_to_rect(min_q, min_c)
        x1, y1, w, h = self._geo.cell_to_rect(max_q, max_c)
        cx = (x0 + x1 + w) // 2
        cy = (y0 + y1 + h) // 2
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "ensureVisible"):
                parent.ensureVisible(cx, cy, 50, 50)
                break
            parent = parent.parentWidget()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position().toPoint()
            cell = self._geo.point_to_cell(
                pt.x(), pt.y(), num_qubits=self._adapter.circuit.num_qubits, num_columns=50
            )
            ctrl = bool(
                event.modifiers()
                & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
            )
            if cell is not None:
                hit = gate_at(self._adapter.circuit, cell[0], cell[1])
                if hit is not None:
                    self._controller.press_cell_for_drag(
                        self._adapter.circuit, cell, (pt.x(), pt.y()), ctrl=ctrl
                    )
                else:
                    self._controller.press_empty(cell, ctrl=ctrl)
                    self._controller.marquee_begin(cell, ctrl=ctrl)
                    self._marquee_pixel_start = pt
                    self._marquee_pixel_current = pt
            else:
                self._controller.press_empty((0, 0), ctrl=ctrl)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pt = event.position().toPoint()
        if self._controller.is_drag_initiated:
            cell = self._geo.point_to_cell(
                pt.x(), pt.y(), num_qubits=self._adapter.circuit.num_qubits, num_columns=50
            )
            if cell is not None:
                self._controller.update_drag_move(cell, (pt.x(), pt.y()))
            self.update()
        elif self._controller.is_marquee_active and self._marquee_pixel_start is not None:
            self._marquee_pixel_current = pt
            cells = self._geo.rect_to_cells(
                self._marquee_pixel_start.x(),
                self._marquee_pixel_start.y(),
                self._marquee_pixel_current.x(),
                self._marquee_pixel_current.y(),
                num_qubits=self._adapter.circuit.num_qubits,
                num_columns=50,
            )
            if cells:
                q_min = min(c[0] for c in cells)
                q_max = max(c[0] for c in cells)
                c_min = min(c[1] for c in cells)
                c_max = max(c[1] for c in cells)
                self._controller.marquee_update_rect(
                    self._adapter.circuit, q_min, q_max, c_min, c_max
                )
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._controller.is_drag_initiated:
            pt = event.position().toPoint()
            cell = self._geo.point_to_cell(
                pt.x(), pt.y(), num_qubits=self._adapter.circuit.num_qubits, num_columns=50
            )
            d_q, d_c = self._controller.drag_delta
            action = self._controller.end_drag_move(self._adapter.circuit, cell)
            if action == "move" and (d_q != 0 or d_c != 0):
                res = self._controller.move_selection(self._adapter.circuit, d_q, d_c)
                if res.status == "applied":
                    self._adapter.apply(res)
                    self._controller.follow_move(res)
                    self.scroll_selection_into_view()
                elif res.status == "rejected" and self._ui is not None:
                    self._ui.show_error("Move Error", "\n".join(res.messages))
            self.update()
        elif self._controller.is_marquee_active:
            self._controller.marquee_end(self._adapter.circuit)
            self._marquee_pixel_start = None
            self._marquee_pixel_current = None
            self.update()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._controller.selection:
                res = delete_gates(self._adapter.circuit, self._controller.selection)
                if res.status == "applied":
                    self._adapter.apply(res)
                    self._controller.clear_selection()
                elif res.status == "rejected" and self._ui is not None:
                    self._ui.show_error("Delete Error", "\n".join(res.messages))
            event.accept()
            return
        if event.key() == Qt.Key.Key_A and bool(
            event.modifiers()
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        ):
            self._controller.select_all(self._adapter.circuit)
            event.accept()
            return
        if event.key() == Qt.Key.Key_C and bool(
            event.modifiers()
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        ):
            if self._commands is not None:
                self._commands.action_copy.trigger()
            event.accept()
            return
        if event.key() == Qt.Key.Key_V and bool(
            event.modifiers()
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        ):
            if self._commands is not None:
                self._commands.action_paste.trigger()
            event.accept()
            return

        d_q, d_c = 0, 0
        if event.key() == Qt.Key.Key_Left:
            d_c = -1
        elif event.key() == Qt.Key.Key_Right:
            d_c = 1
        elif event.key() == Qt.Key.Key_Up:
            d_q = -1
        elif event.key() == Qt.Key.Key_Down:
            d_q = 1

        if (d_q != 0 or d_c != 0) and self._controller.selection:
            res = self._controller.move_selection(self._adapter.circuit, d_q, d_c)
            if res.status == "applied":
                self._adapter.apply(res)
                self._controller.follow_move(res)
                self.scroll_selection_into_view()
            elif res.status == "rejected" and self._ui is not None:
                self._ui.show_error("Move Error", "\n".join(res.messages))
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        if self._commands is not None:
            menu.addAction(self._commands.action_change_target)
            menu.addSeparator()
            menu.addAction(self._commands.action_delete)
        else:
            action_ct = menu.addAction("Change Target")
            action_ct.setEnabled(self._controller.can_change_target())
            action_ct.triggered.connect(self._handle_change_target)
        menu.exec(event.globalPos())

    def _handle_change_target(self) -> None:
        if not self._controller.can_change_target():
            return
        res = self._controller.change_target_selected(self._adapter.circuit)
        if res.status == "applied":
            self._adapter.apply(res)
            self._controller.follow_move(res)
        elif res.status == "rejected" and self._ui is not None:
            self._ui.show_error("Change Target Error", "\n".join(res.messages))

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
            is_selected = p in self._controller.selection
            if p.gate_type in (GateType.CNOT, GateType.Toffoli):
                self._draw_multi_qubit_gate(
                    painter, p, window_text, box_bg, is_selected=is_selected
                )
            elif p.gate_type == GateType.Measurement:
                self._draw_measurement(
                    painter, p.targets[0], p.column, window_text, box_bg, is_selected=is_selected
                )
            else:
                self._draw_single_qubit_gate(
                    painter, p, window_text, box_bg, is_selected=is_selected
                )

        # 4. Draw marquee rectangle if active
        if (
            self._controller.is_marquee_active
            and self._marquee_pixel_start is not None
            and self._marquee_pixel_current is not None
        ):
            x0 = min(self._marquee_pixel_start.x(), self._marquee_pixel_current.x())
            y0 = min(self._marquee_pixel_start.y(), self._marquee_pixel_current.y())
            w = abs(self._marquee_pixel_start.x() - self._marquee_pixel_current.x())
            h = abs(self._marquee_pixel_start.y() - self._marquee_pixel_current.y())
            marquee_rect = QRectF(x0, y0, w, h)
            highlight_color = pal.color(QPalette.ColorRole.Highlight)
            fill_color = QColor(highlight_color)
            fill_color.setAlpha(40)
            painter.setPen(QPen(highlight_color, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(fill_color)
            painter.drawRect(marquee_rect)

        # 5. Draw move preview outline if dragging move
        if self._controller.is_dragging_move:
            d_q, d_c = self._controller.drag_delta
            if d_q != 0 or d_c != 0:
                highlight_color = pal.color(QPalette.ColorRole.Highlight)
                outline_pen = QPen(highlight_color, 2.0, Qt.PenStyle.DashLine)
                painter.setPen(outline_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for p in self._controller.selection:
                    tgt_col = p.column + d_c
                    tgt_qubits = [q + d_q for q in p.occupied_qubits]
                    if all(0 <= q < num_qubits for q in tgt_qubits) and 0 <= tgt_col < 50:
                        min_q = min(tgt_qubits)
                        max_q = max(tgt_qubits)
                        hx, hy, hw, _ = self._geo.cell_to_rect(min_q, tgt_col)
                        _, b_hy, _, b_hh = self._geo.cell_to_rect(max_q, tgt_col)
                        total_h = (b_hy + b_hh) - hy
                        painter.drawRoundedRect(QRectF(hx + 3, hy + 3, hw - 6, total_h - 6), 5, 5)

    def _draw_single_qubit_gate(
        self,
        painter: QPainter,
        placement: GatePlacement,
        text_color: QColor,
        box_bg: QColor,
        is_selected: bool = False,
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

        if is_selected:
            highlight_color = self.palette().color(QPalette.ColorRole.Highlight)
            sel_rect = rect.adjusted(-3, -3, 3, 3)
            painter.setPen(QPen(highlight_color, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(sel_rect, 6, 6)

        # Gate label
        gate_font = QFont(self.font())
        gate_font.setBold(True)
        gate_font.setPointSize(gate_font.pointSize() + 1)
        painter.setFont(gate_font)
        painter.setPen(text_color)
        symbols = {
            GateType.H: "H",
            GateType.X: "X",
            GateType.Y: "Y",
            GateType.Z: "Z",
            GateType.S: "S",
            GateType.T: "T",
        }
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            symbols.get(placement.gate_type, placement.gate_type.value),
        )

    def _draw_multi_qubit_gate(
        self,
        painter: QPainter,
        placement: GatePlacement,
        line_color: QColor,
        box_bg: QColor,
        is_selected: bool = False,
    ) -> None:
        all_qubits = list(placement.controls) + list(placement.targets)
        min_q = min(all_qubits)
        max_q = max(all_qubits)
        c = placement.column

        cx, min_cy = self._geo.cell_center(min_q, c)
        _, max_cy = self._geo.cell_center(max_q, c)

        if is_selected:
            highlight_color = self.palette().color(QPalette.ColorRole.Highlight)
            hx, hy, hw, _ = self._geo.cell_to_rect(min_q, c)
            _, bottom_hy, _, bottom_hh = self._geo.cell_to_rect(max_q, c)
            total_h = (bottom_hy + bottom_hh) - hy
            sel_rect = QRectF(hx + 4, hy + 4, hw - 8, total_h - 8)
            fill = QColor(highlight_color)
            fill.setAlpha(40)
            painter.setPen(QPen(highlight_color, 2.0, Qt.PenStyle.DashLine))
            painter.setBrush(fill)
            painter.drawRoundedRect(sel_rect, 6, 6)
            line_color = highlight_color

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
        self,
        painter: QPainter,
        q: int,
        c: int,
        stroke_color: QColor,
        box_bg: QColor,
        is_selected: bool = False,
    ) -> None:
        cx, cy = self._geo.cell_center(q, c)
        size = 34
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)

        # Meter box
        painter.setPen(QPen(stroke_color, 1.5))
        painter.setBrush(box_bg)
        painter.drawRoundedRect(rect, 4, 4)

        if is_selected:
            highlight_color = self.palette().color(QPalette.ColorRole.Highlight)
            sel_rect = rect.adjusted(-3, -3, 3, 3)
            painter.setPen(QPen(highlight_color, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(sel_rect, 6, 6)

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
