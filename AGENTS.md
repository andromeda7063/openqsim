# AGENTS.md

Instructions for coding agents working on OpenQSim.

## Overview

OpenQSim is an offline PySide6 desktop application for constructing, editing,
validating, simulating, and visualising small quantum circuits. It performs
exact, noiseless statevector simulation with Qiskit Aer.

## Source of Truth

| Document | Governs |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | Product behavior, scope, acceptance. **Authoritative.** |
| [`docs/architecture.md`](docs/architecture.md) | Layers and package boundaries |
| [`docs/qcs-format.md`](docs/qcs-format.md) | `.qcs` schema, loader strictness, canonical form |
| [`docs/qasm-support.md`](docs/qasm-support.md) | Supported OpenQASM 2.0 subset |
| [`docs/quick-start.md`](docs/quick-start.md) | User walkthrough (Bell state) |

- Read the relevant requirements before changing product behavior.
- Lifecycle rules **LC-1 to LC-17** (requirements §6.5) govern application
  state. If another section restates them differently, §6.5 wins.
- Never edit `docs/requirements.md` to make the implementation look compliant.
  If a requirement looks wrong or ambiguous, stop and report it.

## Working Principles

**Think before coding.**
- State assumptions explicitly. If something is unclear, name it and ask
  instead of guessing.
- If several interpretations exist, present them; do not pick silently.
- If a simpler approach exists, say so.

**Simplicity first.**
- Write the minimum code that satisfies the requirement. No speculative
  features, abstractions for single-use code, or unrequested configurability.
- Do not invent product requirements or add out-of-scope features.
- No error handling for impossible states.

**Surgical changes.**
- Every changed line must trace to the task.
- Match existing style. Do not refactor or reformat unrelated code.
- Remove only imports/variables/functions that *your* change orphaned. Mention
  unrelated dead code instead of deleting it.
- Do not change dependency versions unless the task requires it.

**Goal-driven execution.**
- Turn the task into verifiable checks (a failing test, then a passing one).
- For multi-step work, state a brief plan with a verification for each step.

## Environment

- Reference and only tested platform: **CachyOS (Arch-based)** under
  **Hyprland (native Wayland)**, 1920x1080. Do not add Windows- or
  macOS-specific code paths.
- Python **3.13**, managed with **uv**. Use the project environment
  (`uv sync`, `uv run ...`). Do not use the system Python or bare `pip`.
- The user's shell is **fish**; use `.fish` variants when documenting
  virtualenv activation.
- Run non-GUI tests with `uv run pytest libqsim/tests`.
- Run GUI tests headless with
  `QT_QPA_PLATFORM=offscreen uv run pytest qsim-gui/tests`.
- The application makes no network requests. Never add network access,
  telemetry, or downloads at runtime.

## Architecture

Preserve this separation:

```text
UI                                  (qsim-gui)
├── circuit editor
├── selection / copy / paste
├── visualisation
└── command bindings and state indicators (views over the session layer)

Domain                              (libqsim)
├── Circuit
├── Gate
├── GatePlacement
└── validation

Application (headless session layer) (libqsim)
├── EditorSession
│   ├── current circuit
│   ├── current file path and saved baseline
│   └── Save status / Simulation status
├── candidate/commit mutation pipeline
├── undo/redo state
└── New / Open / Save / Import / Export / Run commands

Simulation                          (libqsim)
├── Qiskit Aer adapter
├── statevector
├── probabilities
└── Bloch-vector calculation

Persistence                         (libqsim)
├── QCS serializer
└── QCS loader

Interoperability                    (libqsim)
├── OpenQASM importer
└── OpenQASM exporter
```

Rules:
- `libqsim` must never import PySide6 or any Qt module.
- The domain, application session, simulation, persistence, and
  interoperability layers must be usable without creating the main window.
- Save status, Simulation status, the saved baseline, undo/redo, and the
  candidate/commit pipeline live in the **application session layer**, not in
  widgets. `qsim-gui/state.py` and `commands.py` are thin Qt adapters over it.
- Do not implement circuit semantics inside widgets.
- Do not make the 50-column limit intrinsic to the domain model; it is an
  editor-level release constraint.

## Circuit Rules

- 1-10 qubits, indexed `0..n-1`.
- Qubit 0 is the top wire and the least-significant bit. Basis-state labels put
  the highest-indexed qubit on the left. Never silently reinterpret ordering.
- Editor columns are `0..49`. The canvas may scroll; the limit stays.
- Gates execute in increasing column order.
- At most one gate per wire per column. Multi-qubit gates occupy every wire of
  their targets and controls.
- **CNOT and Toffoli** occupy contiguous wires in one column. Exactly one
  occupied wire is the target and the rest are controls. **The target may be any
  occupied wire.** Gate semantics follow Qiskit.
- Each qubit has at most one Measurement, and it must be the final operation on
  that qubit. Measurement is ignored by statevector simulation.

Gate conventions:

| Gate | `targets` | `controls` | OpenQASM |
|---|---|---|---|
| H X Y Z S T Measurement | 1 | 0 | `h q[i];` ... `measure q[i] -> c[i];` |
| CNOT | 1 | 1 | `cx q[control],q[target];` |
| Toffoli | 1 | 2 | `ccx q[c1],q[c2],q[target];` |

**Equality:** two circuits are equal when they have the same `num_qubits` and
the same *set* of placements. Placement order and the order of control indices
do not matter. Save status uses this equality. Sort placements and controls to
a canonical form wherever equality or serialization needs it.

## Mutation Semantics

All editor mutations run in the session layer as:

```text
requested operation -> build candidate circuit -> validate candidate
    fail:    no mutation, no history entry, standard error
    success: commit once, one history entry, update statuses
```

This applies to drag/drop, movement, multi-selection movement, paste,
Change target, and destructive resize.

- A rejected mutation leaves the circuit unchanged, creates no history entry,
  and reports the reason through the standard error mechanism.
- A successful mutation creates exactly one undo-history entry.
- **No-ops are not mutations** (Clear on an empty circuit, zero-cell move,
  resize to the same size): no history entry, no status change, no error.
- **Move validation** is evaluated on the resulting arrangement: remove the
  selected gates from their original cells first, so a selection may move onto
  cells it vacates but never onto unselected gates.
- Multi-qubit gates are atomic: controls, targets, relative wire positions, and
  contiguity move and copy together. They are never partially selected.
- A dropped CNOT/Toffoli starts at the dropped wire (its lowest-indexed wire)
  with controls on the upper wires and the target on the bottom wire.
  **Change target** swaps CNOT roles or cycles the Toffoli target; each use is
  one undoable mutation.
- Paste: the clicked cell is the top-left anchor; Ctrl+V uses the most recently
  clicked cell, else qubit 0 / column 0. Arrow keys with an empty selection and
  Ctrl+V with an empty clipboard do nothing.

## Undo / Redo

- Undo and Redo move through existing history; they create no new entries.
- They recalculate Save status against the saved baseline.
- They make a retained simulation result `Stale`; historical results are not
  restored.
- A new successful mutation after Undo clears redo history.
- Run, Save, Save As, Load/Open, Import, Export, selection changes, and other
  non-mutating operations create no history entries.

## Application State

Save status (`Clean` | `Dirty`) and Simulation status (`None` | `Current` |
`Stale`) are independent.

The app edits a single **`.qcs` session**: a circuit, an optional file path, and
an optional saved baseline. A session with no baseline is always `Dirty`.

- **Startup:** empty 2-qubit circuit, baseline = that circuit, Save=`Clean`,
  Simulation=`None`.
- **Mutation:** recompute Save status; a retained result becomes `Stale`.
- **Run (success):** replace the result, Simulation=`Current`; Save status is
  unchanged.
- **Run (failure):** leave the previous result **and its status unchanged**;
  report the error.
- **Save / Save As:** establish the current circuit as the clean baseline. Save
  with no file path opens the file-save dialog.
- **New / Load/Open (success):** circuit becomes the clean baseline,
  Simulation=`None`, history cleared.
- **Import OpenQASM (success):** replaces the session with a **new unsaved
  session**: no file path, no baseline, Save=`Dirty`, Simulation=`None`, history
  cleared. A `.qasm` file never becomes the session file.
- **Failed Load/Open or Import:** the complete prior state is unchanged.
- **Dirty New, Load/Open, Import, or Exit** offers exactly `Save`,
  `Don't Save`, `Cancel`. `Save` failing aborts the operation. `Cancel` changes
  nothing. If the operation then fails after `Don't Save`, nothing is
  discarded.

## Validation

Validation must be callable without the GUI and returns a list of errors
(empty = valid). Preserve checks for:

- qubit and column bounds;
- gate arity (exactly one target; 0/1/2 controls by gate);
- duplicate qubit references;
- wire/column collisions;
- Measurement rules;
- CNOT/Toffoli contiguity and exactly one target.

Errors identify the offending placement in plain language and never expose raw
Python exceptions or Qiskit stack traces. A failed validation never modifies
the circuit. When validation fails, Run must not invoke the simulator; the
simulation API itself also validates and refuses invalid circuits.

## Simulation

- Use Qiskit Aer exact noiseless statevector simulation.
- The API is callable without the GUI and returns the full statevector,
  probabilities of all basis states, and one reduced Bloch vector per qubit.
- Run only when the user activates Run. Never re-run automatically.
- Execute in increasing column order. Strip Measurement before simulating; it
  does not collapse the state.
- Run is synchronous on the GUI thread for this release.
- Compare floats with an absolute tolerance of `1e-9` unless a test needs
  stricter.

## QCS

JSON with `schema_version` (exactly the string `"1.0"`), `num_qubits`, and
`gates` (each with `gate_type`, `targets`, `controls`, `column`). Full schema:
[`docs/qcs-format.md`](docs/qcs-format.md).

- Never persist simulation results.
- **Writer:** canonical order: placements by increasing column, then lowest
  occupied qubit; controls ascending.
- **Loader is strict** and must not crash. Reject: non-object root, missing
  fields, unknown fields, non-integer values (floats and booleans included),
  wrong `schema_version`, wrong target/control counts, and anything failing
  circuit validation. Errors are plain-language.
- A failed load leaves all application state unchanged.

## OpenQASM

Implement only the subset in [`docs/qasm-support.md`](docs/qasm-support.md).

- Header: `OPENQASM 2.0;` and `include "qelib1.inc";` are both required.
  `//` comments are ignored. Gate names are lowercase.
- One quantum register named `q` (1-10 qubits); zero or one classical register.
  With any `measure`, the classical register is exactly `c[n]` and maps
  `q[i] -> c[i]`.
- Operands are explicit `q[i]`. Reject whole-register operands (`h q;`),
  repeated or out-of-range operands, and non-contiguous `cx`/`ccx` operands.
- **Argument order is Qiskit's: controls first, target last.** On import `ccx`
  controls may come in either order and are stored ascending; on export,
  controls are written ascending, then the target.
- Import validates the whole file before constructing anything, then places each
  statement in the next column (`0, 1, 2, ...`). More than 50 operations is
  rejected.
- Export order: increasing column, then lowest occupied qubit. Every export
  starts with `OPENQASM 2.0;`, `include "qelib1.inc";`, `qreg q[n];`, then
  `creg c[n];` only if a Measurement exists.
- Import/export preserve gate type, qubits, and execution order, not exact
  columns.
- Do not add unsupported constructs or Qiskit Python source import/export.

## GUI

- Base the canvas on discrete `(qubit, column)` cells and centralize the
  conversion between grid coordinates and visual geometry.
- All 50 columns and all wires must be reachable; the canvas may scroll.
  Drag/drop, selection, paste, and arrow-key movement behave identically for
  scrolled-to cells, and a moved or pasted selection is scrolled into view.
- At 1920x1080 the palette, scrollable canvas, and access to the Bloch and
  histogram views must all fit in one window.
- Selection operates on whole logical gate objects.
  - Click replaces the selection; Ctrl toggles; marquee replaces unless Ctrl is
    held.
  - Arrow keys move the selection exactly one cell per press.
- `Ctrl+E` is **Export OpenQASM**; image export has no default shortcut.
- Must work in a native Wayland session under Hyprland, tiled and floating:
  drag-and-drop, shortcuts, file dialogs, PNG export.
- Implement the keyboard and selection behavior in the requirements; do not
  approximate it.

## Error Handling

Use one standard user-facing error mechanism. Never expose raw Python
exceptions, Qiskit stack traces, or parser stack traces. Failed operations
preserve existing state unless a destructive mutation was explicitly confirmed.

## Required checks (before every commit)

CI fails on unformatted code, so format first, then verify. Run in this order
and report real output:

```fish
uv run ruff format .            # applies formatting; never skip
uv run ruff check . --fix       # applies safe lint fixes
uv run ruff format --check .    # must report nothing would change
uv run ruff check .             # must pass
uv run mypy libqsim
uv run pytest
QT_QPA_PLATFORM=offscreen uv run pytest qsim-gui/tests
```

- Never commit unformatted code; include any files ruff reformats in the same
  commit.
- Do not change ruff configuration or add ignores to make checks pass.

## Testing

- Prefer non-GUI tests for domain, validation, session, simulation, QCS, and
  QASM. The session state-transition tests (LC-1 to LC-17) must run without
  constructing Qt objects.
- Reference cases (see requirements §17): startup state; empty 1-qubit circuit;
  X; Y; H; H then H; Bell state (H on the control, then CNOT); Z; S and T;
  known Bloch vectors; 3-qubit basis ordering; CNOT with control above and
  below the target; Toffoli including a middle-wire target; Measurement;
  validation failures; no-op mutations; move/paste atomicity; selection;
  undo/redo and baseline equality; save/load round trip; QCS strictness and
  canonical order; QASM ordering, argument order, limits, and invalid operands;
  Import marks the session `Dirty`; failed Run keeps status; stale/current
  simulation state.
- Test failure paths as carefully as success paths.
- Do not claim tests passed unless you ran them.

## Scope

Do not implement these unless the requirements change:

- quantum-hardware or cloud execution;
- network communication or telemetry;
- noise/error models;
- hardware transpilation or optimisation;
- Qiskit Python-code import/export;
- OpenQASM 3;
- parameterized or symbolic gates; arbitrary-angle RX/RY/RZ;
- custom gate definitions;
- mid-circuit branching or classical control flow;
- reset; barriers;
- multiple quantum-register declarations in imported OpenQASM;
- accounts, authentication, collaboration;
- production-scale circuit design;
- dedicated Grover or Shor features;
- packaged installers or bundled executables;
- Windows, macOS, or other-distribution support.

## Task Format

For a bounded coding task, use:

```text
Requirements:
- FR-x.x / NFR-x.x / LC-x

Files in scope:
- ...

Behavior:
- ...

Non-goals:
- ...

Tests:
- ...

Verification:
- ...
```

Avoid broad tasks such as "Finish the entire application", "Refactor the
project", or "Make it production-ready".

## Completion Report

```text
Implemented:
- ...

Requirements:
- ...

Assumptions:
- ...

Files changed:
- ...

Tests:
- ...

Verification:
- ...

Known limitations:
- ...
```

Do not claim tests passed unless they were actually run. Review the final diff
for unrelated changes before reporting.