# Changelog

## v1.1 (in development)

Changes on `v1.1/dev` relative to `dev` (v1.0).

### Circuit workspace

- Reworked the main window with a compact vertical gate palette, a centered
  circuit canvas, an OpenQASM 2.0 editor beside it, and Bloch and histogram
  results below it.
- Added syntax highlighting for supported OpenQASM headers, declarations,
  gates, strings, numbers, and comments in the editor.
- Added Dark and Dark Purple themes and an Edit → Preferences window. The
  selected theme is restored on launch.
- Replaced the main toolbar's text buttons with bundled Lucide icons, retaining
  action names in menus and accessible names and tooltips on the controls.
- Expanded the canvas to keep all 50 editor columns reachable as gates are
  placed, and added scrolling that follows active drag gestures and edited
  selections.
- Added palette drag ghosts, gate role previews, and candidate validity
  feedback; drops in the canvas margin are rejected.
- Preserved selection while revealing pasted gates and added coverage for
  canvas state transitions, edge scrolling, and viewport geometry.

### Circuits and simulation

- Added five built-in, editable example circuits. Loading an example starts an
  unsaved session and follows the dirty-session confirmation flow.
- Added simulation snapshots for the initial state and after each occupied
  circuit column, with probabilities and Bloch vectors for each snapshot.
- Separated **Run** from **Step Run**: Run displays the final result; Step Run
  starts at the initial state and shows Previous and Next snapshot controls.
- Redesigned Bloch results as independently rotatable wireframe spheres with
  numeric vector coordinates. One Reset View control restores all sphere
  orientations, and PNG export captures the displayed angles and snapshot.

### Documentation and checks

- Updated requirements, architecture, quick-start guidance, and acceptance
  checks for the v1.1 features. Preserved the v1.0 requirements at
  `docs/archive/requirements-v1.0.md`.
- Added and updated core and GUI tests for examples, trace navigation, QASM
  highlighting, preferences, and Bloch interaction.
