"""OpenQASM 2.0 subset exporter."""

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit
from libqsim.domain.validation import validate
from libqsim.qasm.importer import QasmError

__all__ = ["export_text"]


def export_text(circuit: Circuit) -> str:
    """Serialize a Circuit to an OpenQASM 2.0 string."""
    errors = validate(circuit)
    if errors:
        msg = "; ".join(e.message for e in errors)
        raise QasmError(f"Cannot export invalid circuit: {msg}")

    lines: list[str] = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{circuit.num_qubits}];",
    ]

    has_measurement = any(p.gate_type == GateType.Measurement for p in circuit.placements)
    if has_measurement:
        lines.append(f"creg c[{circuit.num_qubits}];")

    for p in circuit.canonical_placements():
        gt = p.gate_type
        if gt in (
            GateType.H,
            GateType.X,
            GateType.Y,
            GateType.Z,
            GateType.S,
            GateType.T,
        ):
            lines.append(f"{gt.value.lower()} q[{p.targets[0]}];")
        elif gt == GateType.CNOT:
            lines.append(f"cx q[{p.controls[0]}],q[{p.targets[0]}];")
        elif gt == GateType.Toffoli:
            ctrls = sorted(p.controls)
            lines.append(f"ccx q[{ctrls[0]}],q[{ctrls[1]}],q[{p.targets[0]}];")
        elif gt == GateType.Measurement:
            lines.append(f"measure q[{p.targets[0]}] -> c[{p.targets[0]}];")

    return "\n".join(lines) + "\n"
