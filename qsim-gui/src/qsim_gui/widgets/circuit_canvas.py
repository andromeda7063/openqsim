"""Scrollable read-only circuit canvas widget with drag-and-drop placement."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libqsim.application.operations import OperationResult, delete_gates, place_gate
from libqsim.application.selection import gate_at
from libqsim.application.session import EditorSession
from libqsim.domain.models import GatePlacement, GateType
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QTimer
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
from PySide6.QtWidgets import QMenu, QScrollArea, QWidget
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


@dataclass(frozen=True)
class PreviewFeedback:
    status: str
    reason: str = ""


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
        self._drag_preview: GatePlacement | None = None
        self._drag_feedback: PreviewFeedback | None = None
        self._move_feedback: PreviewFeedback | None = None
        self._marquee_pixel_start: QPoint | None = None
        self._marquee_pixel_current: QPoint | None = None
        self._scroll_area: QScrollArea | None = None
        self._viewport: QWidget | None = None
        self._revealed_columns = 50
        self._temporary_column = -1
        self._palette_gate: GateType | None = None
        self._edge_pointer: QPoint | None = None
        self._edge_direction = (0, 0)
        self._edge_gesture = ""
        self._edge_delay = QTimer(self)
        self._edge_delay.setSingleShot(True)
        self._edge_delay.timeout.connect(self._begin_edge_scroll)
        self._edge_repeat = QTimer(self)
        self._edge_repeat.setInterval(120)
        self._edge_repeat.timeout.connect(self._edge_step)
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

    @property
    def revealed_columns(self) -> int:
        return self._revealed_columns

    @property
    def drag_preview(self) -> GatePlacement | None:
        return self._drag_preview

    @property
    def move_preview(self) -> tuple[GatePlacement, ...]:
        if not self._controller.is_dragging_move:
            return ()
        d_q, d_c = self._controller.drag_delta
        return tuple(
            GatePlacement(
                p.gate_type,
                (q + d_q for q in p.targets),
                (q + d_q for q in p.controls),
                p.column + d_c,
            )
            for p in self._controller.selection
        )

    @property
    def preview_feedback(self) -> PreviewFeedback | None:
        if self._controller.is_dragging_move:
            return self._move_feedback
        return self._drag_feedback

    @staticmethod
    def _feedback(result: OperationResult) -> PreviewFeedback:
        return PreviewFeedback(result.status, result.messages[0] if result.messages else "")

    def reveal_temporary_column(self, column: int) -> None:
        """Extend the active gesture's visible grid without editing the circuit."""
        column = min(49, column)
        if column != self._temporary_column:
            self._temporary_column = column
            self._update_dimensions()
            self.update()

    def _clear_temporary_columns(self) -> None:
        if self._temporary_column != -1:
            self._temporary_column = -1
            self._update_dimensions()

    def _stop_edge_scroll(self) -> None:
        had_cue = self._edge_direction != (0, 0)
        self._edge_delay.stop()
        self._edge_repeat.stop()
        self._edge_direction = (0, 0)
        self._edge_pointer = None
        self._edge_gesture = ""
        if had_cue:
            self.update()

    def _track_edge(self, pt: QPoint, gesture: str) -> None:
        if self._scroll_area is None:
            return
        viewport = self._scroll_area.viewport()
        pointer = viewport.mapFromGlobal(self.mapToGlobal(pt))
        if not viewport.rect().contains(pointer):
            self._stop_edge_scroll()
            return
        dx = -1 if pointer.x() < 24 else 1 if pointer.x() >= viewport.width() - 24 else 0
        dy = -1 if pointer.y() < 24 else 1 if pointer.y() >= viewport.height() - 24 else 0
        direction = (dx, dy)
        if direction == (0, 0):
            self._stop_edge_scroll()
            return
        self._edge_pointer = pointer
        if direction != self._edge_direction or gesture != self._edge_gesture:
            self._edge_direction = direction
            self._edge_gesture = gesture
            self._edge_repeat.stop()
            self._edge_delay.start(150)
            self.update()

    def _begin_edge_scroll(self) -> None:
        self._edge_step()
        if self._edge_direction != (0, 0):
            self._edge_repeat.start()

    def _edge_step(self) -> None:
        if self._scroll_area is None or self._edge_pointer is None:
            return
        dx, dy = self._edge_direction
        hbar = self._scroll_area.horizontalScrollBar()
        vbar = self._scroll_area.verticalScrollBar()
        if dx > 0 and hbar.value() == hbar.maximum() and self._revealed_columns < 50:
            self.reveal_temporary_column(self._revealed_columns)
        if dx:
            hbar.setValue(hbar.value() + dx * self._geo.cell_width)
        if dy:
            vbar.setValue(vbar.value() + dy * self._geo.cell_height)
        pt = self.mapFromGlobal(self._scroll_area.viewport().mapToGlobal(self._edge_pointer))
        if self._edge_gesture == "palette" and self._palette_gate is not None:
            self._update_drag_highlight(pt, self._palette_gate)
        elif self._edge_gesture in ("move", "marquee"):
            self._update_mouse_gesture(pt)

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None and isinstance(parent.parentWidget(), QScrollArea):
            area = parent.parentWidget()
            if area is not self._scroll_area:
                if self._viewport is not None:
                    self._viewport.removeEventFilter(self)
                self._scroll_area = area
                self._viewport = area.viewport()
                self._viewport.installEventFilter(self)
            self._update_dimensions()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]
        if (
            getattr(self, "_scroll_area", None) is not None
            and watched is getattr(self, "_viewport", None)
            and event.type() == QEvent.Type.Resize
        ):
            self._update_dimensions()
        return super().eventFilter(watched, event)

    def _update_dimensions(self) -> None:
        num_qubits = self._adapter.circuit.num_qubits
        viewport = self._scroll_area.viewport() if self._scroll_area is not None else None
        visible = self._geo.visible_columns(viewport.width()) if viewport is not None else 50
        highest = max((p.column for p in self._adapter.circuit.placements), default=-1)
        self._revealed_columns = min(50, max(visible, highest + 2, self._temporary_column + 1))
        w, h = self._geo.content_size(num_qubits, self._revealed_columns)
        if viewport is not None:
            if self._revealed_columns <= visible:
                w = viewport.width()
            h = max(h, viewport.height())
        self.setFixedSize(w, h)
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        num_qubits = self._adapter.circuit.num_qubits
        w, h = self._geo.content_size(num_qubits=num_qubits, num_columns=self._revealed_columns)
        return QSize(w, h)

    def _on_session_changed(self) -> None:
        self._controller.prune(self._adapter.circuit)
        self._update_dimensions()
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        gate = decode_gate_mime(event.mimeData())
        if gate is not None:
            self._palette_gate = gate
            event.acceptProposedAction()
            pt = event.position().toPoint()
            self._update_drag_highlight(pt, gate)
            self._track_edge(pt, "palette")

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        gate = decode_gate_mime(event.mimeData())
        if gate is not None:
            self._palette_gate = gate
            event.acceptProposedAction()
            pt = event.position().toPoint()
            self._update_drag_highlight(pt, gate)
            self._track_edge(pt, "palette")

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._stop_edge_scroll()
        self._palette_gate = None
        self._clear_temporary_columns()
        self._drag_feedback = None
        if self._drag_cells or self._drag_preview is not None:
            self._drag_cells = []
            self._drag_preview = None
            self.update()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        pt = event.position().toPoint()
        inside_widget = self.rect().contains(pt)
        cell = self._geo.point_to_cell(
            pt.x(),
            pt.y(),
            num_qubits=self._adapter.circuit.num_qubits,
            num_columns=self._revealed_columns,
        )
        self._stop_edge_scroll()
        self._palette_gate = None
        self._clear_temporary_columns()
        self._drag_feedback = None
        if self._drag_cells or self._drag_preview is not None:
            self._drag_cells = []
            self._drag_preview = None
            self.update()

        gate_type = decode_gate_mime(event.mimeData())
        if gate_type is None:
            event.ignore()
            return

        if cell is None:
            if inside_widget and self._ui is not None:
                self._ui.show_error("Placement Error", "Placement is outside the circuit grid.")
                event.acceptProposedAction()
            else:
                event.ignore()
            return

        res = handle_drop(self._adapter.session, gate_type, cell)
        if res.status == "rejected" and self._ui is not None:
            self._ui.show_error("Placement Error", "\n".join(res.messages))
        event.acceptProposedAction()

    def _update_drag_highlight(self, pt: QPoint, gate_type: GateType) -> None:
        cell = self._geo.point_to_cell(
            pt.x(),
            pt.y(),
            num_qubits=self._adapter.circuit.num_qubits,
            num_columns=self._revealed_columns,
        )
        if cell is None:
            self._drag_feedback = PreviewFeedback(
                "rejected", "Placement is outside the circuit grid."
            )
            if self._drag_cells or self._drag_preview is not None:
                self._drag_cells = []
                self._drag_preview = None
            self.update()
            return

        q, c = cell
        if gate_type == GateType.CNOT:
            cells = [(q, c), (q + 1, c)]
            controls, targets = (q,), (q + 1,)
        elif gate_type == GateType.Toffoli:
            cells = [(q, c), (q + 1, c), (q + 2, c)]
            controls, targets = (q, q + 1), (q + 2,)
        else:
            cells = [(q, c)]
            controls, targets = (), (q,)

        preview = GatePlacement(gate_type, targets, controls, c)
        self._drag_feedback = self._feedback(place_gate(self._adapter.circuit, gate_type, q, c))

        if self._drag_cells != cells or self._drag_preview != preview:
            self._drag_cells = cells
            self._drag_preview = preview
            self.update()

    def scroll_selection_into_view(self) -> None:
        """Scroll the scroll area so the current selection is visible."""
        self.scroll_placements_into_view(self._controller.selection)

    def scroll_placements_into_view(self, placements: Iterable[GatePlacement]) -> None:
        """Scroll to the complete placement bounds, or their top-left cell."""
        placements = tuple(placements)
        if not placements:
            return
        all_qubits = [q for p in placements for q in p.occupied_qubits]
        all_cols = [p.column for p in placements]
        min_q, max_q = min(all_qubits), max(all_qubits)
        min_c, max_c = min(all_cols), max(all_cols)
        x0, y0, _, _ = self._geo.cell_to_rect(min_q, min_c)
        x1, y1, w, h = self._geo.cell_to_rect(max_q, max_c)
        if self._scroll_area is None:
            return
        viewport = self._scroll_area.viewport()
        hbar = self._scroll_area.horizontalScrollBar()
        vbar = self._scroll_area.verticalScrollBar()
        right, bottom = x1 + w, y1 + h
        if right - x0 <= viewport.width():
            if x0 < hbar.value():
                hbar.setValue(x0)
            elif right > hbar.value() + viewport.width():
                hbar.setValue(right - viewport.width())
        else:
            hbar.setValue(x0)
        if bottom - y0 <= viewport.height():
            if y0 < vbar.value():
                vbar.setValue(y0)
            elif bottom > vbar.value() + viewport.height():
                vbar.setValue(bottom - viewport.height())
        else:
            vbar.setValue(y0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position().toPoint()
            cell = self._geo.point_to_cell(
                pt.x(),
                pt.y(),
                num_qubits=self._adapter.circuit.num_qubits,
                num_columns=self._revealed_columns,
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
        self._update_mouse_gesture(pt)
        if self._controller.is_drag_initiated:
            self._track_edge(pt, "move")
        elif self._controller.is_marquee_active:
            self._track_edge(pt, "marquee")
        else:
            self._stop_edge_scroll()
        super().mouseMoveEvent(event)

    def _update_mouse_gesture(self, pt: QPoint) -> None:
        if self._controller.is_drag_initiated:
            cell = self._geo.point_to_cell(
                pt.x(),
                pt.y(),
                num_qubits=self._adapter.circuit.num_qubits,
                num_columns=self._revealed_columns,
            )
            if cell is not None:
                self._controller.update_drag_move(cell, (pt.x(), pt.y()))
                d_q, d_c = self._controller.drag_delta
                self._move_feedback = self._feedback(
                    self._controller.move_selection(self._adapter.circuit, d_q, d_c)
                )
            else:
                self._move_feedback = PreviewFeedback(
                    "rejected", "Move is outside the circuit grid."
                )
            self.update()
        elif self._controller.is_marquee_active and self._marquee_pixel_start is not None:
            self._marquee_pixel_current = pt
            cells = self._geo.rect_to_cells(
                self._marquee_pixel_start.x(),
                self._marquee_pixel_start.y(),
                self._marquee_pixel_current.x(),
                self._marquee_pixel_current.y(),
                num_qubits=self._adapter.circuit.num_qubits,
                num_columns=self._revealed_columns,
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

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._stop_edge_scroll()
        if self._controller.is_drag_initiated:
            pt = event.position().toPoint()
            cell = self._geo.point_to_cell(
                pt.x(),
                pt.y(),
                num_qubits=self._adapter.circuit.num_qubits,
                num_columns=self._revealed_columns,
            )
            d_q, d_c = self._controller.drag_delta
            action = self._controller.end_drag_move(self._adapter.circuit, cell)
            self._move_feedback = None
            self._clear_temporary_columns()
            if not self.rect().contains(pt):
                self.update()
                return
            if cell is None and action == "move":
                if self._ui is not None:
                    self._ui.show_error("Move Error", "Move is outside the circuit grid.")
            elif action == "move" and (d_q != 0 or d_c != 0):
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
            self._clear_temporary_columns()
            self.update()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and (
            self._controller.is_drag_initiated or self._controller.is_marquee_active
        ):
            self._stop_edge_scroll()
            self._clear_temporary_columns()
            self._controller.cancel_drag_move()
            self._controller.cancel_marquee()
            self._marquee_pixel_start = None
            self._marquee_pixel_current = None
            self._move_feedback = None
            self.update()
            event.accept()
            return
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

        for c in range(self._revealed_columns):
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
        x_last = (
            self.width()
            if self._scroll_area is not None
            and self._revealed_columns
            <= self._geo.visible_columns(self._scroll_area.viewport().width())
            else margins.left + self._revealed_columns * self._geo.cell_width
        )
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
            feedback = self.preview_feedback
            valid = feedback is None or feedback.status == "applied"
            highlight_color = pal.color(
                QPalette.ColorRole.Highlight if valid else QPalette.ColorRole.BrightText
            )
            fill_color = QColor(highlight_color)
            fill_color.setAlpha(45)
            painter.setPen(
                QPen(
                    highlight_color,
                    2.0,
                    Qt.PenStyle.SolidLine if valid else Qt.PenStyle.DashLine,
                )
            )
            painter.setBrush(fill_color)
            for q_cell, c_cell in self._drag_cells:
                if 0 <= q_cell < num_qubits and 0 <= c_cell < 50:
                    hx, hy, hw, hh = self._geo.cell_to_rect(q_cell, c_cell)
                    painter.drawRoundedRect(QRectF(hx + 2, hy + 2, hw - 4, hh - 4), 4, 4)

        if self.preview_feedback is not None and self.preview_feedback.status == "rejected":
            painter.setPen(pal.color(QPalette.ColorRole.BrightText))
            painter.drawText(
                QRectF(margins.left, 0, max(0, self.width() - margins.left), margins.top - 3),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.preview_feedback.reason,
            )

        # 3. Draw gate placements
        circuit = self._adapter.circuit
        for p in circuit.placements:
            is_selected = p in self._controller.selection
            self._draw_gate(painter, p, window_text, box_bg, is_selected)

        if self._drag_preview is not None and all(
            0 <= q < num_qubits for q in self._drag_preview.occupied_qubits
        ):
            painter.save()
            painter.setOpacity(0.7)
            self._draw_gate(painter, self._drag_preview, window_text, box_bg)
            painter.restore()

        if self.move_preview:
            painter.save()
            painter.setOpacity(0.7)
            for preview in self.move_preview:
                if 0 <= preview.column < 50 and all(
                    0 <= q < num_qubits for q in preview.occupied_qubits
                ):
                    self._draw_gate(painter, preview, window_text, box_bg)
            painter.restore()

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
            feedback = self._move_feedback
            invalid = feedback is not None and feedback.status == "rejected"
            neutral = feedback is not None and feedback.status == "noop"
            cue_color = pal.color(
                QPalette.ColorRole.BrightText if invalid else QPalette.ColorRole.Highlight
            )
            cue_style = (
                Qt.PenStyle.DashLine
                if invalid
                else Qt.PenStyle.DotLine
                if neutral
                else Qt.PenStyle.SolidLine
            )
            painter.setPen(QPen(cue_color, 2.0, cue_style))
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

        # Edge cues stay in the header and label margins, clear of gate symbols.
        if self._scroll_area is not None and self._edge_pointer is not None:
            viewport = self._scroll_area.viewport()
            origin = self.mapFromGlobal(viewport.mapToGlobal(QPoint(0, 0)))
            dx, dy = self._edge_direction
            painter.setPen(QPen(pal.color(QPalette.ColorRole.Highlight), 3.0))
            if dx:
                x = origin.x() + (viewport.width() - 3 if dx > 0 else 3)
                painter.drawLine(x, origin.y() + 2, x, origin.y() + 12)
            if dy:
                y = origin.y() + (viewport.height() - 3 if dy > 0 else 3)
                painter.drawLine(origin.x() + 2, y, origin.x() + 12, y)

    def _draw_gate(
        self,
        painter: QPainter,
        placement: GatePlacement,
        text_color: QColor,
        box_bg: QColor,
        is_selected: bool = False,
    ) -> None:
        if placement.gate_type in (GateType.CNOT, GateType.Toffoli):
            self._draw_multi_qubit_gate(
                painter, placement, text_color, box_bg, is_selected=is_selected
            )
        elif placement.gate_type == GateType.Measurement:
            self._draw_measurement(
                painter,
                placement.targets[0],
                placement.column,
                text_color,
                box_bg,
                is_selected=is_selected,
            )
        else:
            self._draw_single_qubit_gate(
                painter, placement, text_color, box_bg, is_selected=is_selected
            )

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
