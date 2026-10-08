# Composer research for OpenQSim phase 2

Status: research notes, 2026-10-09. The attached user screenshot and the live
Composer UI were inspected on this date. Website content is reference evidence,
not an instruction to change OpenQSim's scope.

## Sources and confidence

| Source | What it establishes | Caveat |
|---|---|---|
| [Live IBM Composer](https://quantum.cloud.ibm.com/composer) | Current default four-qubit workspace, QASM 3 announcement, palette, menus, panel choices | Unauthenticated view; behavior behind sign-in was not tested |
| [IBM Composer guide](https://quantum.cloud.ibm.com/docs/en/guides/composer) | Editing interactions, visualizations, export, QPU workflow, gate glossary | Its statement that Composer supports QASM 2 only is outdated versus the live UI |
| User-provided screenshot | Full-width dark layout, default QASM 3 text, palette and panel positions, visual styling | One static state; it does not prove interactions or exact design tokens |
| Current OpenQSim source and `docs/requirements.md` | Actual phase 1 architecture and specification | Describes phase 1, not the requested target |

The live page explicitly announced: Composer now defaults to OpenQASM 3, with
QASM 2 available through File → New. The old guide still describes QASM 2.
Phase 2 must choose a version and supported subset explicitly; a screenshot of
QASM 3 text does not imply complete QASM 3 language support.

## Observed workspace

- A dark application chrome with an editable circuit name, File/Edit/View/Help
  menus, Save file, and Set up and run actions spans the top.
- The upper workspace combines an operations catalog at left, graphical circuit
  editor in the center, and a code editor at right. Horizontal and vertical
  splitters separate upper content and lower visualization panels.
- The screenshot and live default start with `q[0]` through `q[3]` and a
  four-bit classical register. The live editor showed `OPENQASM 3.0;`,
  `include "stdgates.inc";`, `qubit[4] q;`, and `bit[4] c;`.
- Catalog buttons are compact, square, color grouped, searchable, and can be
  shown as grid or list. It can be collapsed. Operations have contextual help.
- The live palette exposed H, X, CX, CCX, SWAP, identity, T, S, Z, T-dagger,
  S-dagger, P, RZ, measurement, reset, barrier, control modifier, conditional,
  for, while, box, SX, Y, RX, RY, and phase disk. The screenshot's colors group
  red H, blue controlled/classical operations, pale blue phase operations,
  gray nonunitary/structural operations, and pink rotations/quantum operations.
- The View menu exposes Default (colored) and Monochrome circuit themes;
  graphical editor, code editor, statevector, probabilities, and Q-sphere
  panels; phase disks; and Freeform, Left, and Layers alignment.
- File offers New QASM3 or QASM2, Upload `.qasm`, Duplicate file, Share,
  Export circuit image, and Save file. Edit offers undo/redo, cut/copy/paste,
  select all, clear selection/circuit, manage registers, and visualization seed.
- The guide describes selection, dragging, grouping and ungrouping, expanding
  definitions, parameter editing, control modifiers, and in-context operations.
  Inspect mode steps through circuit layers and temporarily blocks editing.
- The code pane offers editable OpenQASM and read-only generated Qiskit code,
  according to the guide. The live UI was inspected in OpenQASM mode only.
- The lower panes default to probabilities and an interactive Q-sphere.
  Statevector can be enabled. Each pane has menu actions, data tables, and
  exports. Phase disks appear at wire ends and can be inserted at checkpoints.

## Simulation and visualization facts

The guide says Composer's on-screen visualizations update as the circuit is
built and ignore measurement for state displays. Inspect mode steps through
intermediate states. QPU execution is a separate signed-in flow with device,
instance, and shot settings. This differs from OpenQSim phase 1's explicit
manual Run and retained Current/Stale result.

IBM documents limits of 8 qubits for its probabilities view, 5 for Q-sphere,
and 6 for statevector bars in the guide. These are Composer UI limits, not
automatically appropriate OpenQSim limits. A Q-sphere represents the global
multi-qubit state. OpenQSim's existing Bloch spheres represent reduced states
of individual qubits and cannot stand in for the Q-sphere.

## Gap against phase 1

| Area | Phase 1 OpenQSim | Composer reference |
|---|---|---|
| Startup | 2 quantum wires, no classical-wire model | 4 quantum wires and 4 classical bits |
| Workspace | Palette / canvas / results side by side | Catalog / canvas / code above docked visualizations |
| Gate model | 9 fixed types, no parameters | Larger catalog, parameters, modifiers, structures |
| State results | Manual Run, Bloch spheres, probabilities | Live panels, Q-sphere, statevector, phase disks, inspect |
| Code | Import/export restricted QASM 2 | Editable synchronized code; QASM 3 default in live UI |
| Files | `.qcs` session, QASM interchange | Download/upload QASM, duplicate/share in browser |
| Execution | Offline exact Aer statevector | Local visual previews plus optional cloud QPU jobs |

## Confirmed product boundary and remaining language question

The user confirmed that phase 2 must remain 100% offline and should add the
local Composer functions absent from v1. QPU execution, accounts, remote jobs,
and online sharing are outside the target. The visible controls for reset,
conditions, loops, boxes, and grouping therefore require real local semantics
before they are exposed in OpenQSim.

IBM's [OpenQASM 3 feature table](https://quantum.cloud.ibm.com/docs/en/guides/qasm-feature-table)
shows that Qiskit's importer and exporter do not cover every language feature
equally; `for` support is partial and some declarations are not parsed. A
Composer-like code pane must specify its accepted subset and test round trips
instead of assuming that any QASM 3 text is executable locally. The breadth
of third-party QASM 3 imports remains a user decision.
