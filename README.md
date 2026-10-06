# OpenQSim

OpenQSim is an offline PySide6 desktop application for constructing, editing,
validating, simulating, and visualising small quantum circuits.

It is intended for educational and prototyping use. It performs exact,
noiseless statevector simulation on a classical computer using Qiskit Aer.
It does not execute circuits on quantum hardware and does not require network
access.

The release is source-run; a packaged installer or bundled executable is not
required.

## Features

- Circuit editor for 1–10 qubits and up to 50 columns (the canvas scrolls)
- Gate palette containing H, X, Y, Z, S, T, CNOT, Toffoli, and Measurement
- Gate placement, deletion, movement, rectangular multi-selection,
  copy/paste, and keyboard editing
- Change target command for CNOT and Toffoli
- Undo and redo for circuit mutations
- Structural circuit validation
- Exact noiseless statevector simulation using Qiskit Aer
- Per-qubit reduced-state Bloch-sphere visualisation
- Full computational-basis probability histogram
- PNG export of the circuit, Bloch-sphere view, and histogram view
- Local `.qcs` JSON session files
- OpenQASM 2.0 import and export for the explicitly supported subset
- Non-GUI simulation API
- Local user documentation and gate tooltips
- Offline operation

## Requirements

The implementation is governed by the
[OpenQSim Requirements Specification](docs/requirements.md).

The requirements document is the authoritative reference for release scope,
functional requirements, non-functional requirements, data requirements,
interfaces, error handling, correctness, and acceptance criteria.

## Project Structure

The repository is organized into a reusable core package and a PySide6
application package.

```text
OpenQSim/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
│
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   ├── qcs-format.md
│   ├── qasm-support.md
│   └── quick-start.md
│
├── libqsim/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── libqsim/
│   │       ├── __init__.py
│   │       ├── domain/
│   │       │   ├── __init__.py
│   │       │   ├── models.py
│   │       │   ├── gates.py
│   │       │   └── validation.py
│   │       ├── application/
│   │       │   ├── __init__.py
│   │       │   ├── session.py
│   │       │   └── history.py
│   │       ├── simulation/
│   │       │   ├── __init__.py
│   │       │   ├── engine.py
│   │       │   ├── results.py
│   │       │   └── bloch.py
│   │       ├── persistence/
│   │       │   ├── __init__.py
│   │       │   └── qcs.py
│   │       └── qasm/
│   │           ├── __init__.py
│   │           ├── importer.py
│   │           └── exporter.py
│   └── tests/
│       ├── test_gates.py
│       ├── test_models.py
│       ├── test_validation.py
│       ├── test_history.py
│       ├── test_session.py
│       ├── test_results.py
│       ├── test_simulation.py
│       ├── test_bloch.py
│       ├── test_qcs.py
│       └── test_qasm.py
│
├── qsim-gui/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── qsim_gui/
│   │       ├── __init__.py
│   │       ├── app.py
│   │       ├── main_window.py
│   │       ├── state.py
│   │       ├── commands.py
│   │       ├── dialogs.py
│   │       └── widgets/
│   │           ├── gate_palette.py
│   │           ├── circuit_canvas.py
│   │           ├── bloch_view.py
│   │           └── histogram_view.py
│   └── tests/
│       ├── test_state.py
│       ├── test_commands.py
│       └── test_gui_smoke.py
│
└── tests/
    └── acceptance/
        └── test_release_acceptance.py
```

The exact file/module names are an implementation organization; the
requirements define the responsibilities and boundaries, not these filenames.
In `qsim-gui`, `state.py` and `commands.py` are thin Qt adapters over the
session layer in `libqsim/application/`; they contain no state-machine logic.

## Architecture

The implementation keeps the following separation:

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
├── QCS serializer
└── QCS loader

Interoperability
├── OpenQASM importer
└── OpenQASM exporter
```

The domain, application session, simulation, persistence, and interoperability
layers remain usable without creating the PySide6 main window.

## Circuit Conventions

- A circuit contains 1–10 qubits.
- Qubits are indexed `0..n-1`.
- Qubit 0 is the top wire.
- Qubit 0 is the least-significant bit in computational-basis indexing.
- Basis-state labels place the highest-indexed qubit on the left.
- Editor columns are `0..49`; the canvas may scroll to reach them all.
- Gates execute in increasing column order.
- At most one gate may occupy a given qubit wire in a given column.
- Multi-qubit gates occupy every wire associated with their targets and controls.
- CNOT and Toffoli occupy contiguous qubit wires in one column.
- For CNOT and Toffoli, exactly one occupied wire is the target and the others
  are controls. The target may be any occupied wire.
- A newly placed CNOT or Toffoli puts its controls on the upper wires and its
  target on the bottom wire; use **Change target** to move the target.
- Gate semantics and OpenQASM argument order follow Qiskit:
  `cx control,target` and `ccx control1,control2,target`.
- Each qubit may contain at most one Measurement.
- Measurement must be the final operation on its qubit.
- Measurement is not a probabilistic state-collapse operation.
- The simulator ignores Measurement when calculating the statevector.

## Simulation

Simulation occurs only when the user activates **Run**.

A successful simulation produces:

- the full statevector;
- the probability of every computational-basis state;
- one reduced Bloch vector for each qubit.

The application retains simulation results in memory. They are not persisted
in `.qcs` files.

After a successful circuit mutation, an existing simulation result remains
visible but becomes stale. A successful Run replaces the retained result and
makes it current. A failed Run leaves the previous result and its status
unchanged.

## Session Files

The application always edits a `.qcs` session. `.qcs` files are JSON and
contain the circuit definition and schema version.

Example:

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

Loading is strict: malformed files, unknown fields, non-integer values, and
unsupported schema versions are rejected without changing the current circuit.

Importing OpenQASM creates a new **unsaved** session (no file path, Save status
`Dirty`); a `.qasm` file never becomes the session file. New, Open, Import, and
Exit prompt with `Save` / `Don't Save` / `Cancel` when there are unsaved
changes.

The exact schema is documented in
[`docs/qcs-format.md`](docs/qcs-format.md).

## OpenQASM 2.0

OpenQSim supports the explicitly defined OpenQASM 2.0 subset:

- `OPENQASM 2.0;` and `include "qelib1.inc";` (both required);
- one quantum register named `q`;
- a quantum register containing at most 10 qubits;
- zero or one classical register;
- H, X, Y, Z, S, T, CX, CCX;
- Measurement statements of the form `measure q[i] -> c[i];`

Argument order follows OpenQASM and Qiskit: controls first, target last.

```qasm
cx q[0],q[1];        // control q0, target q1
ccx q[0],q[2],q[1];  // controls q0,q2; target q1
```

Unsupported OpenQASM constructs are rejected. OpenQASM 3 and Qiskit Python
source-code import/export are outside the release scope.

See [`docs/qasm-support.md`](docs/qasm-support.md).

## Development

Use Python 3.13 and the exact dependency versions defined by the checked-in
project environment/lock files. Arch-based distributions track the newest
Python, so provision 3.13 with `uv` (see `.python-version`) rather than relying
on the system Python.

```fish
uv sync
uv run python -m qsim_gui.app
uv run pytest libqsim/tests
QT_QPA_PLATFORM=offscreen uv run pytest qsim-gui/tests
```

The project requires PySide6 / Qt 6, Qiskit, Qiskit Aer, and NumPy where
required.

**Tested platform.** Release acceptance is performed on a single reference
machine: CachyOS (Arch-based) under Hyprland (native Wayland) at 1920x1080.
Other operating systems are not claimed or verified in this release.

Before release, verify the automated tests and the acceptance criteria in
[`docs/requirements.md`](docs/requirements.md).

## Documentation

- [Requirements](docs/requirements.md) — authoritative requirements specification
- [Architecture](docs/architecture.md) — implementation architecture
- [Quick Start](docs/quick-start.md) — Bell-state workflow
- [QCS Format](docs/qcs-format.md) — `.qcs` schema
- [OpenQASM Support](docs/qasm-support.md) — supported OpenQASM 2.0 subset
- [AGENTS.md](AGENTS.md) — coding-agent instructions

## Scope

The release does not require:

- quantum-hardware execution;
- cloud execution;
- network communication or telemetry;
- noise or error models;
- hardware transpilation or optimisation;
- Qiskit Python-code import/export;
- OpenQASM 3;
- parameterized gates or symbolic parameters;
- arbitrary-angle RX/RY/RZ gates;
- custom gate definitions;
- mid-circuit branching or classical control flow;
- reset operations;
- barriers;
- multiple quantum-register declarations in imported OpenQASM;
- multi-user accounts;
- authentication;
- collaboration;
- production-scale circuit design;
- dedicated Grover or Shor application features;
- a packaged installer or bundled executable;
- support for Windows, macOS, or other Linux distributions.