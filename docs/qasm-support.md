# OpenQASM 2.0 Support

## Overview

OpenQSim supports a deliberately limited subset of OpenQASM 2.0 for import and
export.

OpenQASM is the supported interchange format. Qiskit Python source code is not
imported or exported.

## Supported Header

The importer accepts:

```qasm
OPENQASM 2.0;
include "qelib1.inc";
```

Both header lines are required. `//` comments are ignored and whitespace is
not significant. Gate names are lowercase.

## Registers

The supported subset allows:

- one quantum register, named `q` (`qreg q[n];`, 1 to 10 qubits);
- zero or one classical register.

A classical register declared when no Measurement is present is accepted and
ignored; it is not preserved on export.

When Measurement is present:

- the classical register must be named `c`;
- it must contain exactly `n` bits;
- measurements must map one-to-one as `q[i] -> c[i]`.

## Supported Operations

The supported gate operations are:

```qasm
h q[i];
x q[i];
y q[i];
z q[i];
s q[i];
t q[i];

cx q[control],q[target];
ccx q[control1],q[control2],q[target];

measure q[i] -> c[i];
```

Argument order follows OpenQASM 2.0 and Qiskit: controls first, target last.

The circuit model convention is:

- CNOT occupies two contiguous qubit wires;
- Toffoli occupies three contiguous qubit wires;
- exactly one occupied wire is the target and may be any of them; the other
  occupied wires are controls;
- all operands are explicit single-qubit references such as `q[i]`.

For example, `cx q[1],q[0];` is a CNOT with control q1 and target q0, and
`ccx q[0],q[2],q[1];` is a Toffoli whose target is the middle wire.

On import, `ccx` controls may appear in either order; they are stored in
ascending order. On export, controls are written in ascending order, then the
target.

## Import

The importer validates the supported OpenQASM subset before constructing the
circuit.

Each OpenQASM operation is placed in the next editor column:

```text
statement 1 -> column 0
statement 2 -> column 1
statement 3 -> column 2
...
```

Therefore exact editor column positions are determined by QASM statement
order.

The application always edits a `.qcs` session, never a raw `.qasm` file. A
successful import replaces the current session with a new unsaved `.qcs`
session: no file path, Save status `Dirty`, no simulation result, and empty
undo/redo history. If Save status is `Dirty` before the import, the user is
first offered `Save`, `Don't Save`, and `Cancel`.

The importer must reject unsupported or invalid constructs instead of
silently ignoring them.

## Rejected Constructs

The importer rejects constructs including:

```text
sdg
tdg
rotation gates
custom gate definitions
if
reset
barrier
opaque
multiple quantum-register declarations
unsupported classical operations
unsupported gate arguments
whole-register operands (for example `h q;`)
repeated, out-of-range, or non-contiguous cx/ccx operands
a quantum register not named q
missing include "qelib1.inc"
more than 10 qubits
second Measurement on one qubit
Measurement before another operation on the same qubit
invalid Measurement/classical-register mapping
more than 50 imported operations
```

A failed import must leave the existing application state unchanged.

## Export

Export produces OpenQASM 2.0 for the supported circuit subset.

Every export begins with:

```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[n];
```

followed by `creg c[n];` only when at least one Measurement exists, then the
operations.

Operations are written in:

1. increasing editor-column order;
2. within one column, increasing lowest-indexed occupied qubit.

Exact editor column positions do not need to survive an import/export round
trip.

Execution order and supported gate semantics must be preserved.

## Measurement Export

When at least one Measurement exists, export uses exactly one classical
register:

```qasm
creg c[n];
```

Each Measurement is exported as:

```qasm
measure q[i] -> c[i];
```

Measurement is required to remain the final operation on the measured qubit.

## Ordering Example

For a circuit containing:

```text
column 0: H on q1
column 0: X on q0
column 1: CNOT, control q0, target q1
```

the exporter orders the same-column operations by their lowest occupied qubit:

```qasm
x q[0];
h q[1];
cx q[0],q[1];
```

The important property is deterministic ordering, not preservation of the
original textual arrangement.

## Scope

OpenQASM 3, arbitrary-angle rotation gates, custom gates, classical control
flow, reset, barriers, and Qiskit Python source import/export are outside the
release scope.
