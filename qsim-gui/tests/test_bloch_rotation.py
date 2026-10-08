"""Interaction and export checks for independently rotatable Bloch views."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtWidgets import QApplication, QPushButton
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.bloch_view import (
    DEFAULT_ELEVATION,
    DEFAULT_YAW,
    BlochSphereWidget,
)


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


def drag(sphere: BlochSphereWidget, start: QPointF, end: QPointF) -> None:
    for kind, position, buttons in (
        (QMouseEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton),
        (QMouseEvent.Type.MouseMove, end, Qt.MouseButton.LeftButton),
        (QMouseEvent.Type.MouseButtonRelease, end, Qt.MouseButton.NoButton),
    ):
        event = QMouseEvent(
            kind,
            position,
            position,
            Qt.MouseButton.LeftButton
            if kind != QMouseEvent.Type.MouseMove
            else Qt.MouseButton.NoButton,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(sphere, event)


@pytest.mark.req("FR-4.18", "FR-4.19", "FR-4.21")
def test_drag_is_independent_view_state_and_reset(qapp: QApplication) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter = SessionAdapter(session)
    window = MainWindow(adapter=adapter, ui=StubUserInterface())
    assert adapter.run().ok
    spheres = window._results_panel._bloch_view._spheres
    assert len(spheres) == 2
    before = (
        session.circuit,
        session.simulation_result,
        session.save_status,
        session.simulation_status,
        session.selected_step,
        session.can_undo,
        session.can_redo,
        tuple(session._history._undo_stack),
        tuple(session._history._redo_stack),
        spheres[0].vector,
    )

    drag(spheres[0], QPointF(88, 93), QPointF(113, 103))
    assert spheres[0].yaw != DEFAULT_YAW
    assert spheres[0].elevation != DEFAULT_ELEVATION
    assert (spheres[1].yaw, spheres[1].elevation) == (DEFAULT_YAW, DEFAULT_ELEVATION)
    assert (
        session.circuit,
        session.simulation_result,
        session.save_status,
        session.simulation_status,
        session.selected_step,
        session.can_undo,
        session.can_redo,
        tuple(session._history._undo_stack),
        tuple(session._history._redo_stack),
        spheres[0].vector,
    ) == before

    angle = (spheres[0].yaw, spheres[0].elevation)
    drag(spheres[0], QPointF(5, 5), QPointF(30, 20))
    assert (spheres[0].yaw, spheres[0].elevation) == angle

    button = spheres[0].findChild(QPushButton, "reset_view_button")
    assert button is not None
    button.click()
    assert (spheres[0].yaw, spheres[0].elevation) == (DEFAULT_YAW, DEFAULT_ELEVATION)


@pytest.mark.req("FR-4.10", "FR-4.20", "FR-4.22", "FR-4.23")
def test_snapshot_preserves_angle_and_export_matches_view(
    qapp: QApplication, tmp_path: Path
) -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter = SessionAdapter(session)
    window = MainWindow(adapter=adapter, ui=StubUserInterface())
    assert adapter.run().ok
    sphere = window._results_panel._bloch_view._spheres[0]
    initial_vector = sphere.vector
    assert "z = 1.0000" in sphere.toolTip()

    initial_path = tmp_path / "initial.png"
    assert window.export_bloch_image(initial_path)
    initial = QImage(str(initial_path))
    drag(sphere, QPointF(88, 93), QPointF(120, 110))
    angle = (sphere.yaw, sphere.elevation)
    rotated_path = tmp_path / "rotated.png"
    assert window.export_bloch_image(rotated_path)
    assert QImage(str(rotated_path)) != initial

    adapter.select_step(1)
    assert window._results_panel._bloch_view._spheres[0] is sphere
    assert sphere.vector != initial_vector
    assert (sphere.yaw, sphere.elevation) == angle
    selected_path = tmp_path / "selected.png"
    assert window.export_bloch_image(selected_path)
    assert QImage(str(selected_path)) != QImage(str(rotated_path))

    adapter.select_step(0)
    assert sphere.vector == initial_vector
    assert (sphere.yaw, sphere.elevation) == angle
    sphere.reset_view()
    reset_path = tmp_path / "reset.png"
    assert window.export_bloch_image(reset_path)
    assert QImage(str(reset_path)) == initial

    drag(sphere, QPointF(88, 93), QPointF(105, 110))
    angle = (sphere.yaw, sphere.elevation)
    assert adapter.run().ok
    assert window._results_panel._bloch_view._spheres[0] is sphere
    assert (sphere.yaw, sphere.elevation) == angle
