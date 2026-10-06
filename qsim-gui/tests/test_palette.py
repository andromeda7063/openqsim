"""Tests for GatePalette and MIME payload serialization."""

import os
from collections.abc import Generator

import pytest
from libqsim.domain.models import GateType
from PySide6.QtWidgets import QApplication
from qsim_gui.widgets.gate_palette import (
    GATE_MIME_TYPE,
    GatePalette,
    decode_gate_mime,
    encode_gate_mime,
)


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-1.4", "FR-7.3")
def test_palette_contains_exactly_nine_items_with_tooltips(qapp: QApplication) -> None:
    palette = GatePalette()
    items = palette.items()

    assert len(items) == 9

    expected_gates = [
        GateType.H,
        GateType.X,
        GateType.Y,
        GateType.Z,
        GateType.S,
        GateType.T,
        GateType.CNOT,
        GateType.Toffoli,
        GateType.Measurement,
    ]

    found_gates = [gate for gate, _ in items]
    assert found_gates == expected_gates

    for gate, tooltip in items:
        assert isinstance(tooltip, str)
        assert len(tooltip.strip()) > 5, f"Tooltip for {gate.value} is missing or too short"


@pytest.mark.req("FR-1.4", "NFR-6.4")
def test_mime_encode_decode_round_trip(qapp: QApplication) -> None:
    for gate_type in GateType:
        mime_data = encode_gate_mime(gate_type)
        assert mime_data.hasFormat(GATE_MIME_TYPE)
        decoded = decode_gate_mime(mime_data)
        assert decoded == gate_type
