"""Tests for CircuitCanvas rendering and updates."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession
from libqsim.domain.models import GateType
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from qsim_gui.state import SessionAdapter
from qsim_gui.widgets.circuit_canvas import CircuitCanvas
from qsim_gui.widgets.grid import GridGeometry


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


def _pixmap_to_bytes(pixmap) -> bytes:
    image: QImage = pixmap.toImage()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


@pytest.mark.req("FR-1.11", "NFR-2.4", "NFR-2.5", "NFR-2.7")
def test_canvas_renders_sample_circuit_not_blank(qapp: QApplication) -> None:
    session = EditorSession()
    sample_path = Path(__file__).resolve().parents[2] / "examples" / "sample.qcs"
    assert sample_path.exists()
    outcome = session.open(sample_path)
    assert outcome.ok is True

    adapter = SessionAdapter(session)
    geo = GridGeometry(cell_width=48, cell_height=48)
    canvas = CircuitCanvas(adapter=adapter, geometry=geo)
    canvas.resize(canvas.sizeHint())

    expected_w, expected_h = geo.content_size(num_qubits=session.circuit.num_qubits, num_columns=50)
    assert canvas.width() == expected_w
    assert canvas.height() == expected_h

    pixmap = canvas.grab()
    assert pixmap.width() == expected_w
    assert pixmap.height() == expected_h

    png_bytes = _pixmap_to_bytes(pixmap)
    assert len(png_bytes) > 0

    # Ensure rendered canvas is not all single solid color (not blank)
    image: QImage = pixmap.toImage()
    unique_colors = set()
    for y in range(0, min(100, image.height()), 5):
        for x in range(0, min(200, image.width()), 10):
            unique_colors.add(image.pixel(x, y))
    assert len(unique_colors) > 1, "Canvas appears completely blank"


@pytest.mark.req("FR-1.11")
def test_canvas_re_renders_on_circuit_mutation(qapp: QApplication) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    canvas = CircuitCanvas(adapter=adapter)
    canvas.resize(canvas.sizeHint())

    pix1 = canvas.grab()
    bytes1 = _pixmap_to_bytes(pix1)

    # Mutate circuit
    res = place_gate(session.circuit, GateType.X, qubit=0, column=0)
    adapter.apply(res)

    pix2 = canvas.grab()
    bytes2 = _pixmap_to_bytes(pix2)

    assert bytes1 != bytes2, "Canvas rendering did not update after circuit edit"
