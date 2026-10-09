"""Candidate feedback agrees with headless operations without editing the session."""

import pytest
from libqsim.application.operations import move_gates, place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QPalette
from PySide6.QtWidgets import QApplication
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.state import SessionAdapter
from qsim_gui.theme import Theme, apply_theme
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.gate_palette import encode_gate_mime


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def _hover(canvas: CircuitCanvas, gate: GateType, q: int, col: int) -> None:
    cx, cy = canvas.grid_geometry.cell_center(q, col)
    mime = encode_gate_mime(gate)
    canvas.dragEnterEvent(
        QDragEnterEvent(
            QPoint(cx, cy),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


@pytest.mark.req("FR-1.54")
def test_palette_feedback_matches_operations_and_preserves_state(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter)
    adapter.apply(place_gate(session.circuit, GateType.H, 0, 0))
    before = (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    )
    for gate, q, col in [(GateType.X, 1, 1), (GateType.X, 0, 0), (GateType.CNOT, 1, 2)]:
        _hover(canvas, gate, q, col)
        result = place_gate(session.circuit, gate, q, col)
        assert canvas.preview_feedback is not None
        assert canvas.preview_feedback.status == result.status
        if result.status == "rejected":
            assert canvas.preview_feedback.reason == result.messages[0]
        assert (
            session.circuit,
            session.save_status,
            session.simulation_status,
            session.can_undo,
            session.can_redo,
        ) == before
        assert canvas.selection_controller.selection == frozenset()


@pytest.mark.req("FR-1.54")
def test_move_feedback_and_invalid_release(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    adapter.apply(place_gate(session.circuit, GateType.H, 0, 0))
    adapter.apply(place_gate(session.circuit, GateType.X, 0, 2))
    canvas = CircuitCanvas(adapter, ui=ui)
    gate = next(p for p in session.circuit.placements if p.column == 0)
    canvas.selection_controller.set_selection({gate})
    canvas.selection_controller.start_drag_move((0, 0), (84, 64))
    before = (
        session.circuit,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    )
    for col, expected in [(0, "noop"), (1, "applied"), (2, "rejected")]:
        cx, cy = canvas.grid_geometry.cell_center(0, col)
        if col == 0:
            cx += 10
        event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(cx, cy),
            QPointF(cx, cy),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mouseMoveEvent(event)
        assert canvas.preview_feedback is not None
        assert canvas.preview_feedback.status == expected
        assert (
            session.circuit,
            session.save_status,
            session.simulation_status,
            session.can_undo,
            session.can_redo,
        ) == before
        assert canvas.selection_controller.selection == frozenset({gate})

    cx, cy = canvas.grid_geometry.cell_center(0, 2)
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(cx, cy),
        QPointF(cx, cy),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(release)
    assert len(ui.errors) == 1
    assert session.circuit == before[0]
    assert canvas.selection_controller.selection == frozenset({gate})


@pytest.mark.req("FR-1.54")
def test_measurement_and_vacated_cell_preview(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.Measurement, 1, 2))
    canvas = CircuitCanvas(adapter)
    _hover(canvas, GateType.H, 1, 3)
    assert canvas.preview_feedback is not None
    assert canvas.preview_feedback.status == "rejected"
    assert "Measurement" in canvas.preview_feedback.reason

    session.new()
    adapter.apply(place_gate(session.circuit, GateType.H, 0, 0))
    adapter.apply(place_gate(session.circuit, GateType.X, 0, 1))
    selected = frozenset(session.circuit.placements)
    canvas.selection_controller.set_selection(selected)
    canvas.selection_controller.start_drag_move((0, 0), (84, 64))
    cx, cy = canvas.grid_geometry.cell_center(0, 1)
    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(cx, cy),
        QPointF(cx, cy),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(event)
    expected = move_gates(session.circuit, selected, 0, 1)
    assert expected.status == "applied"
    assert canvas.preview_feedback is not None
    assert canvas.preview_feedback.status == expected.status
    assert canvas.selection_controller.selection == selected
    canvas.selection_controller.cancel_drag_move()


@pytest.mark.req("FR-1.54")
def test_valid_move_release_commits_once(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    adapter.apply(place_gate(session.circuit, GateType.H, 0, 0))
    canvas = CircuitCanvas(adapter)
    gate = session.circuit.placements[0]
    canvas.selection_controller.set_selection({gate})
    canvas.selection_controller.start_drag_move((0, 0), (84, 64))
    cx, cy = canvas.grid_geometry.cell_center(0, 1)
    canvas.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(cx, cy),
            QPointF(cx, cy),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert canvas.preview_feedback is not None
    assert canvas.preview_feedback.status == "applied"
    canvas.mouseReleaseEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(cx, cy),
            QPointF(cx, cy),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert session.circuit.placements[0].column == 1
    assert session.undo()
    assert session.circuit.placements[0].column == 0
    assert session.undo()
    assert session.circuit.placements == ()


@pytest.mark.req("FR-1.5", "FR-1.54")
def test_invalid_margin_drop_reports_once(qapp: QApplication) -> None:
    session = EditorSession()
    ui = StubUserInterface()
    canvas = CircuitCanvas(SessionAdapter(session), ui=ui)
    mime = encode_gate_mime(GateType.H)
    event = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(event)
    assert len(ui.errors) == 1
    assert "outside" in ui.errors[0][1]
    assert session.circuit.placements == ()
    assert session.can_undo is False


def _luminance(color) -> float:  # type: ignore[no-untyped-def]
    values = [color.redF(), color.greenF(), color.blueF()]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a, b) -> float:  # type: ignore[no-untyped-def]
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.req("NFR-2.9")
def test_theme_preview_colors_have_contrast(qapp: QApplication) -> None:
    for theme in (Theme.DARK, Theme.DARK_PURPLE):
        apply_theme(qapp, theme)
        palette = qapp.palette()
        base = palette.color(QPalette.ColorRole.Base)
        for role in (QPalette.ColorRole.Highlight, QPalette.ColorRole.BrightText):
            assert _contrast(palette.color(role), base) >= 3
        ghost = palette.color(QPalette.ColorRole.WindowText)
        composite = type(ghost)(
            round(0.7 * ghost.red() + 0.3 * base.red()),
            round(0.7 * ghost.green() + 0.3 * base.green()),
            round(0.7 * ghost.blue() + 0.3 * base.blue()),
        )
        assert _contrast(composite, base) >= 4.5
