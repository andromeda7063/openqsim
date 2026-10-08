# OpenQSim Release Acceptance Checklist

Manual acceptance procedure for OpenQSim v1.1 on the reference platform
(**CachyOS**, **Hyprland / native Wayland**, **1920x1080** display resolution).

This document details the manual verification items required by §18 of
[`docs/requirements.md`](requirements.md) that cannot be verified purely by headless
automated test runners.

---

## 1. Environment & Setup Verification

- [ ] **Platform**: Running natively on CachyOS (Arch-based Linux) under Hyprland (native Wayland compositor).
- [ ] **Display Resolution**: Primary display is set to 1920x1080.
- [ ] **Environment**: Pinned dependencies synced via `uv sync`.
- [ ] **Launch**: Run `uv run python -m qsim_gui` from the repo root.
- [ ] **Startup State Check**:
  - Main window appears cleanly without graphical glitching.
  - Compact symbolic gate palette on the left; circuit canvas in the center; OpenQASM editor on the right; simulation results below the workspace with Bloch views and histogram side by side.
  - Status bar displays: `Save: Clean`, `Simulation: None`.
  - Undo and Redo actions are disabled.

---

## OpenQASM Editor and Updated Layout (FR-7.6 to FR-7.8)

- [ ] The palette is a narrow vertical column of symbolic gate icons; each icon has an accessible name and useful tooltip.
- [ ] Circuit single-qubit gates use conventional symbols; CNOT and Toffoli use control dots and target circled-plus symbols.
- [ ] The QASM editor shows the current circuit export and updates after circuit edits or loading a `.qcs` file.
- [ ] Invalid QASM syntax is reported and cannot be applied. Syntax-valid unsupported constructs are reported as unsupported.
- [ ] Applying valid supported QASM to a dirty session offers Save, Don't Save, and Cancel; Cancel preserves the session.
- [ ] Bloch spheres and the histogram appear side by side in the bottom results area.

## Rotatable Bloch Views (FR-4.17 to FR-4.23, NFR-2.8)

- [ ] At 1920x1080, inspect each wireframe, front and rear line styles, X/Y/Z labels, vector, numeric coordinates, and Reset View control. Check readability in tiled and floating layouts.
- [ ] Left-drag starting inside `q0`'s sphere at several angles. Confirm `q0` rotates while `q1` keeps its angle. Dragging from a label or surrounding panel does not rotate a sphere.
- [ ] Confirm the vector stays attached to its Bloch coordinates; pure vectors remain on the sphere surface and mixed reduced-state vectors stay inside. Numeric coordinates stay unchanged while dragging.
- [ ] Confirm dragging changes neither the circuit nor Save/Simulation status, selected step, or Undo/Redo availability.
- [ ] Move to another simulation snapshot. Confirm the vector and coordinates update while each sphere retains its angle.
- [ ] Click **Reset View** on one sphere. Confirm it returns to the default angle and the other sphere does not move.
- [ ] Export a Bloch PNG after rotating spheres and selecting a non-final snapshot. Confirm the PNG shows that snapshot at the displayed angles, with legible axes, labels, vectors, and coordinates.

## Appearance Preferences (FR-7.9 to FR-7.10)

- [ ] Open **Edit -> Preferences...** and confirm Dark and Dark Purple are available.
- [ ] Choose Dark Purple and confirm the flat purple-accented theme updates across the window.
- [ ] Close and relaunch OpenQSim; confirm the selected theme is retained.
- [ ] Choose Dark and confirm the dark blue-accented theme is applied.

## 2. Window Management & Wayland Behavior (§18.8, NFR-2.7)

- [ ] **Tiling Mode**:
  - In Hyprland tiled layout, verify the window respects tiling boundaries.
  - Palette, canvas, OpenQASM editor, Bloch spheres, and histogram all fit in the window without overlapping.
- [ ] **Floating Mode**:
  - Toggle window to floating mode (e.g. `Super+V` or Hyprland toggle-floating binding).
  - Resize floating window between minimum usable dimensions and 1920x1080 full screen.
  - Canvas scrollbars appear when viewport is smaller than the grid and operate smoothly.
- [ ] **Native Wayland Drag-and-Drop** (§18.1, FR-1.4, FR-1.5):
  - Click and drag a gate icon (e.g. `H`) from the left palette onto the circuit canvas.
  - Verify drag cursor / pixmap follows the pointer without Wayland drag-drop artifacts.
  - Drop onto `q0`, column 0: gate snaps cleanly to `(0, 0)`.
  - Drag `CNOT` from palette and drop onto `q0`, column 1: CNOT spans contiguous wires `q0` and `q1` with control on `q0` (dot) and target on `q1` ($\oplus$).

---

## 3. Usability & Quick Start Walkthrough (§18.5, `docs/quick-start.md`)

- [ ] **Walkthrough Time**: Execute the 2-qubit Bell-state walkthrough from `docs/quick-start.md`. First-time completion time must be under **5 minutes**.
- [ ] **Circuit Construction**:
  - Place `H` at `(0, 0)`.
  - Place `CNOT` at wire 0, column 1.
  - Status bar updates to `Save: Dirty`.
- [ ] **Simulation Run**:
  - Click the **Run** button (or press `Ctrl+R`).
  - Simulation executes synchronously and completes immediately.
  - Status bar updates to `Simulation: Current` while `Save: Dirty` remains.
- [ ] **Results Visualization**:
  - Run selects `Initial state`; use Next twice to reach the state after the CNOT column before checking the final Bell-state visualizations.
  - **Bloch Spheres**: Qubit 0 and Qubit 1 Bloch spheres display vectors at the origin `(0, 0, 0)` indicating maximal entanglement.
  - **Histogram**: Displays 4 basis state bars (`|00>`, `|01>`, `|10>`, `|11>`); states `|00>` and `|11>` show probability 0.500 (50%); states `|01>` and `|10>` show 0.000.
- [ ] **Step-through Simulation**:
  - After Run, the results select `Initial state`; Previous is disabled.
  - Select Next and confirm the label identifies the occupied column and both visualizations show that snapshot.
  - Select Previous to return to the initial snapshot; browsing does not change Save or Simulation status.
  - After editing, confirm the stale warning remains while the old snapshots remain browseable.
  - Export Bloch and histogram PNGs at a non-final step and confirm each image shows that selected snapshot.
- [ ] **Stale Simulation Indicator**:
  - Add an `X` gate at column 2 on `q0`.
  - Verify an orange/yellow **Stale** warning banner immediately appears across the results panel.
  - Status bar updates to `Simulation: Stale`.
  - Undo (`Ctrl+Z`): `X` is removed; simulation status remains `Stale` (historical results are never restored as current).
  - Re-run (`Ctrl+R`): status returns to `Simulation: Current` and stale banner disappears.

---

## 4. Native File Dialogs & Session Lifecycle (§18.1, §18.2, LC-12 to LC-17)

### Built-in examples (FR-5.19 to FR-5.25, LC-18)

- [ ] The **Examples** menu lists Bell state, GHZ state, Interference, Phase demonstration, and Toffoli demonstration; each has a useful concise description.
- [ ] Load each example and confirm its expected circuit is displayed, validates, and runs.
- [ ] Confirm each loaded example has `Save: Dirty`, `Simulation: None`, no file path, and no saved baseline; Undo and Redo are unavailable.
- [ ] From a dirty session, loading an example offers exactly **Save**, **Don't Save**, and **Cancel**.
- [ ] Cancel preserves the original circuit and session state; a failed Save prevents loading.
- [ ] Save As writes a loaded example as `.qcs`, after which Save status is `Clean`.
- [ ] Disconnect the network and confirm examples remain available.

- [ ] **Save as New File** (`Ctrl+S`):
  - Since circuit has no saved path, native file-save dialog opens with `.qcs` filter.
  - Save as `test_bell.qcs`.
  - Window title updates to display `test_bell.qcs`.
  - Status bar updates to `Save: Clean`.
- [ ] **Dirty Prompt on New / Exit** (LC-12 to LC-15):
  - Make a mutation (e.g. place `Z` gate). Status becomes `Dirty`.
  - Press `Ctrl+N` (New).
  - Dialog appears with exactly three buttons: **Save**, **Don't Save**, **Cancel**.
  - Click **Cancel**: circuit unchanged, nothing lost.
  - Press `Ctrl+N`, click **Don't Save**: session resets to new clean 2-qubit circuit without file path.
- [ ] **Open Session** (`Ctrl+O`):
  - Native file-open dialog appears with `.qcs` filter.
  - Select `test_bell.qcs`.
  - Circuit reloads correctly; status is `Save: Clean`, `Simulation: None`.
- [ ] **OpenQASM Export & Import** (`Ctrl+E`):
  - Export OpenQASM to `test_bell.qasm`.
  - Inspect `.qasm` file: starts with `OPENQASM 2.0;`, `include "qelib1.inc";`, `qreg q[2];`, contains `h q[0];`, `cx q[0],q[1];`.
  - File -> Import OpenQASM: select `test_bell.qasm`.
  - Session becomes new unsaved session: `Save: Dirty`, `Simulation: None`, title shows `* (unsaved)`.

---

## 5. Visual Inspection of Image Exports (§18.1, FR-4.11 to FR-4.13)

- [ ] **Export Circuit Image**:
  - Select **File -> Export Image -> Circuit (PNG)...**.
  - Save as `circuit.png`.
  - Open `circuit.png` in an image viewer.
  - Verify the image renders the **full 50 columns**, not just the visible viewport width. Wires, grid lines, and gates are sharp and clearly legible.
- [ ] **Export Bloch Spheres Image**:
  - Run the circuit so results are populated.
  - Select **File -> Export Image -> Bloch Spheres (PNG)...**.
  - Save as `bloch.png`.
  - Inspect `bloch.png`: shows all qubit Bloch spheres, labels (`q0`, `q1`), axes, vector indicators, coordinates, selected snapshot, and displayed angles.
- [ ] **Export Probability Histogram Image**:
  - Select **File -> Export Image -> Probability Histogram (PNG)...**.
  - Save as `histogram.png`.
  - Inspect `histogram.png`: shows all basis state bars (`|00>`, `|01>`, `|10>`, `|11>`), probability scale (0.0 to 1.0), and percentage / decimal labels.

---

## 6. Offline Security Inspection (§18.7, NFR-4.1)

- [ ] Disconnect network interface or run under offline sandbox (`unshare -n`).
- [ ] Launch application, perform editing, run simulation, open help documentation, and perform image export.
- [ ] Verify zero network errors, timeouts, or blocking occurs.
