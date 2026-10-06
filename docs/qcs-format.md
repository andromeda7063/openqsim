# QCS Session File Format

## Overview

OpenQSim uses `.qcs` files to persist circuit definitions as JSON.

The format stores the circuit itself and its schema version. It does not store
simulation results.

The current schema version is:

```text
1.0
```

## Minimal Structure

A `.qcs` document contains at least:

```json
{
  "schema_version": "1.0",
  "num_qubits": 2,
  "gates": [
    {
      "gate_type": "H",
      "targets": [0],
      "controls": [],
      "column": 0
    }
  ]
}
```

## Fields

### `schema_version`

String identifying the QCS schema version.

The current supported value is:

```text
"1.0"
```

Matching is exact string equality: `"1.1"`, `1.0` (a number), or a missing
field are all rejected with a plain-language error.

### `num_qubits`

Integer number of qubits in the circuit.

The release supports:

```text
1 through 10 inclusive
```

Qubits are indexed from:

```text
0 through n-1
```

### `gates`

Array of gate placements.

Each placement contains:

| Field | Type | Description |
|---|---|---|
| `gate_type` | string | Supported gate/marker type |
| `targets` | array of integers | Target qubit indices |
| `controls` | array of integers | Control qubit indices where applicable |
| `column` | integer | Editor column, `0..49` |

## Supported Gate Types

The release gate palette contains exactly:

```text
H
X
Y
Z
S
T
CNOT
Toffoli
Measurement
```

No additional gate type is required by the release format.

Gate type names are case-sensitive.

## Targets and Controls

| `gate_type` | `targets` | `controls` |
|---|---|---|
| `H`, `X`, `Y`, `Z`, `S`, `T`, `Measurement` | exactly 1 | 0 |
| `CNOT` | exactly 1 | exactly 1 |
| `Toffoli` | exactly 1 | exactly 2 |

For `CNOT` and `Toffoli`, the target may be any wire of the contiguous block
formed by the target and control wires. Example Toffoli with the target on the
middle wire:

```json
{
  "gate_type": "Toffoli",
  "targets": [1],
  "controls": [0, 2],
  "column": 3
}
```

## Structural Rules

A loaded circuit must satisfy the normal circuit validation rules.

These include:

- valid qubit indices;
- valid column indices;
- correct gate arity;
- no duplicate qubit references;
- no wire/column collisions;
- valid CNOT/Toffoli structure (contiguous wires, exactly one target);
- at most one Measurement per qubit;
- Measurement must be final on its qubit.

A malformed or invalid `.qcs` file must be rejected without crashing.

## Loader Strictness

The loader must reject, with a plain-language error and without crashing:

- a root value that is not a JSON object;
- a missing required field;
- unknown fields at the root or inside a gate placement;
- `num_qubits`, `column`, and qubit indices that are not JSON integers
  (floats such as `2.0` and booleans are rejected).

## Canonical Form

The writer emits placements sorted by increasing `column`, then by the lowest
occupied qubit, with `controls` in ascending order.

Circuit equality, used for Save status, ignores placement order and the order
of `controls` entries: two circuits are equal when `num_qubits` and the set of
placements match.

## Simulation Results

Simulation results must not be stored in `.qcs` files.

The session format persists only:

```text
schema_version
num_qubits
gate placements
```

Loading a `.qcs` file clears any existing simulation result in the application.

## Save/Load Semantics

The application always edits a `.qcs` session. A successful save establishes
the current circuit as the clean saved baseline.

A session created by importing OpenQASM has no file path and no saved baseline,
so it is `Dirty` until it is saved to a `.qcs` file.

A successful load reconstructs the same circuit definition.

A save/load round trip must preserve:

- qubit count;
- gate type;
- target qubits;
- control qubits;
- editor column.

A failed load must leave the current in-memory circuit and application state
unchanged.
