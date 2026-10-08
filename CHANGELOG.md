# Changelog

Changes on `v1.1-dev` relative to `main` (v1.0):

## v1.1 (in development)

- Added a fixed offline library of five editable circuit examples. Loading an
  example uses the dirty-session prompt and creates a new unsaved session.
- Reworked the circuit workspace with a compact vertical palette of symbolic
  gate buttons, a canvas-centered layout, and simulation results below the
  workspace with Bloch and histogram views side by side.
- Added an embedded editable OpenQASM 2.0 editor beside the canvas. It displays
  canonical circuit text, checks syntax and the supported subset as text
  changes, and applies valid programs only after an explicit action.
- Added Dark and Dark Purple flat themes plus an Edit -> Preferences window.
  The chosen theme is stored locally and restored on launch.
- Expanded requirements, architecture, user guidance, and manual acceptance
  steps to cover the v1.1 workspace, QASM editor, and appearance preferences.
- Preserved the v1.0 requirements from `main` at
  `docs/archive/requirements-v1.0.md`; the active v1.1 requirements remain at
  `docs/requirements.md`, with pytest mappings in the current traceability
  report.
- Added GUI tests for the embedded QASM editor and theme preferences. Existing
  core OpenQASM tests cover importer/exporter rules, limits, ordering, and
  invalid input.
