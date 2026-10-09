"""Edge scrolling and selection visibility in a controlled scroll area."""

import pytest
from libqsim.application.operations import place_gate, resize
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget
from qsim_gui.commands import CommandActions
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.theme import Theme, apply_theme
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import encode_gate_mime


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def _area(
    qapp: QApplication, session: EditorSession, width: int = 300, height: int = 220
) -> tuple[CircuitCanvas, QScrollArea]:
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    area = QScrollArea()
    area.setWidget(canvas)
    area.setFixedSize(width, height)
    area.show()
    qapp.processEvents()
    return canvas, area


@pytest.mark.req("FR-1.55")
def test_palette_edge_reveal_waits_then_stops_and_clears(qapp: QApplication) -> None:
    session = EditorSession()
    canvas, area = _area(qapp, session)
    visible = canvas.revealed_columns
    viewport = area.viewport()
    pointer = QPoint(viewport.width() - 2, canvas.grid_geometry.cell_center(0, 0)[1])
    canvas_point = canvas.mapFrom(viewport, pointer)
    mime = encode_gate_mime(GateType.H)
    enter = QDragEnterEvent(
        canvas_point,
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragEnterEvent(enter)
    assert canvas._edge_delay.isActive()
    QTest.qWait(100)
    assert canvas.revealed_columns == visible
    QTest.qWait(90)
    assert canvas.revealed_columns >= visible + 1
    initial_scroll = area.horizontalScrollBar().value()
    QTest.qWait(135)
    assert area.horizontalScrollBar().value() > initial_scroll

    for _ in range(55):
        canvas._edge_step()
    assert canvas.revealed_columns == 50
    assert canvas.drag_preview is None or canvas.drag_preview.column <= 49
    before = (session.circuit, session.save_status, session.simulation_status, session.can_undo)
    canvas.dragLeaveEvent(QDragLeaveEvent())
    qapp.processEvents()
    assert not canvas._edge_delay.isActive()
    assert not canvas._edge_repeat.isActive()
    assert canvas.revealed_columns == visible
    assert area.horizontalScrollBar().maximum() == 0
    assert (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
    ) == before


@pytest.mark.req("FR-1.55")
def test_pointer_leaving_edge_band_stops_scroll(qapp: QApplication) -> None:
    session = EditorSession()
    canvas, area = _area(qapp, session)
    viewport = area.viewport()
    mime = encode_gate_mime(GateType.X)
    edge = canvas.mapFrom(viewport, QPoint(viewport.width() - 2, 64))
    center = canvas.mapFrom(viewport, QPoint(viewport.width() // 2, 64))
    canvas.dragEnterEvent(
        QDragEnterEvent(
            edge,
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert canvas._edge_delay.isActive()
    canvas.dragMoveEvent(
        QDragMoveEvent(
            center,
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert not canvas._edge_delay.isActive()
    assert not canvas._edge_repeat.isActive()


@pytest.mark.req("FR-1.55")
def test_drop_in_temporarily_revealed_column_49(qapp: QApplication) -> None:
    session = EditorSession()
    canvas, area = _area(qapp, session)
    viewport = area.viewport()
    edge = canvas.mapFrom(viewport, QPoint(viewport.width() - 2, 64))
    mime = encode_gate_mime(GateType.H)
    canvas.dragEnterEvent(
        QDragEnterEvent(
            edge,
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    for _ in range(55):
        canvas._edge_step()
    assert canvas.revealed_columns == 50
    cx, cy = canvas.grid_geometry.cell_center(0, 49)
    drop = QDropEvent(
        QPointF(cx, cy),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(drop)
    assert session.circuit.placements[0].column == 49
    assert canvas.revealed_columns == 50


@pytest.mark.req("FR-1.55")
def test_vertical_edge_scroll_and_move_cancellation(qapp: QApplication) -> None:
    session = EditorSession()
    session.apply(resize(session.circuit, 10))
    session.apply(place_gate(session.circuit, GateType.X, 0, 0))
    canvas, area = _area(qapp, session, height=190)
    gate = session.circuit.placements[0]
    canvas.selection_controller.set_selection({gate})
    canvas.selection_controller.start_drag_move((0, 0), canvas.grid_geometry.cell_center(0, 0))
    viewport = area.viewport()
    edge = canvas.mapFrom(viewport, QPoint(84, viewport.height() - 2))
    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(edge),
        QPointF(edge),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(event)
    assert canvas._edge_delay.isActive()
    before = session.circuit
    canvas._begin_edge_scroll()
    assert area.verticalScrollBar().value() > 0
    assert canvas.selection_controller.drag_current_cell is not None
    right = canvas.mapFrom(viewport, QPoint(viewport.width() - 2, 84))
    canvas.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(right),
            QPointF(right),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    canvas._begin_edge_scroll()
    assert area.horizontalScrollBar().value() > 0
    escape = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(escape)
    assert not canvas._edge_repeat.isActive()
    assert session.circuit == before
    assert canvas.selection_controller.selection == frozenset({gate})


@pytest.mark.req("FR-1.55")
def test_marquee_tracks_cells_as_viewport_scrolls(qapp: QApplication) -> None:
    session = EditorSession()
    session.apply(resize(session.circuit, 10))
    session.apply(place_gate(session.circuit, GateType.H, 4, 1))
    canvas, area = _area(qapp, session, height=190)
    start = QPoint(*canvas.grid_geometry.cell_center(0, 1))
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(start),
        QPointF(start),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    viewport = area.viewport()
    edge = canvas.mapFrom(viewport, QPoint(start.x(), viewport.height() - 2))
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(edge),
        QPointF(edge),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    canvas._begin_edge_scroll()
    assert area.verticalScrollBar().value() > 0
    assert session.circuit.placements[0] in canvas.selection_controller.selection
    right = canvas.mapFrom(viewport, QPoint(viewport.width() - 2, 84))
    canvas.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(right),
            QPointF(right),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    canvas._begin_edge_scroll()
    assert area.horizontalScrollBar().value() > 0
    canvas.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )
    assert canvas.selection_controller.selection == frozenset()


@pytest.mark.req("FR-1.56")
def test_paste_selects_and_reveals_result(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.X, 0, 0))
    canvas, area = _area(qapp, session)
    commands = CommandActions(
        QWidget(), adapter, StubUserInterface(), selection_controller=canvas.selection_controller
    )
    commands.on_paste_applied = canvas.scroll_selection_into_view
    canvas.selection_controller.set_selection(session.circuit.placements)
    commands.action_copy.trigger()
    canvas.selection_controller.click_empty((0, 30))
    commands.action_paste.trigger()
    selection = canvas.selection_controller.selection
    assert len(selection) == 1
    pasted = next(iter(selection))
    assert pasted.column == 30
    x, _, w, _ = canvas.grid_geometry.cell_to_rect(0, 30)
    scroll = area.horizontalScrollBar().value()
    assert scroll <= x and x + w <= scroll + area.viewport().width()


@pytest.mark.req("FR-1.55", "NFR-2.9")
@pytest.mark.parametrize("theme", [Theme.DARK, Theme.DARK_PURPLE])
def test_edge_cue_renders_in_theme_margin(qapp: QApplication, theme: Theme) -> None:
    apply_theme(qapp, theme)
    session = EditorSession()
    canvas, area = _area(qapp, session)
    viewport = area.viewport()
    edge = canvas.mapFrom(viewport, QPoint(viewport.width() - 2, 64))
    cue = canvas.mapFrom(viewport, QPoint(viewport.width() - 3, 7))
    baseline = canvas.grab().toImage().pixel(cue)
    mime = encode_gate_mime(GateType.H)
    canvas.dragEnterEvent(
        QDragEnterEvent(
            edge,
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert canvas.grab().toImage().pixel(cue) != baseline
    canvas.dragLeaveEvent(QDragLeaveEvent())
    assert canvas.grab().toImage().pixel(cue) == baseline


@pytest.mark.req("FR-1.56")
def test_selection_visibility_fits_and_oversized(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, 0, 10))
    adapter.apply(place_gate(session.circuit, GateType.X, 1, 12))
    canvas, area = _area(qapp, session)
    canvas.selection_controller.set_selection(session.circuit.placements)
    canvas.scroll_selection_into_view()
    hbar = area.horizontalScrollBar()
    viewport_width = area.viewport().width()
    for p in canvas.selection_controller.selection:
        x, _, w, _ = canvas.grid_geometry.cell_to_rect(p.targets[0], p.column)
        assert hbar.value() <= x
        assert x + w <= hbar.value() + viewport_width

    adapter.apply(place_gate(session.circuit, GateType.Z, 0, 30))
    canvas.selection_controller.set_selection(session.circuit.placements)
    canvas.scroll_selection_into_view()
    left, _, w, _ = canvas.grid_geometry.cell_to_rect(0, 10)
    assert hbar.value() <= left
    assert left + w <= hbar.value() + area.viewport().width()
