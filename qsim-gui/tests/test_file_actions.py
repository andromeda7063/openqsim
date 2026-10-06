"""Tests for GUI file actions, dirty lifecycle prompts, and image export."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from libqsim.application.guarded import UserChoice
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.domain.models import GateType
from PySide6.QtGui import QCloseEvent, QImage
from PySide6.QtWidgets import QApplication
from qsim_gui.dialogs import StubUserInterface
from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter


@pytest.fixture
def qapp() -> Generator[QApplication]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app  # type: ignore[misc]


@pytest.mark.req("FR-5.11", "LC-12", "LC-13", "LC-14", "LC-15")
def test_new_when_dirty_prompts_three_choices(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Modify circuit so it is Dirty
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert adapter.save_status == SaveStatus.DIRTY

    # 1. User selects Cancel -> circuit unchanged, still dirty
    ui.save_prompt_choices = [UserChoice.CANCEL]
    assert window.commands.handle_new() is False
    assert adapter.save_status == SaveStatus.DIRTY
    assert len(adapter.circuit.placements) == 1
    assert len(ui.save_prompts) == 1

    # 2. User selects Don't Save -> new circuit created, Clean
    ui.save_prompt_choices = [UserChoice.DONT_SAVE]
    assert window.commands.handle_new() is True
    assert adapter.save_status == SaveStatus.CLEAN
    assert len(adapter.circuit.placements) == 0
    assert len(ui.save_prompts) == 2

    # Modify circuit again
    adapter.apply(place_gate(session.circuit, GateType.X, qubit=0, column=1))
    assert adapter.save_status == SaveStatus.DIRTY

    # 3. User selects Save, but cancels the save file dialog -> aborted
    ui.save_prompt_choices = [UserChoice.SAVE]
    ui.save_file_result = None  # user cancelled file dialog
    assert window.commands.handle_new() is False
    assert adapter.save_status == SaveStatus.DIRTY
    assert len(adapter.circuit.placements) == 1

    # 4. User selects Save and provides file path -> saved then new circuit created
    save_file = tmp_path / "saved_test.qcs"
    ui.save_prompt_choices = [UserChoice.SAVE]
    ui.save_file_result = save_file
    assert window.commands.handle_new() is True
    assert save_file.exists()
    assert adapter.save_status == SaveStatus.CLEAN
    assert len(adapter.circuit.placements) == 0


@pytest.mark.req("FR-5.1", "FR-5.13", "LC-16")
def test_save_with_no_path_opens_save_dialog(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Circuit starts with no file path
    assert adapter.file_path is None

    # Cancel save dialog -> not saved
    ui.save_file_result = None
    assert window.commands.handle_save() is False
    assert adapter.file_path is None

    # Choose file in save dialog -> saved successfully
    save_file = tmp_path / "circuit1.qcs"
    ui.save_file_result = save_file
    assert window.commands.handle_save() is True
    assert save_file.exists()
    assert adapter.file_path == save_file
    assert adapter.save_status == SaveStatus.CLEAN

    # Next save uses the established path directly without prompting save dialog
    ui.save_file_result = None  # if it opened dialog, it would get None
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert adapter.save_status == SaveStatus.DIRTY
    assert window.commands.handle_save() is True
    assert adapter.save_status == SaveStatus.CLEAN


@pytest.mark.req("FR-5.12", "LC-6", "LC-17")
def test_save_as_establishes_clean_baseline(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    save_file1 = tmp_path / "c1.qcs"
    ui.save_file_result = save_file1
    assert window.commands.handle_save() is True
    assert adapter.file_path == save_file1

    # Save As to c2.qcs
    save_file2 = tmp_path / "c2.qcs"
    ui.save_file_result = save_file2
    assert window.commands.handle_save_as() is True
    assert adapter.file_path == save_file2
    assert save_file2.exists()
    assert adapter.save_status == SaveStatus.CLEAN


@pytest.mark.req("FR-5.4", "FR-5.8", "FR-5.9", "FR-5.10", "FR-5.14", "LC-11", "NFR-3.3", "NFR-3.5")
def test_failed_open_keeps_old_circuit_and_history(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Establish initial circuit with history and clean baseline
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    init_path = tmp_path / "init.qcs"
    adapter.session.save_as(init_path)
    assert len(adapter.circuit.placements) == 1
    assert adapter.can_undo is True
    assert adapter.save_status == SaveStatus.CLEAN

    # 1. Attempt to open a non-existent file
    non_existent = tmp_path / "does_not_exist.qcs"
    ui.open_file_result = non_existent
    assert window.commands.handle_open() is False
    assert len(ui.errors) == 1
    assert len(adapter.circuit.placements) == 1
    assert adapter.can_undo is True

    # 2. Attempt to open a malformed file
    bad_file = tmp_path / "corrupt.qcs"
    bad_file.write_text("NOT A JSON OBJECT", encoding="utf-8")
    ui.open_file_result = bad_file
    assert window.commands.handle_open() is False
    assert len(ui.errors) == 2
    assert len(adapter.circuit.placements) == 1
    assert adapter.can_undo is True


@pytest.mark.req("FR-5.11", "FR-5.4", "LC-12", "LC-14")
def test_open_when_dirty_prompts(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Create a valid target file to open
    other_session = EditorSession()
    other_session.apply(place_gate(other_session.circuit, GateType.X, qubit=1, column=2))
    target_path = tmp_path / "target.qcs"
    other_session.save_as(target_path)

    # Modify current session to dirty
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert adapter.save_status == SaveStatus.DIRTY

    # Open with Don't Save
    ui.save_prompt_choices = [UserChoice.DONT_SAVE]
    ui.open_file_result = target_path
    assert window.commands.handle_open() is True
    assert adapter.save_status == SaveStatus.CLEAN
    assert adapter.file_path == target_path
    assert len(adapter.circuit.placements) == 1
    assert adapter.circuit.placements[0].gate_type == GateType.X


@pytest.mark.req("FR-6.11", "FR-6.12", "NFR-3.5")
def test_import_openqasm_success_and_failure(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Build and save initial circuit
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    init_path = tmp_path / "init.qcs"
    adapter.session.save_as(init_path)

    # 1. Import invalid OpenQASM -> error reported, state untouched
    bad_qasm = tmp_path / "invalid.qasm"
    bad_qasm.write_text("INVALID QASM CONTENT", encoding="utf-8")
    ui.open_file_result = bad_qasm
    assert window.commands.handle_import_qasm() is False
    assert len(ui.errors) == 1
    assert adapter.file_path == init_path
    assert len(adapter.circuit.placements) == 1

    # 2. Import valid OpenQASM -> replaces session as new unsaved session
    valid_qasm = tmp_path / "valid.qasm"
    valid_qasm.write_text(
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nx q[0];\n',
        encoding="utf-8",
    )
    ui.open_file_result = valid_qasm
    assert window.commands.handle_import_qasm() is True
    assert adapter.file_path is None  # no file path
    assert adapter.baseline is None  # no baseline
    assert adapter.save_status == SaveStatus.DIRTY
    assert adapter.simulation_status == SimulationStatus.NONE
    assert adapter.can_undo is False
    assert len(adapter.circuit.placements) == 1
    assert adapter.circuit.placements[0].gate_type == GateType.X


@pytest.mark.req("FR-6.4", "NFR-3.3")
def test_export_openqasm_success_and_failure(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))

    # Export successfully
    export_path = tmp_path / "exported.qasm"
    ui.save_file_result = export_path
    assert window.commands.handle_export_qasm() is True
    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8")
    assert "h q[0];" in content

    # Export failure (e.g. invalid directory path)
    ui.save_file_result = Path("/nonexistent_dir/subdir/exported.qasm")
    assert window.commands.handle_export_qasm() is False
    assert len(ui.errors) >= 1


@pytest.mark.req("FR-5.11", "LC-12", "LC-13", "LC-14", "LC-15")
def test_window_close_dirty_lifecycle(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # 1. Clean circuit -> close accepted
    event1 = QCloseEvent()
    window.closeEvent(event1)
    assert event1.isAccepted() is True

    # Modify circuit to Dirty
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert adapter.save_status == SaveStatus.DIRTY

    # 2. Dirty + Cancel -> close ignored
    ui.save_prompt_choices = [UserChoice.CANCEL]
    event2 = QCloseEvent()
    window.closeEvent(event2)
    assert event2.isAccepted() is False

    # 3. Dirty + Don't Save -> close accepted
    ui.save_prompt_choices = [UserChoice.DONT_SAVE]
    event3 = QCloseEvent()
    window.closeEvent(event3)
    assert event3.isAccepted() is True

    # 4. Dirty + Save (succeeds) -> close accepted
    save_file = tmp_path / "closed.qcs"
    ui.save_prompt_choices = [UserChoice.SAVE]
    ui.save_file_result = save_file
    event4 = QCloseEvent()
    window.closeEvent(event4)
    assert event4.isAccepted() is True
    assert save_file.exists()


@pytest.mark.req("FR-4.11", "FR-4.12", "FR-4.13", "NFR-6.4")
def test_export_images_circuit_bloch_histogram(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    # Build and simulate Bell state
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    adapter.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    adapter.run()
    assert adapter.simulation_status == SimulationStatus.CURRENT

    # 1. Export Circuit Diagram (FULL 50-column canvas)
    circuit_png = tmp_path / "circuit.png"
    ui.save_file_result = circuit_png
    assert window.export_circuit_image() is True
    assert circuit_png.exists()

    img = QImage(str(circuit_png))
    assert not img.isNull()
    # Width must match full 50-column canvas width
    canvas_w = window.canvas.size().width()
    canvas_h = window.canvas.size().height()
    assert img.width() == canvas_w
    assert img.height() == canvas_h

    # 2. Export Bloch View
    bloch_png = tmp_path / "bloch.png"
    ui.save_file_result = bloch_png
    assert window.export_bloch_image() is True
    assert bloch_png.exists()

    bloch_img = QImage(str(bloch_png))
    assert not bloch_img.isNull()
    assert bloch_img.width() > 0
    assert bloch_img.height() > 0

    # 3. Export Histogram View
    hist_png = tmp_path / "hist.png"
    ui.save_file_result = hist_png
    assert window.export_histogram_image() is True
    assert hist_png.exists()

    hist_img = QImage(str(hist_png))
    assert not hist_img.isNull()
    assert hist_img.width() > 0
    assert hist_img.height() > 0

    # 4. Export failure shows error dialog
    ui.save_file_result = Path("/nonexistent_dir/bad/circuit.png")
    assert window.export_circuit_image() is False
    assert len(ui.errors) >= 1


@pytest.mark.req("FR-5.1", "FR-5.4", "FR-6.11")
def test_window_title_and_indicators_on_file_actions(qapp: QApplication, tmp_path: Path) -> None:
    session = EditorSession()
    adapter = SessionAdapter(session)
    ui = StubUserInterface()
    window = MainWindow(adapter=adapter, ui=ui)

    assert "Untitled [*] - OpenQSim" in window.windowTitle()
    assert window.isWindowModified() is False

    # Modify -> Dirty
    adapter.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert window.isWindowModified() is True

    # Save -> Clean
    save_file = tmp_path / "my_circuit.qcs"
    ui.save_file_result = save_file
    assert window.commands.handle_save() is True
    assert window.isWindowModified() is False
    assert "my_circuit.qcs" in window.windowTitle()
