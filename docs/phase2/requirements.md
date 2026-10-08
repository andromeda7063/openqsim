# OpenQSim phase 2 — Composer-inspired requirements (draft)

Status: **proposal for user review**, 2026-10-09. This is a new
`requirements.md` for the next iteration, not the current implementation
baseline. Phase 1 remains governed by [`../requirements.md`](../requirements.md)
until this document is adopted. Evidence and uncertainties are recorded in
[`research.md`](research.md); proposed deltas are in [`changes.md`](changes.md).

## 1. Product goal and fidelity target

P2-GOAL-1. At the reference 1920×1080 native Wayland desktop size, the app
should closely resemble the supplied Composer screenshot in layout, density,
colors, gate glyphs, typography, and panel placement. Exact IBM branding,
legal/footer links, and browser-specific account chrome are not required.

P2-GOAL-2. Add the Composer functions missing from v1 that can operate
locally: circuit creation/editing, the visible operations catalog, code
synchronization, grouping, inspection, live visualizations, exports, and
keyboard behavior. A visible operation must have working simulation,
validation, persistence, and code semantics; unsupported language constructs
must be rejected clearly.

P2-GOAL-3. The application must remain **100% offline**. All computation,
visualization, file handling, help, preferences, and code conversion happen
locally. It must make no runtime network requests and have no QPU, account,
remote job, or sharing workflow. A Composer-like run control runs a local
simulator only.

### Settled scope and remaining questions

| ID | Status | Requirement or question |
|---|---|---|
| D1 | Resolved by user | 100% offline; no cloud QPU, accounts, jobs, sharing, or runtime network access |
| D2 | Proposed from live Composer | QASM 3 default, with QASM 2 as a selectable document/import/export dialect |
| D3 | Proposed from Composer parity | Live local previews plus a separate explicit local shot run |
| D4 | Resolved in scope | Implement the local semantics of every exposed catalog operation, including reset, mid-circuit measurement, conditions, loops, boxes, and custom gates |
| D5 | Proposed | Keep v1 Bloch spheres as an optional extra panel alongside Composer's Q-sphere |
| D6 | Open | Keep 1–10 simulated qubits or raise the limit; remove the 50-column editor limit |
| D7 | Open | Accept the Composer-generated QASM 3 subset or broader OpenQASM 3 programs? |

The requirements below specify the offline feature target. D6–D7 and exact
grammar, safety bounds, and lifecycle rules remain to be finalized before
the draft becomes authoritative.

## 2. Platform and architecture

P2-NFR-1. Continue source-run Python 3.13, PySide6, Qiskit, Qiskit Aer, uv,
and the CachyOS/Hyprland native Wayland test target. Editing, simulation,
persistence, help, preferences, and code conversion must work without network
access. The running app must never make network requests, check for updates,
download assets, or send telemetry.

P2-NFR-2. Preserve `libqsim` as a Qt-free domain/application/simulation/file
layer. GUI widgets render state and dispatch commands; they do not own circuit
semantics, saved baseline, validation, or undo history.

P2-NFR-3. Every edit, including code-pane replacement and parameter changes,
uses the session candidate → validate → commit pipeline. Failure leaves the
last valid circuit, history, file path, and results unchanged and gives an
actionable error. Successful multi-object actions add one undo step. No-ops add
none. Undo/redo and dirty status use semantic circuit equality.

P2-NFR-4. The UI must remain usable at 1920×1080 with four quantum wires,
catalog, canvas, code editor, probabilities, and Q-sphere visible at once.
Splitters and hidden panels must not strand editing actions or make wires
unreachable. Verify tiled and floating Wayland windows.

P2-NFR-5. Menus, tooltips, focus, shortcuts, text contrast, and non-color gate
labels must support keyboard access and distinguish operations without relying
only on color. Gate glyphs may be custom drawn but require text equivalents.

## 3. Workspace and visual design

P2-UI-1. Provide a compact header with editable circuit name, File/Edit/View/
Help menus, Save, and a prominent local simulation action. Show unsaved and
simulation state without obscuring the Composer-like layout.

P2-UI-2. Use a resizable left operations catalog, central horizontal-wire
canvas, right code pane, and lower resizable visualization panes. Initial
layout follows the screenshot: catalog about 15% of total width, code pane
about 19%, upper canvas about 66%, and lower panes roughly half
each. These are starting proportions, not hard minimums.

P2-UI-3. Default appearance is dark. Proposed design tokens sampled from
unobstructed pixels of the supplied screenshot are **subject to visual QA**;
surfaces vary across its subtle gradient:

| Token | Draft value | Use |
|---|---|---|
| `surface.canvas` | `#24292c` to `#332d2e` | editor dark base with soft warm gradient |
| `surface.panel` | `#262b2e` | catalog and visualization panes |
| `surface.header` | `#282c2e` | top bars |
| `line.divider` | `#5f5f61` | pane borders and splitters |
| `line.wire` | `#3e4044` | quantum wires |
| `text.primary` | `#e5e7e8` | primary labels |
| `text.muted` | `#9aa2a6` | register labels, axes |
| `action.primary` | `#1962ee` | primary button and focus |
| `gate.hadamard` | `#e54a52` | H tile |
| `gate.classical` | `#4380ea` | X/CX/CCX/SWAP/I family |
| `gate.phase` | `#acd4ea` | T/S/Z/P/RZ and inverses |
| `gate.other` | `#ea76a9` | SX/Y/RX/RY family |
| `gate.structure` | `#979da3` | reset, barrier, conditional, loop, box |

P2-UI-4. Support light/dark workspace appearance and default-colored/
monochrome gate themes as separate settings. Preserve readable contrasts in
every combination. Remember panel visibility, split sizes, theme, and catalog
mode locally; provide Reset workspace.

P2-UI-5. Catalog supports search, grid/list switch, collapse, drag/drop, and
contextual gate information. A selected operation opens an edit/info panel
with operands, parameter values, and a short definition.

P2-UI-6. Canvas shows quantum wires labeled `q[i]` in index order and a
classical register/wire when needed. Gate symbols, control dots, target marks,
connectors, measurement links, and phase disks should visually match the
reference at normal scale. Zoom/scroll preserve exact hit testing.

## 4. Circuit model and editing

P2-ED-1. Proposed startup is an untitled, empty 4-qubit circuit with 4
classical bits. New QASM 3 and New QASM 2 choose the code dialect of the
document. The file title and dialect are saved document state.

P2-ED-2. Qubit 0 remains the top wire and least-significant bit. Basis labels
show the highest-indexed bit on the left. Circuit execution order is explicit
and independent of visual alignment. Simultaneous disjoint operations may
share a layer; overlapping operations must have a defined order.

P2-ED-3. Add/remove qubits and classical bits through wire context actions
and Manage registers. Edits that would remove occupied wires or referenced
bits require a preview and explicit confirmation. Rejection or cancellation
preserves the full document state.

P2-ED-4. Placement, drag movement, click/Shift-toggle selection, marquee,
cut/copy/paste, duplicate, delete, select all, and keyboard nudging act on
whole logical operations. A group move may occupy cells it vacates. Invalid
candidate arrangements change nothing. Selection and layout changes do not
dirty the circuit.

P2-ED-5. Freeform preserves user placement. Left compacts operations while
preserving execution order. Layers shows ordered layer boundaries. Alignment
is a view choice unless the user explicitly requests a structural reorder.
Switching alignment must not alter simulation, saved semantic content, or
undo history.

P2-ED-6. A control modifier or operand editor may attach controls to a
supported unitary gate on nonadjacent wires. The editor must render the full
span and validate actual occupied wires and connector crossing rules. CX/CCX
may have any target wire, preserving phase 1 semantics.

P2-ED-7. Parameter editing accepts finite numeric angles and safe expressions
made from numbers, `pi`, parentheses, and `+ - * /`. Reject names, function
calls, non-finite values, and division by zero. Store canonical numeric values
and display a human-readable expression when available. The exact persistence
form remains to be fixed in the QCS v2 specification.

P2-ED-8. Group/ungroup, expand/collapse definition, and named custom unitary
operations work both from a selection and from supported OpenQASM code.
Definitions are scoped to the current circuit, reusable in its catalog,
editable without corrupting existing instances, and preserved by a file
round trip. Renaming updates the catalog and instances. Deleting a definition
shows how many instances will be removed and requires confirmation.

## 5. Operations and semantics

P2-GATE-1. Required first expansion: H, X, Y, Z, S, Sdg, T, Tdg, I, SX,
SXdg, P(theta), RX(theta), RY(theta), RZ(theta), CX, CCX, SWAP,
Measurement. Preserve Qiskit control-first argument ordering and basis order.
Implement simulation, validation, copy/move, persistence, code mapping, glyph,
tooltip, and tests for every exposed operation.

P2-GATE-2. `P`, `RX`, `RY`, and `RZ` default to `pi/2` on palette drop, and
their parameters remain editable. Angles follow Qiskit's gate definitions;
global phase must be retained where required by statevector/Q-sphere views.

P2-GATE-3. Barrier and phase disk are visual/checkpoint structures with
explicit semantics. Barrier never changes state; a phase disk displays the
state after the preceding layer. Both are usable palette items and round trip
through the adopted document format. QASM export preserves barriers; it
explicitly warns that phase disks are local visual annotations and omits them
from QASM, which has no equivalent operation.

P2-GATE-4. Reset, mid-circuit Measurement, conditions, `for`, `while`, and
`box` are required local operations. They require true classical-bit mapping,
branch/shot semantics, bounded execution, inspect behavior, and file/code
round trips. A condition evaluates actual classical results. A `for` repeats
its body over a finite range; a `while` has a documented finite execution
limit and reports when the limit is reached. A box preserves its block
boundary and contained operations. Do not model these as unitary gates or
ignore them in a result labeled as full circuit execution.

P2-GATE-5. Validate target/control counts, duplicate operands, bounds,
same-layer conflicts, parameter arity and values, classical references,
measurement ordering, and any group/structure boundaries. Errors identify the
offending operation and remain plain-language.

## 6. Code editor and files

P2-CODE-1. A docked code editor shows the current document as OpenQASM with
syntax highlighting and line numbers. Its text and graphical circuit are
synchronized. Applying valid code is one atomic history step; invalid text
shows line/column diagnostics and preserves the last valid circuit and
visualizations. Keep an invalid text draft visibly distinct from the last
valid circuit until the user fixes or discards it. Saving or exporting that
draft is blocked so the written file cannot silently differ from the editor.

P2-CODE-2. OpenQASM 3 is the proposed default, matching the live Composer
page; QASM 2 remains an explicit document/import/export option. The parser
must support all adopted catalog operations that the selected dialect can
represent and define its accepted grammar precisely. If a document contains
an operation that QASM 2 cannot faithfully represent, switching or exporting
to QASM 2 fails with an actionable explanation. No conversion may silently
discard operations or execute arbitrary include files or Python.

P2-CODE-3. A read-only Qiskit code tab generates equivalent source for
inspection/export. It must state the required dependency versions and must
not execute pasted Python. Its presence is UI parity; editable Qiskit Python
is outside the offline target.

P2-FILE-1. Keep local `.qcs` as the primary editable session format. Create a
versioned v2 schema for title, code dialect, quantum/classical register sizes,
gate parameters, operation order, and any adopted structural features. Read
v1 files without reinterpreting them. A failed load leaves the complete
current session unchanged. Do not write v2 features into a v1 file.

P2-FILE-2. Offer New, Open `.qcs`, Save/Save As, Import `.qasm`, Export `.qasm`,
Duplicate, Export circuit image, and visualization exports. Save of a new
document opens a local file dialog. QASM import/export must not silently
change the active `.qcs` path. Dirty prompts and baseline comparison need
updated lifecycle rules before adoption.

P2-FILE-3. Circuit image export offers preview, PNG/SVG, light/dark and
monochrome variants, and optional wrap. Visualization images and underlying
tables offer formats that each view can represent faithfully. Errors use the
standard user-facing mechanism.

## 7. Simulation and visualizations

P2-SIM-1. The headless simulation API remains authoritative and validates
before executing. Purely unitary circuits use exact noiseless statevector
simulation. Circuits with reset, measurement, and classical control use a
local dynamic simulation mode that follows their actual semantics and returns
sampled classical outcomes for a user-selected shot count. No statevector
result may claim to include an operation it omitted.

P2-SIM-2. Live local previews update after a valid committed edit, with a
visible busy/error state and no GUI freeze at the supported qubit limit.
An explicit local Run produces sampled counts for a selected shot count.
Preview and run results are labeled so deterministic probabilities are not
confused with sampled measurement counts. No automatic edit may submit a
job or contact a remote service.

P2-SIM-3. For a circuit with branching or nonunitary operations, preview
panels must either show a mathematically valid mixed-state/branch result or
state clearly that a pure-state view is unavailable at that step. Local shot
runs still execute the complete circuit. The precise preview algorithm and
performance bounds must be fixed in the simulation specification.

P2-VIS-1. Probabilities show every basis state (subject to an explicit
performance limit), with percent scale, tooltips, table view, and export.
Statevector shows amplitude magnitude and phase for each basis state plus a
complex-value table. Both use the phase 1 bit-order convention.

P2-VIS-2. Q-sphere is a separate global-state visualization: basis states
appear by Hamming-weight latitude; marker size reflects probability and
color reflects relative phase. It supports rotate, reset camera, state/phase
labels, legend, table, and export. Keep the existing per-qubit Bloch spheres
as an optional educational panel; they cannot substitute for Q-sphere.

P2-VIS-3. Wire-end phase disks show each qubit's local probability, relative
phase where defined, and reduced purity. Mixed reduced states must be visibly
distinguished. In-circuit phase disks are checkpoints, not quantum gates.

P2-VIS-4. Inspect mode steps through execution layers from start to end and
updates every visible result panel and phase disk for the selected prefix.
Provide first/back/play/forward/last controls, breakpoint selection,
and a clearly marked current step. Editing is disabled while
Inspect is active and resumes on exit without altering circuit/history.

P2-VIS-5. Each panel has hide/show, resize, information, table, export, and
empty/error states. Data and images for a given step come from the same
simulation snapshot. State limits and fallbacks must be tested rather than
copied blindly from Composer's guide.

## 8. Lifecycle and acceptance gates

P2-LC-1. Before implementation, replace phase 1 LC-1–LC-17 with a complete
phase 2 lifecycle table covering startup, all mutations, code drafts,
live-preview success/failure, explicit Run, undo/redo, New/Open/Import,
Save/Save As, QASM dialect changes, duplicate, and exit. The saved baseline
must include every persisted document field.

P2-TEST-1. Add Qt-free tests for every gate matrix/operand mapping,
parameter validation, circuit equality, QCS v1→v2 migration, QASM 2/3
round trips, invalid code, and atomic session transitions. Include Bell,
SWAP, inverses, phase gates, rotations, nonadjacent controls, and Q-sphere
phase/probability fixtures.

P2-TEST-2. Add GUI tests for the four-region layout, drag/drop and selection
while scrolled, parameter editor, code sync, menu/panel state, inspect,
keyboard behavior, and image export. Include native Wayland manual checks at
1920×1080 in tiled and floating modes.

P2-TEST-3. Phase 2 acceptance requires the repository's mandated formatting,
lint, type, and test sequence in `AGENTS.md`, a reviewed screenshot comparison
against the supplied reference, and a documented trace from each adopted
requirement to code and verification.

## 9. Offline boundary and language safety

Cloud QPU execution, IBM login, remote jobs, online sharing, telemetry,
third-party downloads at runtime, arbitrary OpenQASM includes, arbitrary
Python execution, and unbounded loops are excluded. They must not appear as
working controls or dependencies. Exact IBM marks and links are not part of
the visual target. The editor may import only a documented, safe local QASM
subset; unsupported syntax gets diagnostics and cannot partially execute.
