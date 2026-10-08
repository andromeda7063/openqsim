# Phase 2 implementation plan (draft)

Status: planning proposal, 2026-10-09. No phase 2 application behavior has
been implemented. Read [research](research.md), [requirements](requirements.md),
and [changes](changes.md) first.

## Decision gate — before coding

The user's offline decision resolves D1 and brings all local Composer catalog
functions into scope. Resolve D6–D7 in `requirements.md`, then mark the
requirements as adopted, replace phase 1 lifecycle rules with complete
versioned rules, and write QCS v2, QASM v2, and dynamic simulation
specifications. Verify by tracing every palette
operation and menu action to a documented semantic, persistence, and test
expectation. Do not implement placeholders that look functional but are not.

## Milestone 1 — document/domain foundation

- Extend the headless circuit model with explicit operation order, parameters,
  classical bits, groups, and block/loop nodes. Separate logical order
  from visual alignment. Keep phase 1 file interpretation stable.
- Add strict validation and QCS v2 migration, with failure atomicity.
- Verify with failing-then-passing unit tests for each new field, equality,
  ordering, and invalid document, plus old `.qcs` regression tests.

## Milestone 2 — gate and simulation parity

- Add the adopted unitary palette in small families: inverse/identity/SX,
  phase and rotations, then SWAP and generalized controls.
- Build deterministic snapshots for unitary layers and the global Q-sphere
  data model. Add local measurement, reset, classical control, and shot
  execution with explicit mixed-state/branch result semantics.
- Verify matrices and Qiskit argument order with headless reference circuits,
  numeric tolerance tests, and validation failure tests.

## Milestone 3 — code and file interoperability

- Implement the exact adopted QASM 3/2 subsets with a parser that reports
  source locations. Generate code from canonical circuit state. Apply valid
  editor text as one session mutation; retain the last valid circuit on error.
- Cover custom definitions, controls, measurement, reset, and bounded block
  constructs. Report a QASM 2 conversion that cannot preserve meaning.
- Add Qiskit read-only generation only after semantic round trips work.
- Verify code↔canvas↔QCS round trips, unsupported syntax diagnostics, source
  ordering, and undo/redo across code edits.

## Milestone 4 — Composer-like shell and editor

- Build the header, searchable colored catalog, canvas, code pane, docked
  visualization area, splitters, themes, and saved workspace preferences.
- Add in-context controls, parameter editing, alignment views, and register
  management on top of session commands.
- Verify geometry and behavior with headless Qt tests, then native Wayland
  drag/drop, focus, dialogs, shortcuts, and screenshots at 1920×1080.

## Milestone 5 — visualizations and inspection

- Implement probabilities, statevector, Q-sphere, phase disks, and optional
  Bloch panels from one snapshot API. Add table/export options.
- Implement Inspect stepping and live local previews with clear
  result freshness, cancellation, and error behavior.
- Verify Bell and phase-sensitive circuits visually and numerically; test
  intermediate snapshots, stale/failure transitions, and export files.

## Milestone 6 — polish and acceptance

- Compare the app with the supplied Composer screenshot and a fresh live
  reference at the same viewport, fixing spacing, glyphs, contrast, and
  overflow without compromising behavior.
- Update user guides and traceability. Review all changed files for unrelated
  edits. Run the `AGENTS.md` required checks in order before each commit.
- Acceptance requires no exposed unsupported operation, no silent data loss,
  valid v1 file loading, no runtime network calls, and passed
  automated/native Wayland checks.

## Suggested bounded work packages

Do not assign “replicate Composer” as one coding task. Cut work packages by
requirement IDs and files, with a failing test and a specific verification
for each: QCS v2 model; inverse gates; rotations; measurement/reset; control
flow; custom gates; QASM subset; workspace shell; synchronized editor;
Q-sphere; Inspect; exports. The sequence above
allows each completed package to remain reviewable and reversible.
