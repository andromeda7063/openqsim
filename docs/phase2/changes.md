# Phase 2 proposed changes from the phase 1 baseline

Status: discussion draft. This is a change map, not a migration already made.
See [research](research.md), [requirements](requirements.md), and [plan](plan.md).

| Area | Current phase 1 rule | Proposed phase 2 direction | Decision / migration impact |
|---|---|---|---|
| Product | Offline educational desktop statevector app | Composer-like workspace and local functions, still 100% offline | No QPU, accounts, remote jobs, sharing, or runtime network access |
| Startup | Empty 2-qubit clean `.qcs` session | Four qubits and four classical bits, editable title | Changes LC-1 and saved document state |
| Canvas | Finite 50-column grid, contiguous CX/CCX | Freeform/Left/Layers views; arbitrary wire span for multi-qubit gates; expandable circuit width | Distinguish logical order from display columns; retain phase 1 file meaning |
| Gates | H X Y Z S T CX CCX Measurement | Add I, SWAP, SX/SXdg, Sdg/Tdg, P, RX/RY/RZ and control modifiers | Parameter schema, validation, simulation, QASM mapping |
| Parameters | None | Editable numeric angles, including `pi` expressions | Need canonical storage and precision rule |
| Nonunitary | Final measurement marker ignored in statevector | True mid-circuit measurement, reset, classical bits, local shot results, checkpoint phase disks | Dynamic simulation and result-type rules |
| Structures | No barriers/conditionals/loops/boxes/custom gates | Implement local semantics for barriers, if, for, while, boxes, and named custom gates | Bounded execution, block AST, file/code round trips |
| Visualization | Explicit Run; Bloch and probability views | Live probability/Q-sphere/statevector panels, phase disks, Inspect mode | Revise simulation lifecycle; retain Bloch as optional extra |
| Code | QASM 2 import/export subset | Synchronized editable code pane; QASM 3 default, QASM 2 option | Atomic parse/commit and round-trip behavior; guide conflict resolved by live UI |
| Persistence | Strict `.qcs` 1.0 and saved baseline | Versioned `.qcs` 2.0 for new fields; read old files | Never reinterpret a 1.0 file or silently drop features |
| UI | System palette, three-column layout | Dark Composer-inspired four-region layout; colored/monochrome gates; light/dark chrome | Reference 1920×1080 Wayland; keyboard and accessibility parity |
| Export | PNG of circuit and views | Export preview, SVG/PNG, visualization data CSV | Define which panels can export which formats |
| Error handling | One standard error mechanism | Retain atomic rejection; code diagnostics linked to source | A failed code edit must not corrupt the graphical circuit |

## Explicitly retained until a new baseline says otherwise

- Python 3.13, PySide6, Qiskit Aer, headless `libqsim` domain/session boundary.
- Qubit 0 at top and least-significant in basis indexing.
- No runtime network access. Phase 2 must remain 100% offline.
- Phase 1 `.qcs` files remain readable; current release requirements remain
  authoritative for existing implementation work.

## Specification work needed before adoption

1. Revise lifecycle rules LC-1–LC-17 into versioned phase 2 rules, especially
   live results, code edits, and title/format dirty status.
2. Write `qcs-format-v2.md` with a complete schema and 1.0 migration rules.
3. Write `qasm-support-v2.md` with exact accepted QASM 2 and QASM 3 grammar,
   parameters, registers, block structures, and rejected constructs. Decide
   whether broader third-party QASM 3 is a goal beyond Composer-generated code.
4. Specify deterministic unitary previews versus local dynamic shot results,
   including mixed-state panel behavior and finite loop/resource limits.
5. Update architecture, quick start, and acceptance checklist after the new
   requirements are approved.
