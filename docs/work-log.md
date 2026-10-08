# Rolling Work Log

## 2026-10-09 — Add syntax highlighting to the QASM editor

- Added syntax highlighting for OpenQASM headers/declarations, supported gates,
  strings, numeric literals, and line comments in the QASM editor tab.
- Added a GUI test that checks highlighted token formats in the editor.
- Requirements documents, including archived requirements, were not changed.

## 2026-10-09 — Replace main toolbar labels with symbols

- Replaced the New, Open, Save, Save As, Undo, Redo, and Run toolbar labels
  with Lucide SVG symbols bundled under `qsim-gui/src/qsim_gui/assets/icons/`.
- Kept the action labels in menus and supplied accessible names and tooltips
  for the icon-only toolbar controls.
- Included Lucide's license and attribution with the local assets.
- Requirements documents were not changed. The active specification does not
  require text labels on these toolbar controls; this is an interface styling
  change within existing behavior.
