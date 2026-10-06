"""QCS file format persistence for OpenQSim circuits."""

import json
import os
from pathlib import Path

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import validate

__all__ = ["QcsError", "dumps", "loads", "read", "write"]


class QcsError(Exception):
    """Raised when QCS parsing, schema validation, or file IO fails."""


def dumps(circuit: Circuit) -> str:
    """Serialize a Circuit to canonical QCS JSON string.

    Placements are ordered by column, then lowest occupied qubit, with controls ascending.
    """
    gate_list: list[dict[str, object]] = []
    for p in circuit.canonical_placements():
        gate_list.append(
            {
                "gate_type": p.gate_type.value,
                "targets": list(p.targets),
                "controls": sorted(p.controls),
                "column": p.column,
            }
        )

    root = {
        "schema_version": "1.0",
        "num_qubits": circuit.num_qubits,
        "gates": gate_list,
    }
    return json.dumps(root, indent=2) + "\n"


def loads(text: str) -> Circuit:
    """Parse and validate a QCS JSON string into a Circuit.

    Strictly validates types, keys, gate definitions, and domain rules.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError, UnicodeDecodeError) as exc:
        raise QcsError(f"Invalid JSON in QCS data: {exc}") from exc

    if not isinstance(data, dict):
        raise QcsError("Root value of QCS file must be a JSON object")

    root_keys = set(data.keys())
    required_keys = {"schema_version", "num_qubits", "gates"}
    missing = required_keys - root_keys
    if missing:
        raise QcsError(f"Missing required field in QCS root: {', '.join(sorted(missing))}")
    unknown = root_keys - required_keys
    if unknown:
        raise QcsError(f"Unknown field in QCS root: {', '.join(sorted(unknown))}")

    sv = data["schema_version"]
    if not isinstance(sv, str) or sv != "1.0":
        raise QcsError(f"Unsupported schema_version: {sv!r}. Expected exact string '1.0'")

    nq = data["num_qubits"]
    if not isinstance(nq, int) or isinstance(nq, bool):
        raise QcsError(f"num_qubits must be an integer, got {type(nq).__name__}")

    raw_gates = data["gates"]
    if not isinstance(raw_gates, list):
        raise QcsError(f"gates must be a list, got {type(raw_gates).__name__}")

    req_gate_keys = {"gate_type", "targets", "controls", "column"}
    placements: list[GatePlacement] = []

    for idx, gate_obj in enumerate(raw_gates):
        if not isinstance(gate_obj, dict):
            raise QcsError(f"Gate placement at index {idx} must be a JSON object")

        gate_keys = set(gate_obj.keys())
        missing_gate_keys = req_gate_keys - gate_keys
        if missing_gate_keys:
            raise QcsError(
                f"Missing field in gate placement {idx}: {', '.join(sorted(missing_gate_keys))}"
            )
        unknown_gate_keys = gate_keys - req_gate_keys
        if unknown_gate_keys:
            raise QcsError(
                f"Unknown field in gate placement {idx}: {', '.join(sorted(unknown_gate_keys))}"
            )

        gt_raw = gate_obj["gate_type"]
        if not isinstance(gt_raw, str):
            raise QcsError(f"gate_type in placement {idx} must be a string")
        try:
            gate_type = GateType(gt_raw)
        except ValueError:
            raise QcsError(f"Unknown gate_type: {gt_raw!r} in placement {idx}") from None

        col = gate_obj["column"]
        if not isinstance(col, int) or isinstance(col, bool):
            raise QcsError(f"column in placement {idx} must be an integer")

        targets_raw = gate_obj["targets"]
        if not isinstance(targets_raw, list):
            raise QcsError(f"targets in placement {idx} must be a list")
        for t in targets_raw:
            if not isinstance(t, int) or isinstance(t, bool):
                raise QcsError(f"target qubit index in placement {idx} must be an integer")

        controls_raw = gate_obj["controls"]
        if not isinstance(controls_raw, list):
            raise QcsError(f"controls in placement {idx} must be a list")
        for c in controls_raw:
            if not isinstance(c, int) or isinstance(c, bool):
                raise QcsError(f"control qubit index in placement {idx} must be an integer")

        # Validate gate arity and targets/controls counts
        if len(targets_raw) != 1:
            raise QcsError(
                f"Gate {gate_type.value} at index {idx} must have exactly 1 target, "
                f"got {len(targets_raw)}"
            )

        expected_controls = {
            GateType.H: 0,
            GateType.X: 0,
            GateType.Y: 0,
            GateType.Z: 0,
            GateType.S: 0,
            GateType.T: 0,
            GateType.Measurement: 0,
            GateType.CNOT: 1,
            GateType.Toffoli: 2,
        }[gate_type]

        if len(controls_raw) != expected_controls:
            raise QcsError(
                f"Gate {gate_type.value} at index {idx} must have {expected_controls} controls, "
                f"got {len(controls_raw)}"
            )

        placements.append(
            GatePlacement(
                gate_type=gate_type,
                targets=targets_raw,
                controls=controls_raw,
                column=col,
            )
        )

    circuit = Circuit(num_qubits=nq, placements=placements)
    errors = validate(circuit)
    if errors:
        msg = "; ".join(e.message for e in errors)
        raise QcsError(f"Circuit validation failed: {msg}")

    return circuit


def write(path: Path | str, circuit: Circuit) -> None:
    """Write a Circuit atomically to a QCS file."""
    p = Path(path)
    text = dumps(circuit)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        temp_file = p.parent / f".tmp_{p.name}_{os.getpid()}"
        temp_file.write_text(text, encoding="utf-8")
        temp_file.replace(p)
    except OSError as exc:
        msg = exc.strerror if exc.strerror else str(exc)
        raise QcsError(f"Failed to write file '{p.name}': {msg}") from exc


def read(path: Path | str) -> Circuit:
    """Read and validate a Circuit from a QCS file."""
    p = Path(path)
    try:
        if p.is_dir():
            raise QcsError(f"Cannot read '{p.name}': path is a directory")
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise QcsError(f"File not found: '{p.name}'") from exc
    except OSError as exc:
        msg = exc.strerror if exc.strerror else str(exc)
        raise QcsError(f"Failed to read file '{p.name}': {msg}") from exc
    return loads(text)
