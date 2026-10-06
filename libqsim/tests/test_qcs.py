"""Unit, round-trip, strictness, and property tests for QCS persistence."""

import json
import os
import random
from pathlib import Path

import pytest
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.persistence.qcs import QcsError, dumps, loads, read, write


@pytest.mark.req("FR-5.1", "FR-5.2", "FR-5.3", "FR-5.4", "FR-5.5", "FR-5.6", "NFR-5.3", "NFR-7.5")
def test_qcs_roundtrip_handbuilt_and_seeded() -> None:
    # Hand-built circuit
    gates = [
        GatePlacement(GateType.H, [0], [], 0),
        GatePlacement(GateType.CNOT, [1], [0], 1),
        GatePlacement(GateType.Measurement, [0], [], 2),
    ]
    c1 = Circuit(3, gates)
    dumped = dumps(c1)
    assert '"schema_version": "1.0"' in dumped
    assert "simulation" not in dumped.lower()
    assert "statevector" not in dumped.lower()
    assert "probabilities" not in dumped.lower()
    loaded = loads(dumped)
    assert loaded == c1
    assert dumps(loaded) == dumped

    # 50 seeded random valid circuits
    rng = random.Random(42)
    single_gates = [GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T]

    for _ in range(50):
        num_qubits = rng.randint(2, 5)
        placements: list[GatePlacement] = []
        occupied: set[tuple[int, int]] = set()

        for col in range(5):
            q = rng.randint(0, num_qubits - 1)
            if (q, col) not in occupied:
                gt = rng.choice(single_gates)
                placements.append(GatePlacement(gt, [q], [], col))
                occupied.add((q, col))

        c = Circuit(num_qubits, placements)
        d = dumps(c)
        l = loads(d)
        assert l == c
        assert dumps(l) == d


@pytest.mark.req("FR-5.18")
def test_qcs_canonical_output() -> None:
    # Placements out of order and controls out of order
    p1 = GatePlacement(GateType.Toffoli, [2], [1, 0], 3)
    p2 = GatePlacement(GateType.H, [0], [], 0)
    p3 = GatePlacement(GateType.X, [1], [], 0)

    c_shuffled = Circuit(3, [p1, p3, p2])
    c_ordered = Circuit(3, [p2, p3, GatePlacement(GateType.Toffoli, [2], [0, 1], 3)])

    assert dumps(c_shuffled) == dumps(c_ordered)


@pytest.mark.req("FR-5.4", "FR-5.17")
def test_qcs_toffoli_example_from_doc() -> None:
    doc_json = """{
  "schema_version": "1.0",
  "num_qubits": 3,
  "gates": [
    {
      "gate_type": "Toffoli",
      "targets": [1],
      "controls": [0, 2],
      "column": 3
    }
  ]
}
"""
    c = loads(doc_json)
    assert c.num_qubits == 3
    assert len(c.placements) == 1
    p = c.placements[0]
    assert p.gate_type == GateType.Toffoli
    assert p.targets == (1,)
    assert p.controls == (0, 2)
    assert p.column == 3


@pytest.mark.req("FR-5.8", "FR-5.9", "FR-5.15", "FR-5.16", "FR-5.17", "NFR-3.1")
@pytest.mark.parametrize(
    ("bad_input", "error_match"),
    [
        ("not json", "JSON"),
        ("[]", "object"),
        ('"string root"', "object"),
        ('{"num_qubits": 2, "gates": []}', "schema_version"),
        ('{"schema_version": "1.0", "gates": []}', "num_qubits"),
        ('{"schema_version": "1.0", "num_qubits": 2}', "gates"),
        ('{"schema_version": "1.0", "num_qubits": 2, "gates": [], "extra": 1}', "Unknown field"),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [], "column": 0, "foo": 1}]}',
            "Unknown field",
        ),
        ('{"schema_version": "1.0", "num_qubits": 2.0, "gates": []}', "integer"),
        ('{"schema_version": "1.0", "num_qubits": true, "gates": []}', "integer"),
        ('{"schema_version": "1.0", "num_qubits": "2", "gates": []}', "integer"),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [], "column": 1.5}]}',
            "integer",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [], "column": false}]}',
            "integer",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0.0], "controls": [], "column": 0}]}',
            "integer",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [true], "controls": [], "column": 0}]}',
            "integer",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "CNOT", "targets": [1], "controls": [0.0], "column": 0}]}',
            "integer",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": 0, "controls": [], "column": 0}]}',
            "list",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": 0, "column": 0}]}',
            "list",
        ),
        ('{"schema_version": "1.0", "num_qubits": 2, "gates": "not_list"}', "list"),
        ('{"schema_version": "2.0", "num_qubits": 2, "gates": []}', "schema_version"),
        ('{"schema_version": 1.0, "num_qubits": 2, "gates": []}', "schema_version"),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "h", "targets": [0], "controls": [], "column": 0}]}',
            "gate_type",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "UNKNOWN", "targets": [0], "controls": [], "column": 0}]}',
            "gate_type",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [], "controls": [], "column": 0}]}',
            "target",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0, 1], "controls": [], "column": 0}]}',
            "target",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [1], "column": 0}]}',
            "control",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "CNOT", "targets": [1], "controls": [], "column": 0}]}',
            "control",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 3, "gates": [{"gate_type": "Toffoli", "targets": [2], "controls": [0], "column": 0}]}',
            "control",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [0], "controls": [], "column": 55}]}',
            "column",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "H", "targets": [5], "controls": [], "column": 0}]}',
            "qubit",
        ),
        (
            '{"schema_version": "1.0", "num_qubits": 2, "gates": [{"gate_type": "CNOT", "targets": [0], "controls": [0], "column": 0}]}',
            "qubit",
        ),
    ],
)
def test_qcs_rejections(bad_input: str, error_match: str) -> None:
    with pytest.raises(QcsError) as exc_info:
        loads(bad_input)
    assert error_match.lower() in str(exc_info.value).lower()


@pytest.mark.req("FR-5.8", "NFR-3.1")
def test_qcs_recursion_error_rejected() -> None:
    # Deeply nested JSON
    deep_json = "[" * 2000 + "]" * 2000
    with pytest.raises(QcsError):
        loads(deep_json)


@pytest.mark.req("FR-5.8", "NFR-3.1")
def test_qcs_fuzz_random_garbage() -> None:
    rng = random.Random(1337)
    for _ in range(100):
        # Generate random text
        length = rng.randint(1, 100)
        garbage = "".join(chr(rng.randint(0, 127)) for _ in range(length))
        with pytest.raises(QcsError):
            loads(garbage)

    # Generate random json values
    primitives: list[object] = [None, True, False, 1, 2.5, "test", [], {}]
    for _ in range(50):
        val = rng.choice(primitives)
        with pytest.raises(QcsError):
            loads(json.dumps(val))


@pytest.mark.req("FR-5.1", "FR-5.10", "NFR-3.3")
def test_qcs_atomic_file_operations(tmp_path: Path) -> None:
    c = Circuit(2, [GatePlacement(GateType.H, [0], [], 0)])
    target_path = tmp_path / "valid.qcs"

    # Write and read
    write(target_path, c)
    assert target_path.exists()
    loaded = read(target_path)
    assert loaded == c

    # Read missing file
    with pytest.raises(QcsError) as exc1:
        read(tmp_path / "missing.qcs")
    assert "not found" in str(exc1.value).lower() or "missing" in str(exc1.value).lower()

    # Read directory
    with pytest.raises(QcsError):
        read(tmp_path)

    # Write to read-only directory
    ro_dir = tmp_path / "readonly_dir"
    ro_dir.mkdir()
    ro_file = ro_dir / "target.qcs"
    write(ro_file, c)
    original_mtime = ro_file.stat().st_mtime

    os.chmod(ro_dir, 0o555)
    try:
        new_c = Circuit(3)
        with pytest.raises(QcsError):
            write(ro_file, new_c)
        # Original file intact
        assert ro_file.stat().st_mtime == original_mtime
        assert read(ro_file) == c
    finally:
        os.chmod(ro_dir, 0o755)
