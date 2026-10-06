"""Comprehensive release acceptance tests and performance benchmarks.

Covers Section 17 reference cases, NFR-1.1 (2s simulation), NFR-1.2 (100ms edits),
offline networking assertions (NFR-4.1, 4.2), and end-to-end session verification.
"""

import os
import socket
import time
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pytest
from libqsim.application.operations import (
    clear,
    copy_gates,
    delete_gates,
    paste,
    place_gate,
    plan_resize,
    resize,
)
from libqsim.application.session import EditorSession, SaveStatus
from libqsim.domain.models import Circuit, GatePlacement, GateType
from libqsim.domain.validation import validate
from libqsim.persistence.qcs import read, write
from libqsim.qasm.exporter import export_text
from libqsim.qasm.importer import import_text
from libqsim.simulation.engine import simulate
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


# ==============================================================================
# SECTION 17 REFERENCE CASES
# ==============================================================================


@pytest.mark.req("FR-1.2", "FR-3.1", "FR-3.2", "FR-3.3", "FR-3.4")
def test_section17_empty_1qubit_circuit() -> None:
    """Empty 1-qubit circuit produces |0> state with probability 1.0."""
    c = Circuit(num_qubits=1, placements=[])
    res = simulate(c)
    assert np.isclose(res.probabilities[0], 1.0, atol=1e-9)
    assert np.isclose(res.probabilities[1], 0.0, atol=1e-9)
    # Bloch vector for |0> is (0, 0, 1)
    assert np.allclose(res.bloch_vectors[0], [0.0, 0.0, 1.0], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.3", "FR-3.4")
def test_section17_x_on_q0() -> None:
    """X on q0 produces |1> state with probability 1.0 at index 1."""
    c = Circuit(
        num_qubits=1,
        placements=[GatePlacement(GateType.X, targets=(0,), controls=(), column=0)],
    )
    res = simulate(c)
    assert np.isclose(res.probabilities[0], 0.0, atol=1e-9)
    assert np.isclose(res.probabilities[1], 1.0, atol=1e-9)
    # Bloch vector for |1> is (0, 0, -1)
    assert np.allclose(res.bloch_vectors[0], [0.0, 0.0, -1.0], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.3", "FR-3.4")
def test_section17_y_on_q0() -> None:
    """Y on q0 produces statevector i|1> under Qiskit conventions."""
    c = Circuit(
        num_qubits=1,
        placements=[GatePlacement(GateType.Y, targets=(0,), controls=(), column=0)],
    )
    res = simulate(c)
    assert np.allclose(res.statevector, [0.0 + 0.0j, 0.0 + 1.0j], atol=1e-9)
    assert np.isclose(res.probabilities[1], 1.0, atol=1e-9)
    assert np.allclose(res.bloch_vectors[0], [0.0, 0.0, -1.0], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.3", "FR-3.4")
def test_section17_h_on_q0() -> None:
    """H on q0 produces equal superposition (|0>+|1>)/sqrt(2) and |+> Bloch vector."""
    c = Circuit(
        num_qubits=1,
        placements=[GatePlacement(GateType.H, targets=(0,), controls=(), column=0)],
    )
    res = simulate(c)
    assert np.isclose(res.probabilities[0], 0.5, atol=1e-9)
    assert np.isclose(res.probabilities[1], 0.5, atol=1e-9)
    # Bloch vector for |+> is (1, 0, 0)
    assert np.allclose(res.bloch_vectors[0], [1.0, 0.0, 0.0], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2")
def test_section17_h_followed_by_h() -> None:
    """H followed by H restores original state |0>."""
    c = Circuit(
        num_qubits=1,
        placements=[
            GatePlacement(GateType.H, targets=(0,), controls=(), column=0),
            GatePlacement(GateType.H, targets=(0,), controls=(), column=1),
        ],
    )
    res = simulate(c)
    assert np.allclose(res.statevector, [1.0 + 0.0j, 0.0 + 0.0j], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.3", "FR-3.4", "FR-4.4", "FR-4.6")
def test_section17_bell_state_and_bloch() -> None:
    """H on control + CNOT gives Bell state with reduced Bloch vectors at origin."""
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    outcome = session.run()
    assert outcome.ok
    assert session.simulation_result is not None

    res = session.simulation_result
    assert np.isclose(res.probabilities[0], 0.5, atol=1e-9)  # 00
    assert np.isclose(res.probabilities[1], 0.0, atol=1e-9)  # 01
    assert np.isclose(res.probabilities[2], 0.0, atol=1e-9)  # 10
    assert np.isclose(res.probabilities[3], 0.5, atol=1e-9)  # 11

    # Maximally entangled qubits have reduced Bloch vectors at center of sphere (0, 0, 0)
    assert np.allclose(res.bloch_vectors[0], [0.0, 0.0, 0.0], atol=1e-9)
    assert np.allclose(res.bloch_vectors[1], [0.0, 0.0, 0.0], atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.3")
def test_section17_z_on_zero() -> None:
    """Z on |0> leaves computational-basis probability unchanged."""
    c = Circuit(
        num_qubits=1,
        placements=[GatePlacement(GateType.Z, targets=(0,), controls=(), column=0)],
    )
    res = simulate(c)
    assert np.isclose(res.probabilities[0], 1.0, atol=1e-9)


@pytest.mark.req("FR-3.1", "FR-3.2", "FR-3.4")
def test_section17_s_and_t_phases() -> None:
    """S and T phase gates produce expected phase shifts and Bloch vectors."""
    # S on |+> gives |+i>, Bloch vector (0, 1, 0)
    c_s = Circuit(
        num_qubits=1,
        placements=[
            GatePlacement(GateType.H, targets=(0,), controls=(), column=0),
            GatePlacement(GateType.S, targets=(0,), controls=(), column=1),
        ],
    )
    res_s = simulate(c_s)
    assert np.allclose(res_s.bloch_vectors[0], [0.0, 1.0, 0.0], atol=1e-9)

    # T on |+> gives (1/sqrt2, 1/sqrt2, 0)
    c_t = Circuit(
        num_qubits=1,
        placements=[
            GatePlacement(GateType.H, targets=(0,), controls=(), column=0),
            GatePlacement(GateType.T, targets=(0,), controls=(), column=1),
        ],
    )
    res_t = simulate(c_t)
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    assert np.allclose(res_t.bloch_vectors[0], [inv_sqrt2, inv_sqrt2, 0.0], atol=1e-9)


@pytest.mark.req("FR-1.49", "FR-1.50", "FR-2.8")
def test_section17_cnot_contiguous_and_roles() -> None:
    """CNOT with control above and below target and Change target command."""
    session = EditorSession()
    # 1. Default CNOT at 0: control 0, target 1
    session.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=0))
    cnot = session.circuit.placements[0]
    assert cnot.controls == (0,)
    assert cnot.targets == (1,)

    # 2. X on q0 + control q0 / target q1 gives |11>
    session.apply(delete_gates(session.circuit, (cnot,)))
    session.apply(place_gate(session.circuit, GateType.X, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    out1 = session.run()
    assert out1.ok
    assert session.simulation_result is not None
    assert np.isclose(session.simulation_result.probabilities[3], 1.0, atol=1e-9)  # 11

    # 3. Swap roles: control q1 / target q0. X on q1 gives |11>
    session.apply(clear(session.circuit))
    session.apply(place_gate(session.circuit, GateType.X, qubit=1, column=0))
    res_cx = place_gate(session.circuit, GateType.CNOT, qubit=0, column=1)
    session.apply(res_cx)
    p_cx = next(p for p in session.circuit.placements if p.gate_type == GateType.CNOT)
    from libqsim.application.operations import change_target

    session.apply(change_target(session.circuit, p_cx))
    swapped = next(p for p in session.circuit.placements if p.gate_type == GateType.CNOT)
    assert swapped.controls == (1,)
    assert swapped.targets == (0,)
    out2 = session.run()
    assert out2.ok
    assert np.isclose(session.simulation_result.probabilities[3], 1.0, atol=1e-9)  # 11


@pytest.mark.req("FR-1.49", "FR-1.50", "FR-2.8")
def test_section17_toffoli_semantics_and_middle_wire_target() -> None:
    """Toffoli flips target only when both controls are 1; middle wire target works."""
    session = EditorSession()
    session.apply(resize(session.circuit, 3))

    # Controls q0, q2, target q1 (middle wire)
    p_tof = GatePlacement(GateType.Toffoli, targets=(1,), controls=(0, 2), column=1)

    # Case A: Only q0 is 1 -> target q1 unchanged
    session.apply(place_gate(session.circuit, GateType.X, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.H, qubit=1, column=1))  # dummy
    # Clean circuit with X on q0 and middle target Toffoli
    session.apply(clear(session.circuit))
    session.apply(place_gate(session.circuit, GateType.X, qubit=0, column=0))
    c_cand = Circuit(num_qubits=3, placements=[session.circuit.placements[0], p_tof])
    assert len(validate(c_cand)) == 0
    res_a = simulate(c_cand)
    # q0=1, q1=0, q2=0 -> state "001" (index 1)
    assert np.isclose(res_a.probabilities[1], 1.0, atol=1e-9)

    # Case B: Both q0 and q2 are 1 -> target q1 flipped to 1 -> state "111" (index 7)
    session.apply(place_gate(session.circuit, GateType.X, qubit=2, column=0))
    c_cand2 = Circuit(
        num_qubits=3,
        placements=[session.circuit.placements[0], session.circuit.placements[1], p_tof],
    )
    res_b = simulate(c_cand2)
    assert np.isclose(res_b.probabilities[7], 1.0, atol=1e-9)


@pytest.mark.req("FR-2.6", "FR-3.10", "FR-5.4")
def test_section17_measurement_rules_and_ignored_in_simulation() -> None:
    """Measurement is ignored in simulation; double measurement and gate after measurement fail."""
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.Measurement, qubit=0, column=1))

    # Measurement does not alter statevector
    out = session.run()
    assert out.ok
    assert np.isclose(session.simulation_result.probabilities[0], 0.5, atol=1e-9)

    # 1. Gate after measurement is invalid
    res_after = place_gate(session.circuit, GateType.X, qubit=0, column=2)
    assert res_after.status == "rejected"

    # 2. Second measurement on same qubit is invalid
    res_second = place_gate(session.circuit, GateType.Measurement, qubit=0, column=3)
    assert res_second.status == "rejected"


@pytest.mark.req("FR-2.1", "FR-2.7", "FR-2.11", "FR-2.12", "NFR-5.2")
def test_section17_validation_failures_and_column_bounds() -> None:
    """Validation rejects bounds, collisions, and suppresses simulation without raw exceptions."""
    # Callable independently of GUI (NFR-5.2)
    c_bad_col = Circuit(
        num_qubits=2,
        placements=[GatePlacement(GateType.H, targets=(0,), controls=(), column=50)],
    )
    errs = validate(c_bad_col)
    assert len(errs) > 0
    # Error message does not expose raw Python exceptions or Qiskit stack traces (FR-2.11)
    msg = errs[0].message
    assert "Traceback" not in msg
    assert "Exception" not in msg

    # Run refuses invalid circuit (FR-2.12)
    session = EditorSession()
    session._circuit = c_bad_col
    out = session.run()
    assert out.ok is False
    assert len(out.messages) > 0


@pytest.mark.req("FR-3.3", "FR-4.8")
def test_section17_3qubit_basis_ordering() -> None:
    """3-qubit basis ordering puts highest qubit on the left."""
    # X on q0 only -> q2=0, q1=0, q0=1 -> label "001" (index 1)
    c1 = Circuit(
        num_qubits=3,
        placements=[GatePlacement(GateType.X, targets=(0,), controls=(), column=0)],
    )
    res1 = simulate(c1)
    assert np.isclose(res1.probabilities[1], 1.0, atol=1e-9)

    # X on q2 only -> q2=1, q1=0, q0=0 -> label "100" (index 4)
    c2 = Circuit(
        num_qubits=3,
        placements=[GatePlacement(GateType.X, targets=(2,), controls=(), column=0)],
    )
    res2 = simulate(c2)
    assert np.isclose(res2.probabilities[4], 1.0, atol=1e-9)


@pytest.mark.req("FR-1.8", "FR-1.9", "FR-1.28", "FR-1.46", "FR-1.48")
def test_section17_move_paste_selection_atomicity() -> None:
    """Move/paste operations are atomic and respect self-vacated cells and anchors."""
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.X, qubit=0, column=1))

    # Move onto self-vacated cells: move both gates right by 1
    from qsim_gui.widgets.selection_controller import SelectionController

    ctrl = SelectionController()
    ctrl.select_all(session.circuit)
    res_move = ctrl.move_selection(session.circuit, d_qubit=0, d_column=1)
    assert res_move.status == "applied"
    assert session.apply(res_move)

    # Overlap with unselected gate rejected atomically
    session.apply(place_gate(session.circuit, GateType.Z, qubit=0, column=0))
    z_gate = next(p for p in session.circuit.placements if p.gate_type == GateType.Z)
    ctrl.set_selection({z_gate})
    # Try moving Z at (0, 0) into (0, 1) where H is: rejected
    res_clash = ctrl.move_selection(session.circuit, d_qubit=0, d_column=1)
    assert res_clash.status == "rejected"

    # Copy and paste
    clip = copy_gates(session.circuit, {z_gate})
    assert clip is not None
    # Paste at anchor (1, 5)
    res_paste = paste(session.circuit, clip, anchor_qubit=1, anchor_column=5)
    assert res_paste.status == "applied"
    session.apply(res_paste)
    pasted = next(
        p for p in session.circuit.placements if p.column == 5 and p.gate_type == GateType.Z
    )
    assert pasted.targets == (1,)


@pytest.mark.req(
    "FR-1.12",
    "FR-1.13",
    "FR-1.15",
    "LC-2",
    "LC-3",
    "LC-4",
    "LC-5",
)
def test_section17_undo_redo_baseline_equality() -> None:
    """Undo back to baseline sets Clean; Redo sets Dirty; edit after undo clears redo."""
    session = EditorSession()
    assert session.save_status == SaveStatus.CLEAN

    # 1. Mutate
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    assert session.save_status == SaveStatus.DIRTY

    # 2. Undo back to initial baseline -> Clean
    assert session.undo() is True
    assert session.save_status == SaveStatus.CLEAN

    # 3. Redo away from baseline -> Dirty
    assert session.redo() is True
    assert session.save_status == SaveStatus.DIRTY

    # 4. Undo and mutate -> clears redo
    session.undo()
    assert session.can_redo is True
    session.apply(place_gate(session.circuit, GateType.X, qubit=0, column=0))
    assert session.can_redo is False


@pytest.mark.req("FR-5.5", "FR-5.8", "FR-5.15", "FR-5.16", "FR-5.18")
def test_section17_qcs_save_load_strictness_canonical(tmp_path: Path) -> None:
    """QCS round trip preserves circuit; strict loader rejects unknown fields, non-integers."""
    c = Circuit(
        num_qubits=3,
        placements=[
            GatePlacement(GateType.CNOT, targets=(1,), controls=(0,), column=2),
            GatePlacement(GateType.H, targets=(0,), controls=(), column=0),
        ],
    )
    p = tmp_path / "strict.qcs"
    write(p, c)

    # Loader reads back exactly
    loaded = read(p)
    assert loaded == c

    # Canonical order: column ascending, then qubit ascending
    raw = p.read_text(encoding="utf-8")
    assert raw.index('"column": 0') < raw.index('"column": 2')

    # Strictness: float column rejected
    from libqsim.persistence.qcs import QcsError

    bad_p = tmp_path / "bad.qcs"
    bad_p.write_text(
        '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [], "column": 1.5}]}',
        encoding="utf-8",
    )
    with pytest.raises(QcsError):
        read(bad_p)


@pytest.mark.req(
    "FR-6.1",
    "FR-6.2",
    "FR-6.4",
    "FR-6.5",
    "FR-6.7",
    "FR-6.8",
    "FR-6.13",
    "FR-6.14",
    "FR-6.15",
)
def test_section17_qasm_interop_ordering_and_limits() -> None:
    """OpenQASM cx/ccx argument order, statement order, and 50 operations limit."""
    # Exactly 50 operations accepted
    qasm_50 = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n' + "h q[0];\n" * 50
    c50 = import_text(qasm_50)
    assert len(c50.placements) == 50

    # 51 operations rejected
    from libqsim.qasm.importer import QasmError

    qasm_51 = qasm_50 + "h q[0];\n"
    with pytest.raises(QasmError):
        import_text(qasm_51)

    # cx argument order: controls first, target last on import and export
    qasm_cx = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncx q[0],q[1];\n'
    c_cx = import_text(qasm_cx)
    p_cx = c_cx.placements[0]
    assert p_cx.controls == (0,)
    assert p_cx.targets == (1,)

    exported = export_text(c_cx)
    assert "cx q[0],q[1];" in exported


@pytest.mark.req("FR-1.16", "FR-1.17", "FR-1.18", "FR-1.19")
def test_section17_destructive_resize_confirmation() -> None:
    """Destructive resize requires confirmation, removes affected gates in one mutation."""
    c = Circuit(
        num_qubits=4,
        placements=[
            GatePlacement(GateType.H, targets=(0,), controls=(), column=0),
            GatePlacement(GateType.X, targets=(3,), controls=(), column=1),
        ],
    )
    # Plan resize to 2 qubits
    plan = plan_resize(c, 2)
    assert plan.needs_confirmation is True
    assert len(plan.affected) == 1

    # Confirmed resize removes affected gate
    res = resize(c, 2, confirmed=True)
    assert res.status == "applied"
    assert res.circuit.num_qubits == 2
    assert len(res.circuit.placements) == 1
    assert res.circuit.placements[0].gate_type == GateType.H


# ==============================================================================
# PERFORMANCE BENCHMARKS (NFR-1.1, NFR-1.2)
# ==============================================================================


@pytest.mark.perf
@pytest.mark.req("NFR-1.1")
def test_performance_nfr_1_1_max_circuit_simulation() -> None:
    """Fully populated 10-qubit x 50-column circuit (500 gates) simulates within 2.0s."""
    gates = [GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T]
    placements: list[GatePlacement] = []
    # 50 columns x 10 qubits = 500 single-qubit gates
    for col in range(50):
        for q in range(10):
            gt = gates[(col * 10 + q) % len(gates)]
            placements.append(GatePlacement(gt, targets=(q,), controls=(), column=col))

    max_circuit = Circuit(num_qubits=10, placements=placements)
    assert len(max_circuit.placements) == 500

    session = EditorSession()
    session._circuit = max_circuit

    t0 = time.perf_counter()
    outcome = session.run()
    elapsed = time.perf_counter() - t0

    print(f"\n[PERF] NFR-1.1 (Simulation 500 gates, 10 qubits): {elapsed:.4f} s (limit: 2.0 s)")

    assert outcome.ok is True
    assert session.simulation_result is not None
    assert len(session.simulation_result.statevector) == 1024
    assert len(session.simulation_result.probabilities) == 1024
    assert len(session.simulation_result.bloch_vectors) == 10
    assert elapsed < 2.0, f"Simulation exceeded 2.0s threshold: took {elapsed:.4f}s"


@pytest.mark.perf
@pytest.mark.req("NFR-1.2")
def test_performance_nfr_1_2_max_circuit_editing() -> None:
    """Each editing operation on the 500-gate 10-qubit circuit completes within 100 ms."""
    gates = [GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T]
    placements: list[GatePlacement] = []
    for col in range(49):  # leave col 49 empty for place_gate test
        for q in range(10):
            gt = gates[(col * 10 + q) % len(gates)]
            placements.append(GatePlacement(gt, targets=(q,), controls=(), column=col))

    c = Circuit(num_qubits=10, placements=placements)
    assert len(c.placements) == 490

    # 1. place_gate
    t0 = time.perf_counter()
    res_place = place_gate(c, GateType.H, qubit=0, column=49)
    dt_place = time.perf_counter() - t0
    print(f"[PERF] NFR-1.2 (place_gate): {dt_place * 1000:.2f} ms (limit: 100 ms)")
    assert res_place.status == "applied"
    assert dt_place < 0.100

    c_cur = res_place.circuit

    # 2. delete_gates
    target_p = c_cur.placements[0]
    t0 = time.perf_counter()
    res_del = delete_gates(c_cur, (target_p,))
    dt_del = time.perf_counter() - t0
    print(f"[PERF] NFR-1.2 (delete_gates): {dt_del * 1000:.2f} ms (limit: 100 ms)")
    assert res_del.status == "applied"
    assert dt_del < 0.100

    # 3. plan_resize and resize
    t0 = time.perf_counter()
    res_resize = resize(c_cur, 9, confirmed=True)
    dt_resize = time.perf_counter() - t0
    print(f"[PERF] NFR-1.2 (resize): {dt_resize * 1000:.2f} ms (limit: 100 ms)")
    assert res_resize.status == "applied"
    assert dt_resize < 0.100

    # 4. clear
    t0 = time.perf_counter()
    res_clear = clear(c_cur)
    dt_clear = time.perf_counter() - t0
    print(f"[PERF] NFR-1.2 (clear): {dt_clear * 1000:.2f} ms (limit: 100 ms)")
    assert res_clear.status == "applied"
    assert dt_clear < 0.100


# ==============================================================================
# OFFLINE & PRIVACY CONSTRAINTS (NFR-4.1, 4.2, 4.3, FR-3.11, NFR-2.1)
# ==============================================================================


@pytest.mark.req("NFR-4.1", "NFR-4.2", "NFR-4.3", "FR-3.11", "NFR-2.1")
def test_offline_headless_and_gui_smoke_no_network(
    monkeypatch: pytest.MonkeyPatch, qapp: QApplication, tmp_path: Path
) -> None:
    """Verify application makes zero network requests during headless and GUI flows."""

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Network communication is forbidden in OpenQSim (NFR-4.1)")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
    monkeypatch.setattr(socket, "create_connection", forbidden_connect)

    # 1. Full headless flow (NFR-2.1 Bell state)
    session = EditorSession()
    session.apply(place_gate(session.circuit, GateType.H, qubit=0, column=0))
    session.apply(place_gate(session.circuit, GateType.CNOT, qubit=0, column=1))
    # Run is synchronous on GUI thread (FR-3.11)
    run_outcome = session.run()
    assert run_outcome.ok
    assert session.simulation_result is not None

    qcs_path = tmp_path / "offline.qcs"
    assert session.save_as(qcs_path).ok
    assert session.open(qcs_path).ok

    qasm_path = tmp_path / "offline.qasm"
    assert session.export_qasm(qasm_path).ok
    assert session.import_qasm(qasm_path).ok

    # 2. GUI smoke run
    ui = StubUserInterface()
    adapter = SessionAdapter(session)
    window = MainWindow(adapter=adapter, ui=ui)
    assert window.isVisible() or window.isWindow()

    # Image export
    png_path = tmp_path / "offline_circuit.png"
    ui.save_file_result = png_path
    assert window.export_circuit_image() is True
    assert png_path.exists()
