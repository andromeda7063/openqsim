"""OpenQASM 2.0 subset parser and importer."""

import re

from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import validate

__all__ = ["QasmError", "import_text"]


class QasmError(Exception):
    """Raised when OpenQASM 2.0 syntax, subset, or semantic validation fails."""


def _tokenize_statements(text: str) -> list[tuple[str, int]]:
    """Split text into (statement, line_number) tuples, stripping // comments."""
    statements: list[tuple[str, int]] = []
    current_chars: list[str] = []
    start_line: int = 1
    in_statement: bool = False

    lines = text.splitlines(keepends=True)
    for line_idx, line in enumerate(lines, start=1):
        # Strip // comments
        code_part = line.split("//", 1)[0]
        clean_code = code_part.strip()
        if clean_code.startswith("gate "):
            raise QasmError(f"Line {line_idx}: Custom gate definitions ('gate') are not supported")
        if clean_code.startswith("opaque "):
            raise QasmError(f"Line {line_idx}: 'opaque' definitions are not supported")

        for char in code_part:
            if char == ";":
                current_chars.append(";")
                stmt_str = "".join(current_chars).strip()
                if stmt_str:
                    statements.append((stmt_str, start_line))
                current_chars = []
                in_statement = False
            else:
                if not in_statement and not char.isspace():
                    in_statement = True
                    start_line = line_idx
                if in_statement:
                    current_chars.append(char)

    remaining = "".join(current_chars).strip()
    if remaining:
        if remaining.startswith("gate "):
            raise QasmError(
                f"Line {start_line}: Custom gate definitions ('gate') are not supported"
            )
        if remaining.startswith("opaque "):
            raise QasmError(f"Line {start_line}: 'opaque' definitions are not supported")
        raise QasmError(f"Line {start_line}: Syntax error: statement missing terminating semicolon")

    return statements


def import_text(text: str) -> Circuit:
    """Parse and validate an OpenQASM 2.0 string into a Circuit."""
    statements = _tokenize_statements(text)
    if not statements:
        raise QasmError("Line 1: Empty OpenQASM file")

    # Header check: statement 1 must be OPENQASM 2.0;
    stmt1, line1 = statements[0]
    stmt1_clean = " ".join(stmt1[:-1].split())
    if stmt1_clean != "OPENQASM 2.0":
        raise QasmError(f"Line {line1}: Expected 'OPENQASM 2.0;', got '{stmt1}'")

    if len(statements) < 2:
        raise QasmError(f"Line {line1}: Missing include 'qelib1.inc';")

    stmt2, line2 = statements[1]
    stmt2_clean = " ".join(stmt2[:-1].split())
    if stmt2_clean not in ('include "qelib1.inc"', "include 'qelib1.inc'"):
        raise QasmError(f"Line {line2}: Expected 'include \"qelib1.inc\";', got '{stmt2}'")

    num_qubits: int | None = None
    creg_name: str | None = None
    creg_size: int | None = None
    creg_line: int | None = None
    placements: list[GatePlacement] = []
    measured_qubits: set[int] = set()

    single_qubit_gates = {
        "h": GateType.H,
        "x": GateType.X,
        "y": GateType.Y,
        "z": GateType.Z,
        "s": GateType.S,
        "t": GateType.T,
    }

    op_index = 0

    for stmt_raw, line_num in statements[2:]:
        content = stmt_raw[:-1].strip()  # strip trailing ';'
        if not content:
            continue

        parts = content.split(None, 1)
        command = parts[0]
        arg_str = parts[1].strip() if len(parts) > 1 else ""

        # Check unsupported constructs
        lower_cmd = command.lower()
        if lower_cmd in ("sdg", "tdg"):
            raise QasmError(f"Line {line_num}: Unsupported gate '{command}'")
        if lower_cmd in ("rx", "ry", "rz", "u1", "u2", "u3") or lower_cmd.startswith(
            ("rx(", "ry(", "rz(", "u1(", "u2(", "u3(")
        ):
            raise QasmError(f"Line {line_num}: Unsupported rotation gate '{command}'")
        if lower_cmd == "gate":
            raise QasmError(f"Line {line_num}: Custom gate definitions are not supported")
        if lower_cmd == "if":
            raise QasmError(f"Line {line_num}: Conditional 'if' statements are not supported")
        if lower_cmd == "barrier":
            raise QasmError(f"Line {line_num}: 'barrier' is not supported")
        if lower_cmd == "reset":
            raise QasmError(f"Line {line_num}: 'reset' is not supported")
        if lower_cmd == "opaque":
            raise QasmError(f"Line {line_num}: 'opaque' is not supported")

        # Registers
        if command == "qreg":
            if num_qubits is not None:
                raise QasmError(f"Line {line_num}: Second qreg declaration is not supported")
            m = re.fullmatch(r"([a-zA-Z0-9_]+)\[(\d+)\]", arg_str)
            if not m:
                raise QasmError(f"Line {line_num}: Invalid qreg syntax '{content}'")
            name, size_str = m.group(1), m.group(2)
            if name != "q":
                raise QasmError(
                    f"Line {line_num}: Quantum register must be named 'q', got '{name}'"
                )
            size = int(size_str)
            if size < 1 or size > 10:
                raise QasmError(
                    f"Line {line_num}: Quantum register (qreg) must have 1 to 10 qubits, got {size}"
                )
            num_qubits = size
            continue

        if command == "creg":
            if creg_name is not None:
                raise QasmError(f"Line {line_num}: Second creg declaration is not supported")
            m = re.fullmatch(r"([a-zA-Z0-9_]+)\[(\d+)\]", arg_str)
            if not m:
                raise QasmError(f"Line {line_num}: Invalid creg syntax '{content}'")
            creg_name = m.group(1)
            creg_size = int(m.group(2))
            creg_line = line_num
            continue

        # Operations
        if num_qubits is None:
            raise QasmError(f"Line {line_num}: Operation '{content}' before qreg declaration")

        # Check whole-register operand
        if re.search(r"\bq\b(?!\s*\[)", arg_str):
            raise QasmError(
                f"Line {line_num}: Whole-register operands are not supported: '{content}'"
            )

        if lower_cmd in single_qubit_gates:
            gt = single_qubit_gates[lower_cmd]
            m = re.fullmatch(r"q\[(\d+)\]", arg_str)
            if not m:
                raise QasmError(f"Line {line_num}: Invalid operand for '{command}': '{arg_str}'")
            q_idx = int(m.group(1))
            if q_idx >= num_qubits:
                raise QasmError(
                    f"Line {line_num}: Out-of-range qubit index q[{q_idx}] "
                    f"(register has {num_qubits} qubits)"
                )
            if q_idx in measured_qubits:
                raise QasmError(
                    f"Line {line_num}: Gate '{command}' placed on q[{q_idx}] after measurement"
                )

            placements.append(GatePlacement(gt, [q_idx], [], op_index))
            op_index += 1

        elif lower_cmd == "cx":
            args = [a.strip() for a in arg_str.split(",")]
            if len(args) != 2:
                raise QasmError(
                    f"Line {line_num}: 'cx' requires exactly 2 operands, got {len(args)}"
                )
            m1 = re.fullmatch(r"q\[(\d+)\]", args[0])
            m2 = re.fullmatch(r"q\[(\d+)\]", args[1])
            if not m1 or not m2:
                raise QasmError(f"Line {line_num}: Invalid operand in 'cx': '{arg_str}'")
            c_idx = int(m1.group(1))
            t_idx = int(m2.group(1))
            if c_idx >= num_qubits or t_idx >= num_qubits:
                raise QasmError(f"Line {line_num}: Out-of-range qubit index in 'cx'")
            if c_idx == t_idx:
                raise QasmError(f"Line {line_num}: Repeated operand in 'cx': q[{c_idx}]")
            if abs(c_idx - t_idx) != 1:
                raise QasmError(
                    f"Line {line_num}: Non-contiguous cx operands q[{c_idx}] and q[{t_idx}]"
                )
            if c_idx in measured_qubits or t_idx in measured_qubits:
                raise QasmError(f"Line {line_num}: 'cx' operation on wire after measurement")

            placements.append(GatePlacement(GateType.CNOT, [t_idx], [c_idx], op_index))
            op_index += 1

        elif lower_cmd == "ccx":
            args = [a.strip() for a in arg_str.split(",")]
            if len(args) != 3:
                raise QasmError(
                    f"Line {line_num}: 'ccx' requires exactly 3 operands, got {len(args)}"
                )
            m1 = re.fullmatch(r"q\[(\d+)\]", args[0])
            m2 = re.fullmatch(r"q\[(\d+)\]", args[1])
            m3 = re.fullmatch(r"q\[(\d+)\]", args[2])
            if not m1 or not m2 or not m3:
                raise QasmError(f"Line {line_num}: Invalid operand in 'ccx': '{arg_str}'")
            c1_idx = int(m1.group(1))
            c2_idx = int(m2.group(1))
            t_idx = int(m3.group(1))
            if c1_idx >= num_qubits or c2_idx >= num_qubits or t_idx >= num_qubits:
                raise QasmError(f"Line {line_num}: Out-of-range qubit index in 'ccx'")
            if len({c1_idx, c2_idx, t_idx}) != 3:
                raise QasmError(f"Line {line_num}: Repeated operand in 'ccx'")
            wires = sorted([c1_idx, c2_idx, t_idx])
            if wires != [wires[0], wires[0] + 1, wires[0] + 2]:
                raise QasmError(
                    f"Line {line_num}: Non-contiguous ccx operands q[{c1_idx}],q[{c2_idx}],q[{t_idx}]"
                )
            if any(w in measured_qubits for w in wires):
                raise QasmError(f"Line {line_num}: 'ccx' operation on wire after measurement")

            ctrls = sorted([c1_idx, c2_idx])
            placements.append(GatePlacement(GateType.Toffoli, [t_idx], ctrls, op_index))
            op_index += 1

        elif lower_cmd == "measure":
            # Syntax: measure q[i] -> c[j];
            m = re.fullmatch(r"q\[(\d+)\]\s*->\s*([a-zA-Z0-9_]+)\[(\d+)\]", arg_str)
            if not m:
                raise QasmError(f"Line {line_num}: Invalid measure syntax '{content}'")
            q_idx = int(m.group(1))
            target_creg = m.group(2)
            c_idx = int(m.group(3))

            if creg_name is None:
                raise QasmError(
                    f"Line {line_num}: Measurement requires a classical register named 'c'"
                )
            if creg_name != "c" or creg_size != num_qubits:
                err_line = creg_line if creg_line is not None else line_num
                raise QasmError(
                    f"Line {err_line}: Classical register must be named 'c' with size {num_qubits}, "
                    f"got '{creg_name}[{creg_size}]'"
                )
            if target_creg != "c" or q_idx != c_idx:
                raise QasmError(
                    f"Line {line_num}: Invalid measurement mapping q[{q_idx}] -> {target_creg}[{c_idx}], "
                    f"must map q[i] -> c[i]"
                )
            if q_idx >= num_qubits:
                raise QasmError(f"Line {line_num}: Out-of-range qubit index in 'measure'")
            if q_idx in measured_qubits:
                raise QasmError(f"Line {line_num}: Second measure on qubit q[{q_idx}]")

            measured_qubits.add(q_idx)
            placements.append(GatePlacement(GateType.Measurement, [q_idx], [], op_index))
            op_index += 1

        else:
            raise QasmError(f"Line {line_num}: Unsupported OpenQASM command '{command}'")

    if num_qubits is None:
        raise QasmError("Missing quantum register declaration")

    if len(placements) > 50:
        raise QasmError(
            f"Circuit operation count ({len(placements)}) exceeds 50-column import limit"
        )

    circuit = Circuit(num_qubits, placements)
    errors = validate(circuit)
    if errors:
        msg = "; ".join(e.message for e in errors)
        raise QasmError(f"Circuit validation failed: {msg}")

    return circuit
