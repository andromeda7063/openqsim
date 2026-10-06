# OpenQSim Architecture

## Overview

OpenQSim is an offline PySide6 desktop application for constructing, editing,
validating, simulating, and visualising small quantum circuits.

The implementation is divided into five primary layers plus the UI:

```text
UI
├── circuit editor
├── selection / copy / paste
├── visualisation
└── command bindings and state indicators (views over the session layer)

Domain
├── Circuit
├── Gate
├── GatePlacement
└── validation

Application (headless session layer)
├── EditorSession
│   ├── current circuit
│   ├── current file path and saved baseline
│   └── Save status / Simulation status
├── candidate/commit mutation pipeline
├── undo/redo state
└── New / Open / Save / Import / Export / Run commands

Simulation
├── Qiskit Aer adapter
├── statevector
├── probabilities
└── Bloch-vector calculation

Persistence
└── QCS serializer / loader

Interoperability
├── OpenQASM importer
└── OpenQASM exporter
```

The domain, application session, simulation, persistence, and interoperability
layers must remain usable without constructing the PySide6 main window.

## Package Boundary

The repository contains two logical packages:

```text
libqsim/
└── reusable non-GUI functionality

qsim-gui/
└── PySide6 application and user interface
```

The `libqsim` package should not depend on PySide6.

The GUI should communicate with the core through domain and application APIs
rather than implementing quantum-circuit semantics inside widgets.

Save status, Simulation status, the saved baseline, undo/redo history, and the
candidate/commit mutation pipeline belong to the application session layer in
`libqsim`, not to widgets, so the state-transition rules can be tested without
constructing Qt objects.

## Domain

The domain model represents the circuit independently of the GUI.

A circuit contains:

- `num_qubits`
- an ordered collection of gate placements

Each gate placement contains:

- gate type
- target qubit indices
- control qubit indices where applicable
- editor column

Release constraints include:

- 1–10 qubits
- columns `0..49`
- qubit indices `0..n-1`
- at most one gate on a given wire/column
- multi-qubit gates occupy all referenced wires
- CNOT and Toffoli are contiguous, single-column atomic objects

Qubit 0 is the top wire and the least-significant bit in computational-basis
indexing.

For CNOT and Toffoli, exactly one occupied wire is the target and the other
occupied wires are controls. The target may be any occupied wire. Gate
semantics and OpenQASM argument order follow Qiskit: controls first, target
last.

Two circuit definitions are equal when they have the same `num_qubits` and the
same set of gate placements. The order of the placement collection and the
order of control indices within a placement do not affect equality. Save status
is computed with this equality.

## Validation

Circuit validation is independent of the GUI.

Validation checks include:

- qubit bounds
- column bounds
- gate arity
- duplicate qubit references
- wire/column collisions
- Measurement placement
- CNOT and Toffoli contiguity and target/control arrangement

Validation returns a list of validation errors. An empty list indicates a
valid circuit.

A failed validation must not modify the circuit.

## Simulation

Simulation is exposed through a non-GUI API.

The simulation layer:

1. receives a circuit and validates it, returning validation errors without
   invoking Aer if it is invalid;
2. executes supported operations in increasing editor-column order;
3. uses Qiskit Aer statevector simulation;
4. ignores Measurement when calculating the statevector;
5. calculates computational-basis probabilities;
6. calculates one reduced Bloch vector for each qubit.

Simulation is exact noiseless statevector simulation within the application's
numerical precision.

The release runs simulation synchronously on the GUI thread.

## Persistence

The persistence layer owns `.qcs` JSON serialization and loading.

A `.qcs` file stores only the circuit definition and schema version.

The writer emits canonical order: placements sorted by increasing column, then
lowest occupied qubit, with control indices ascending. The loader is strict: it
rejects unknown fields, non-integer values where integers are required, and any
schema version other than `"1.0"`.

Simulation results are held in memory and are not persisted.

Serialization and deserialization must be callable without the GUI.

## OpenQASM Interoperability

The OpenQASM layer provides import and export for the supported OpenQASM 2.0
subset.

Import validates the complete supported subset before constructing a circuit.

Imported operations are placed into successive editor columns according to
statement order.

OpenQASM is only converted to or from a circuit. The application always edits a
`.qcs` session: a successful import replaces the current session with a new
unsaved `.qcs` session (no file path, no saved baseline) and never makes the
`.qasm` file the session file.

`cx` and `ccx` use Qiskit argument order (controls first, target last).

Export is deterministic:

1. increasing editor column;
2. within the same column, increasing lowest-indexed occupied qubit.

The OpenQASM layer is independent of the PySide6 UI.

## GUI

The GUI provides:

- gate palette
- circuit canvas
- New / Save / Save As / Open
- OpenQASM import/export
- Run
- Bloch-sphere visualisation
- probability histogram
- image export
- Save status
- Simulation status
- standard error presentation
- Change target command for CNOT and Toffoli

The circuit canvas maps discrete `(qubit, column)` coordinates to visual grid
cells.

Selection operates on logical gate objects. CNOT and Toffoli remain atomic
through selection, movement, and copy/paste.

## Application State

Save status and simulation status are independent:

```text
SaveStatus
├── Clean
└── Dirty

SimulationStatus
├── None
├── Current
└── Stale
```

A successful circuit mutation recalculates Save status against the saved
baseline. If a simulation result exists, the result becomes stale.

A successful Run replaces the retained simulation result and makes it current
without changing Save status.

Undo and Redo change the circuit and recalculate Save status. They make any
retained simulation result stale and do not restore historical simulation
results.

The application edits a single `.qcs` session: a circuit, an optional file path,
and an optional saved baseline. A session with no saved baseline is always
`Dirty`.

Successful New and Load/Open establish the resulting circuit as clean, clear
simulation results, and clear undo/redo history. A successful Import replaces
the session with a new unsaved session (no file path, no baseline), so Save
status is `Dirty`; it also clears simulation results and undo/redo history.

New, Load/Open, Import, and Exit prompt `Save` / `Don't Save` / `Cancel` when
Save status is `Dirty`.

A failed Run leaves the retained result and its Simulation status unchanged.

## Mutation Boundary

Editor mutations are executed by the application session layer (not by widgets)
and follow an atomic candidate/commit pattern:

```text
requested operation
        |
        v
construct candidate circuit
        |
        v
validate candidate
     /          fail      success
    |          |
    v          v
no mutation   commit once
no history    one history entry
error         update state
```

This applies to drag/drop, movement, multi-selection movement, paste, and
destructive resize.

A requested operation that would leave the circuit definition unchanged is a
no-op: no commit, no history entry, and no status change. Collision checks for
a move are made after removing the selected gates from their original cells, so
a selection may move onto cells it vacates.

## Release Constraint: Editor Columns

The 50-column limit is an editor-level release constraint.

The underlying circuit model should not be designed in a way that makes this
limit intrinsic to the domain model. The canvas may scroll within the release;
a future release may remove the fixed editor limit entirely.