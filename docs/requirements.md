# Open QSim --- Requirements Specification

## 1. Purpose

Open QSim is an offline PySide6 desktop application for constructing,
editing, validating, simulating, and visualising small quantum circuits.
The release is source-run and is not required to provide a packaged
installer or bundled executable.

The application is intended for educational and prototyping use. It
performs exact, noiseless statevector simulation on a classical
computer. It does not execute circuits on quantum hardware and does not
require network access.

This file is the implementation requirements baseline. It is
self-contained and does not depend on a private SRS being present in the
public repository.

## 2. Scope

### 2.1 In scope

Open QSim shall provide:

1.  A graphical quantum-circuit editor for 1--10 qubits and at most 50
    columns in the release editor.
2.  The gate set H, X, Y, Z, S, T, CNOT, Toffoli, and Measurement.
3.  Gate placement, deletion, movement, rectangular multi-selection,
    copy/paste, and keyboard editing.
4.  Undo and redo for circuit mutations.
5.  Structural circuit validation.
6.  Exact noiseless statevector simulation using Qiskit Aer.
7.  Per-qubit reduced-state Bloch-sphere visualisation.
8.  Full computational-basis probability histogram visualisation.
9.  PNG export of the circuit, Bloch-sphere view, and histogram view.
10. Local `.qcs` JSON session files.
11. OpenQASM 2.0 import and export for the explicitly supported subset.
12. A non-GUI simulation API suitable for automated testing.
13. A compact symbolic gate palette with tooltips.
14. An editable OpenQASM 2.0 view synchronized with the circuit, with syntax
    checking and explicit application of valid supported programs.
15. Local user documentation and gate tooltips.

The 50-column editor limit is release-specific. The canvas may scroll within
the release; a future revision may remove the finite 50-column limit
entirely, which is not a release requirement.

### 2.2 Out of scope

The first release shall not require:

-   quantum-hardware execution;
-   cloud execution;
-   network communication or telemetry;
-   noise or error models;
-   hardware transpilation or optimisation;
-   Qiskit Python-code import/export;
-   OpenQASM 3;
-   parameterized gates or symbolic parameters;
-   arbitrary-angle RX/RY/RZ gates;
-   custom gate definitions;
-   mid-circuit branching or classical control flow;
-   reset operations;
-   barriers;
-   multiple quantum-register declarations in imported OpenQASM;
-   multi-user accounts;
-   authentication;
-   collaboration;
-   production-scale circuit design;
-   dedicated Grover or Shor application features;
-   a packaged installer or bundled executable.

Grover or Shor may be constructed externally if the supported gate set
permits it, but neither algorithm is a release acceptance requirement.

## 3. Users

The primary user is a student, self-learner, hobbyist, or
quantum-computing enthusiast with basic familiarity with qubits and
quantum gates. Programming experience is not required.

An instructor or grader may also use the application to evaluate
functionality.

The application is single-user and offline.

## 4. Platform and technology constraints

### 4.1 Runtime

-   Python 3.13.
-   PySide6 / Qt 6.
-   Qiskit.
-   Qiskit Aer.
-   NumPy where required for numerical processing.

Exact tested dependency versions shall be pinned in the checked-in
project dependency/environment file. Release acceptance shall use those
pinned versions rather than unconstrained latest releases.

Arch-based distributions track the newest Python, so the pinned Python 3.13
interpreter shall be provisioned with a version manager (for example `uv` or
`pyenv`) in a project-local virtual environment rather than assumed to be the
system Python.

### 4.2 Supported platform

This release supports and is tested on a single platform:

-   CachyOS (Arch Linux based), x86_64;
-   Hyprland compositor, native Wayland session.

Windows, macOS, and other Linux distributions are not claimed or verified in
this release. Platform-specific wording elsewhere in this document (for
example the Cmd modifier on macOS) is retained for future portability but is
not part of release acceptance.

The application shall not require a network connection after its
pinned dependencies have been installed.

### 4.3 Hardware

Minimum supported memory: 4 GB RAM (a design target; release acceptance is
verified only on the reference machine below).

The reference environment, used for all acceptance and performance
measurements, is:

-   Lenovo laptop with an Intel Core i5-13420H (12 threads);
-   16 GB RAM;
-   Intel Raptor Lake-P integrated graphics (UHD Graphics);
-   a 1920x1080 display;
-   CachyOS under Hyprland (Wayland);
-   local execution;
-   no network dependency.

The 10-qubit limit is a user-interface and visualisation constraint, not
a claim about the maximum capability of the underlying statevector
simulator.

### 4.4 Display and layout

The release editor has a fixed 50-column limit. The circuit canvas may scroll
horizontally and vertically, and layout is verified at the reference
resolution of 1920x1080 (see NFR-2.7).

## 5. Quantum circuit model

### 5.1 Qubits

-   A circuit shall contain between 1 and 10 qubits inclusive.
-   Qubits shall be indexed `0` through `n-1`.
-   Qubit 0 shall be the top wire in the graphical circuit.
-   Qubit 0 shall be the least-significant bit in computational-basis
    indexing.
-   Basis-state labels shall place the highest-indexed qubit on the
    left.
-   Therefore, for a two-qubit circuit, `01` means q1 = 0 and q0 = 1.

### 5.2 Columns and gate occupancy

-   A gate placement shall have an integer column index from `0` through
    `49` inclusive.
-   Gates shall execute in increasing column order.
-   Multiple gates may occupy the same column only when they use
    completely different qubit wires.
-   At most one gate may occupy a given qubit wire in a given column.
-   A multi-qubit gate occupies every wire associated with its targets
    and controls.
-   A placement that overlaps another gate on any occupied wire and
    column is invalid.
-   CNOT and Toffoli shall occupy contiguous qubit wires in one column.
-   For CNOT, one occupied wire is the target and the other is the
    control. Either wire may be the target.
-   For Toffoli, one of the three occupied wires is the target and the
    other two are controls. Any of the three wires may be the target.
-   Gate semantics and OpenQASM argument order follow Qiskit: `cx` is
    written controls first, target last (`cx control,target`) and
    `ccx control1,control2,target`.
-   Multi-qubit gate moves and copies shall preserve these relative wire
    positions and target/control roles.

The 50-column limit is a release editor constraint. The canvas may scroll to
reach all columns. Future revisions may remove the finite limit entirely; no
future behavior is required by this release.

### 5.3 Supported gates

The release gate palette shall contain exactly:

  Gate            Targets   Controls
  ------------- --------- ----------
  H                     1          0
  X                     1          0
  Y                     1          0
  Z                     1          0
  S                     1          0
  T                     1          0
  CNOT                  1          1
  Toffoli               1          2
  Measurement           1          0

No other gate is required in the release palette.

The simulator shall use gate definitions consistent with Qiskit's
conventions.

### 5.4 Measurement

Measurement has deliberately simplified semantics in this release:

-   Measurement is a visual marker on one qubit wire.
-   Each qubit may contain at most one Measurement.
-   A Measurement shall be the final operation on its qubit wire.
-   A gate or second Measurement placed after an existing Measurement on
    the same wire is invalid and shall be rejected by the editor.
-   Measurement is not executed as a probabilistic state-collapse
    operation.
-   The simulator shall ignore Measurement when calculating the
    statevector.
-   The statevector therefore represents the pre-measurement quantum
    state.
-   Measurement shall be represented in OpenQASM using
    `measure q[i] -> c[i];` with a corresponding classical register.
-   An imported measurement is accepted only when it is the final
    operation on its qubit and no second Measurement exists on that
    qubit.

## 6. Functional requirements

### 6.1 Circuit creation and editing

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-1.1                  The system shall allow the user to   High
                          create a new empty circuit.

  FR-1.2                  A new circuit shall contain 2       High
                          qubits and no gate placements.

  FR-1.3                  The system shall allow the user to   High
                          set the circuit size to any integer
                          from 1 through 10 inclusive.

  FR-1.4                  The system shall allow the user to   High
                          add any supported gate to a valid
                          wire and column using drag-and-drop.

  FR-1.5                  Drag-and-drop shall be atomic. If the  High
                          entire gate cannot be placed at the
                          destination because of a boundary,
                          collision, Measurement rule, or other
                          validation rule, the placement shall be
                          rejected, the circuit shall be unchanged,
                          no undo entry shall be created, and the
                          standard error mechanism shall report the
                          reason.

  FR-1.6                  The system shall allow the user to delete  High
                          selected gate placements.

  FR-1.7                  The system shall allow the user to move   High
                          selected gates to another valid wire and
                          column.

  FR-1.8                  A move shall be atomic. If any selected   High
                          gate would be outside the circuit bounds,
                          violate a collision rule, violate the
                          Measurement rule, or otherwise be invalid,
                          the entire move shall be rejected; all
                          selected gates shall remain unchanged and
                          no undo entry shall be created.

  FR-1.9                  Multi-qubit gates shall be atomic editor   High
                          objects. Their controls, targets, relative
                          wire positions, and contiguous-wire
                          arrangement shall always move and copy
                          together.

  FR-1.10                 The system shall allow the user to clear   High
                          all gate placements from the current
                          circuit.

  FR-1.11                 The system shall re-render the circuit     High
                          diagram after every successful circuit
                          edit.

  FR-1.12                 The system shall support undo and redo of  High
                          successful circuit mutations.

  FR-1.13                 Each successful circuit mutation shall    High
                          create exactly one undo-history entry.

  FR-1.14                 Run, Save, Save As, Load/Open, Import,    High
                          Export, selection changes, and other
                          non-mutating UI operations shall not create
                          undo-history entries.

  FR-1.15                 A successful New, Load/Open, or Import     High
                          operation shall clear both undo and redo
                          history. A failed operation shall not clear
                          history.
  -----------------------------------------------------------------------

### 6.2 Qubit resizing

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-1.16                 Increasing the qubit count shall add  High
                          empty wires without changing existing
                          gate placements.

  FR-1.17                 If decreasing the qubit count would      High
                          remove gates referencing deleted qubits,
                          the system shall display a confirmation
                          identifying that affected gates will be
                          removed.

  FR-1.18                 If the user cancels a destructive resize, High
                          the circuit shall remain unchanged.

  FR-1.19                 If the user confirms a destructive resize, High
                          all gate placements referencing removed
                          qubits shall be deleted and the resize shall
                          be recorded as one undoable mutation.
  -----------------------------------------------------------------------

### 6.3 Selection, copy, and paste

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-1.20                 The system shall support rectangular     High
                          marquee selection across circuit wires
                          and columns.

  FR-1.21                 A click on a gate shall replace the      High
                          current selection. Holding Ctrl on
                          Windows/Linux or Cmd on macOS shall add
                          an unselected gate to the selection or
                          remove a selected gate from it.

  FR-1.22                 A marquee selection shall replace the    High
                          current selection unless Ctrl/Cmd is held,
                          in which case it shall add/remove the
                          intersected gate objects from the current
                          selection according to the selection state.

  FR-1.23                 A multi-qubit gate shall never be          High
                          partially selected. If a selection
                          intersects a multi-qubit gate, the complete
                          gate shall be selected.

  FR-1.24                 The system shall support copying the       High
                          selected circuit elements.

  FR-1.25                 The system shall support pasting the       High
                          copied selection at a user-selected
                          destination cell.

  FR-1.26                 The clicked destination cell shall be the  High
                          top-left anchor of the pasted selection.
                          The copied selection shall retain its
                          internal shape and relative positions, with
                          its minimum selected qubit/column translated
                          to the clicked destination qubit/column.

  FR-1.27                 Copy/paste shall preserve the relative     High
                          qubit positions, columns, gate types,
                          targets, controls, and atomic multi-qubit
                          gate structure of the copied elements.

  FR-1.28                 A paste shall be rejected if any           High
                          destination placement is outside the 1--10
                          qubit or 50-column editor bounds, conflicts
                          with an existing gate, violates a
                          Measurement rule, or violates any other
                          circuit validation rule.

  FR-1.29                 A rejected paste shall leave the circuit   High
                          unchanged, shall not create an undo-history
                          entry, and shall report the reason using the
                          standard error mechanism.

  FR-1.30                 A successful paste shall create exactly    High
                          one undo-history entry.
  -----------------------------------------------------------------------

### 6.4 Keyboard shortcuts

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-1.31                 The system shall support Ctrl+Z for undo  Medium
                          and the equivalent platform-native
                          modifier on macOS.

  FR-1.32                 The system shall support Ctrl+Y for redo  Medium
                          where the platform uses Ctrl-based
                          shortcuts, with the equivalent platform-native
                          command where applicable.

  FR-1.33                 The system shall support Ctrl+C for copy.  Medium

  FR-1.34                 The system shall support Ctrl+V for paste. Medium

  FR-1.35                 The system shall support Delete or        Medium
                          Backspace for deleting the current
                          selection.

  FR-1.36                 The system shall support Ctrl+A for       Medium
                          selecting all circuit elements.

  FR-1.37                 The system shall support arrow keys for   Medium
                          moving the current selection by exactly
                          one grid cell per key press: left/right
                          change the column by 1 and up/down change
                          the qubit index by 1.

  FR-1.38                 Any invalid arrow-key movement shall be    Medium
                          rejected atomically, leaving the entire
                          selection unchanged and creating no undo
                          entry.

  FR-1.39                 The system shall support Ctrl+S for Save.  Medium

  FR-1.40                 The system shall support Ctrl+O for        Medium
                          Load/Open.

  FR-1.41                 The system shall support Ctrl+N for New    Medium
                          Circuit.

  FR-1.42                 The system shall support Ctrl+Shift+S for  Medium
                          Save As.

  FR-1.43                 The system shall support Ctrl+E for        Medium
                          Export OpenQASM. Export image has no default shortcut.

  FR-1.44                 On platforms using a native command       Medium
                          modifier instead of Ctrl, the equivalent
                          platform-native modifier shall be
                          supported.
  -----------------------------------------------------------------------

### 6.5 Application state and lifecycle

The application shall track two independent statuses.

The application edits a single `.qcs` session consisting of a circuit, an
optional current file path, and an optional saved baseline. A session that has
no saved baseline is always `Dirty`.

**Save status** shall be either:

- `Clean` — the session has a saved baseline and the current circuit
  definition equals it (equality as defined in Section 14.1).
- `Dirty` — the session has no saved baseline, or the current circuit
  definition differs from it.

**Simulation status** shall be either:

- `None` — there is no successful simulation result currently retained.
- `Current` — the retained simulation result was produced from the current
  circuit definition by the most recent successful Run.
- `Stale` — a retained simulation result exists, but it was produced from
  an earlier circuit definition.

The following lifecycle rules are normative. Sections 5.4, 16, 18, and 21
restate some of them for convenience; if a restatement conflicts with this
section, this section governs.

**LC-1.** At application startup, a new empty 2-qubit circuit is shown with
Save status `Clean` (that empty circuit is the saved baseline; there is no
file path) and Simulation status `None`.

**LC-2.** After every successful circuit mutation, Save status shall be
recalculated against the saved baseline: it is `Clean` when the current
circuit equals the baseline and `Dirty` otherwise. If a retained simulation
result exists, the mutation shall change Simulation status to `Stale`;
otherwise Simulation status remains `None`. An operation that leaves the
circuit definition unchanged is not a successful mutation (see FR-1.45).

**LC-3.** Undo and Redo update the circuit and recalculate Save status by
comparing the resulting circuit definition with the saved baseline.

**LC-4.** Undo and Redo make Simulation status `Stale` when a retained result
exists; they do not restore historical simulation results. Undo and Redo do
not create additional undo-history entries; they move the existing history
position.

**LC-5.** After Undo, a new successful mutation clears the redo history.

**LC-6.** Save and Save As write the current circuit and establish that exact
circuit definition as the new `Clean` baseline after a successful save.

**LC-7.** Run does not change Save status. A successful Run replaces the
retained simulation result and sets Simulation status to `Current`.

**LC-8.** A failed Run leaves the previously retained result, and its
Simulation status (`None`, `Current`, or `Stale`), unchanged. It reports the
failure using the standard error mechanism.

**LC-9.** New and successful Load/Open establish the resulting circuit as the
`Clean` saved baseline (New has no file path; Load/Open sets the file path),
clear simulation results so Simulation status becomes `None`, and clear both
undo and redo history.

**LC-10.** A successful Import OpenQASM replaces the current session with a
new unsaved `.qcs` session: the imported circuit, no file path, no saved
baseline, and therefore Save status `Dirty`. It clears simulation results so
Simulation status becomes `None` and clears both undo and redo history. The
`.qasm` file never becomes the session file.

**LC-11.** A failed Load/Open or Import OpenQASM operation leaves the current
circuit, Save status, Simulation status, and undo/redo history exactly
unchanged, and reports the failure using the standard error mechanism.

**LC-12.** When New, Load/Open, Import OpenQASM, or application Exit is
requested while Save status is `Dirty`, the user shall receive exactly three
choices: `Save`, `Don't Save`, and `Cancel`.

**LC-13.** `Save` shall first perform a successful save. If the save fails,
the requested New/Load/Import/Exit operation shall not proceed and the
current state shall remain unchanged. If the save succeeds, the requested
operation shall then proceed.

**LC-14.** `Don't Save` shall discard the unsaved changes and perform the
requested operation. If the requested operation then fails, LC-11 applies and
nothing is discarded.

**LC-15.** `Cancel` shall perform no operation and shall leave the current
application state unchanged.

**LC-16.** Save on a circuit that has no file path shall open the file-save
dialog.

**LC-17.** A successful Save As shall establish the selected path as the
current file path and establish the current circuit as the clean baseline.

### 6.6 Editing clarifications

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-1.45                 An operation that would leave the  High
                          circuit definition unchanged (for
                          example Clear on an empty
                          circuit, a zero-cell move, or
                          resizing to the current size) is
                          not a successful mutation: no
                          undo entry, no status change, and
                          no error.

  FR-1.46                 Collision and bounds checks for a  High
                          move shall be made against the
                          resulting arrangement: the
                          selected gates are first removed
                          from their original cells, so a
                          selection may move onto cells it
                          vacates but never onto unselected
                          gates.

  FR-1.47                 Arrow keys with an empty           Medium
                          selection, and Ctrl+V with an
                          empty clipboard, shall do nothing
                          and create no undo entry.

  FR-1.48                 Ctrl+V shall paste at the most     Medium
                          recently clicked cell; if no cell
                          has been clicked since the
                          circuit was created or loaded, it
                          shall paste at qubit 0, column 0.

  FR-1.49                 Dropping a CNOT or Toffoli on a    High
                          cell shall place it on contiguous
                          wires starting at the dropped
                          wire, which becomes its
                          lowest-indexed wire. By default
                          the controls occupy the upper
                          wires and the target occupies the
                          bottom (highest-indexed) wire,
                          matching `cx q[w],q[w+1]` and
                          `ccx q[w],q[w+1],q[w+2]`.

  FR-1.50                 The editor shall provide a Change  High
                          target command for a selected
                          CNOT or Toffoli: for CNOT it
                          swaps control and target; for
                          Toffoli it cycles the target
                          through the three wires. Each use
                          is one undoable mutation, and it
                          is rejected atomically if it
                          would violate any validation
                          rule.
  -----------------------------------------------------------------------

## 7. Validation requirements

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-2.1                  The system shall validate every gate     High
                          placement before simulation.

  FR-2.2                  Validation shall reject a target or      High
                          control qubit outside `0..n-1`.

  FR-2.3                  Validation shall reject duplicate        High
                          qubit references within one gate.

  FR-2.4                  Validation shall enforce the defined     High
                          target/control arity for every gate type.

  FR-2.5                  Validation shall reject two gates        High
                          occupying the same qubit wire and column.

  FR-2.6                  Validation shall reject a gate or second  High
                          Measurement placed after Measurement on
                          the same wire, and shall reject more than
                          one Measurement on a qubit.

  FR-2.7                  Validation shall reject a column index    High
                          outside `0..49`.

  FR-2.8                  Validation shall reject CNOT and Toffoli  High
                          placements whose occupied qubits are not
                          contiguous or whose target/control
                          arrangement does not follow Section 5.2.

  FR-2.9                  Validation shall return a list of         High
                          validation errors; an empty list means
                          that the circuit is valid.

  FR-2.10                 Each validation error shall identify the  High
                          offending placement and state the reason
                          in plain language.

  FR-2.11                 Validation errors shall not expose raw    High
                          Python exceptions or Qiskit stack traces.

  FR-2.12                 The Run operation shall not invoke the     High
                          simulator when validation fails.

  FR-2.13                 A failed validation shall leave the        High
                          circuit unchanged.
  -----------------------------------------------------------------------

## 8. Simulation requirements

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-3.1                  The system shall simulate every valid     High
                          supported circuit using the Qiskit Aer
                          statevector simulator.

  FR-3.2                  Simulation shall be exact noiseless        High
                          statevector simulation within the numerical
                          precision of the simulator and application.

  FR-3.3                  The system shall compute the probability    High
                          of every computational-basis state from the
                          resulting statevector.

  FR-3.4                  The system shall compute one reduced Bloch  High
                          vector for each qubit.

  FR-3.5                  Simulation shall execute only when the      High
                          user activates Run.

  FR-3.6                  The application shall not automatically     High
                          re-run the simulator after circuit edits.

  FR-3.7                  After a successful circuit mutation and     High
                          before the next successful Run, any retained
                          simulation result shall remain visible and
                          shall be marked stale.

  FR-3.8                  The application shall clearly indicate when High
                          the retained simulation result is stale
                          relative to the current circuit.

  FR-3.9                  The simulator shall execute gates in         High
                          increasing column order.

  FR-3.10                 Measurement markers shall not alter the     High
                          simulated statevector.

  FR-3.11                 Run shall execute synchronously on the       High
                          GUI thread. Temporary UI blocking during Run
                          is acceptable for this release.

  FR-3.12                 A failed Run shall leave the current circuit High
                          unchanged and shall preserve any previous
                          simulation result and its Simulation status.
  -----------------------------------------------------------------------

## 9. Visualisation requirements

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  FR-4.1                  The system shall        High
                          display one Bloch       
                          sphere for each qubit.  

  FR-4.2                  Each Bloch sphere shall High
                          identify the qubit to   
                          which it corresponds.   

  FR-4.3                  Each Bloch sphere shall High
                          show the X, Y, and Z    
                          axes.                   

  FR-4.4                  The reduced Bloch       High
                          vector shall be         
                          rendered as a point     
                          within or on the unit   
                          sphere.                 

  FR-4.5                  A pure single-qubit     Medium
                          state shall be          
                          represented on the      
                          sphere surface within   
                          numerical tolerance.    

  FR-4.6                  A mixed reduced state   High
                          may be represented      
                          inside the sphere.      

  FR-4.7                  The system shall        High
                          display the full        
                          computational-basis     
                          probability             
                          distribution as a       
                          histogram containing    
                          2\^n basis states.      

  FR-4.8                  Histogram basis-state   High
                          labels shall follow the 
                          defined                 
                          Qiskit-compatible bit   
                          ordering.               

  FR-4.9                  Histogram values shall  High
                          represent probabilities 
                          and shall be            
                          numerically normalised  
                          to sum to 1 within      
                          tolerance.              

  FR-4.10                 Bloch-sphere and        High
                          histogram views shall   
                          refresh after a         
                          successful Run.         

  FR-4.11                 The system shall allow  Medium
                          the user to export the  
                          circuit diagram as a    
                          PNG file.               

  FR-4.12                 The system shall allow  Medium
                          the user to export the  
                          Bloch-sphere view as a  
                          PNG file.               

  FR-4.13                 The system shall allow  Medium
                          the user to export the  
                          histogram view as a PNG 
                          file.                   

  FR-4.14                 The interface shall     Medium
                          provide concise         
                          explanatory text or     
                          tooltips describing     
                          what the Bloch sphere   
                          and histogram           
                          represent.              
  -----------------------------------------------------------------------

## 10. Session management

### 10.1 `.qcs` format

The `.qcs` file shall be JSON and shall contain at least:

``` json
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

The exact schema shall be documented in `docs/qcs-format.md`.

The schema shall not contain simulation results.

### 10.2 Session requirements

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  FR-5.1                  The system shall save the current        High
                          circuit to a `.qcs` JSON file.

  FR-5.2                  A saved circuit shall contain the qubit  High
                          count and all gate placements, including
                          gate type, targets, controls, and column.

  FR-5.3                  The `.qcs` file shall contain a            High
                          `schema_version` field.

  FR-5.4                  The system shall load a valid `.qcs` file  High
                          and reconstruct the same circuit definition.

  FR-5.5                  A save/load round trip shall preserve      High
                          qubit count and every gate placement exactly.

  FR-5.6                  Simulation results shall not be persisted High
                          in `.qcs` files.

  FR-5.7                  Loading a `.qcs` file shall not           High
                          automatically restore old simulation
                          results. A successful load shall clear any
                          retained simulation result and set Simulation
                          status to `None`.

  FR-5.8                  The system shall reject malformed `.qcs`  High
                          files without crashing.

  FR-5.9                  The system shall reject unsupported `.qcs` High
                          schema versions with a plain-language error.

  FR-5.10                 File read/write failures shall be reported High
                          using the standard error mechanism without
                          exposing raw exceptions.

  FR-5.11                 The system shall warn the user before New,   Medium
                          Load, Import OpenQASM, or application Exit when Save status is
                          `Dirty`, using exactly the choices `Save`,
                          `Don't Save`, and `Cancel`, with the lifecycle
                          behavior defined in Section 6.5.

  FR-5.12                 The system shall support Save As to a        Medium
                          user-selected `.qcs` path. A successful Save
                          As shall establish that path and the current
                          circuit as the clean baseline.

  FR-5.13                 Save on a circuit with no current file path  Medium
                          shall open the file-save dialog.

  FR-5.14                 A failed Load/Open shall leave the current   High
                          circuit, Save status, Simulation status, and
                          undo/redo history unchanged.

  FR-5.15                 The loader shall reject, without   High
                          crashing: a root value that is
                          not a JSON object, a missing
                          required field, unknown fields at
                          the root or in a gate placement,
                          and `num_qubits`, `column`, or
                          qubit indices that are not JSON
                          integers (floats and booleans
                          included).

  FR-5.16                 `schema_version` shall equal the   High
                          string `"1.0"` exactly; any other
                          value or type shall be rejected
                          as unsupported.

  FR-5.17                 Every gate placement shall have    High
                          exactly one target. `controls`
                          shall hold 0 entries for H, X, Y,
                          Z, S, T, and Measurement, 1 for
                          CNOT, and 2 for Toffoli.

  FR-5.18                 The writer shall emit canonical    Medium
                          order: placements by increasing
                          column, then lowest occupied
                          qubit, with `controls` ascending.
  -----------------------------------------------------------------------

## 11. OpenQASM 2.0 interoperability

### 11.1 Supported import subset

The importer shall accept only:

-   `OPENQASM 2.0;`
-   `include "qelib1.inc";`
-   one quantum register named `q`;
-   a quantum register containing at most 10 qubits;
-   zero or one classical register;
-   H, X, Y, Z, S, T, CX, CCX;
-   Measurement statements of the form `measure q[i] -> c[i];`;
-   when any Measurement statement is present, exactly one classical
    register named `c` containing exactly `n` bits, with measurements
    mapping one-to-one as `q[i] -> c[i]`.

The importer shall reject:

-   `sdg`;
-   `tdg`;
-   rotation gates;
-   custom `gate` definitions;
-   `if`;
-   `reset`;
-   `barrier`;
-   `opaque`;
-   multiple quantum-register declarations;
-   unsupported classical operations;
-   unsupported gate arguments, including whole-register operands such as
    `h q;`;
-   repeated, out-of-range, or non-contiguous `cx`/`ccx` operands;
-   a quantum register not named `q`;
-   a missing `include "qelib1.inc";`;
-   more than 10 qubits;
-   a second Measurement on the same qubit;
-   Measurement occurring before another operation on the same qubit;
-   Measurement statements whose classical target does not match
    `c[i]` for the measured `q[i]` under the required one-to-one mapping.

### 11.2 Requirements

  --------------------------------------------------------------------------
  ID                      Requirement                           Priority
  ----------------------- ------------------------------- -------------
  FR-6.1                  The system shall import valid files from   Medium
                          the supported OpenQASM 2.0 subset.

  FR-6.2                  The importer shall validate the OpenQASM    Medium
                          header, included library, register declarations,
                          supported operations, qubit limits, Measurement
                          mapping, and Measurement placement before
                          constructing the circuit.

  FR-6.3                  Unsupported OpenQASM constructs shall be    Medium
                          rejected with a plain-language error
                          identifying the unsupported construct.

  FR-6.4                  The system shall export the current         Medium
                          supported circuit as OpenQASM 2.0.

  FR-6.5                  Exported Measurement operations shall use   Medium
                          exactly one classical register `c[n]` when
                          any Measurement exists, with
                          `measure q[i] -> c[i];` for each measured q[i].

  FR-6.6                  Import/export shall preserve supported gate Medium
                          type, target qubits, control qubits, and
                          execution order. Exact editor column positions
                          are not required to survive an import/export
                          round trip.

  FR-6.7                  On export, operations shall be written in    Medium
                          increasing editor-column order; operations in
                          the same column shall be ordered by the
                          lowest-indexed qubit occupied by the operation.

  FR-6.8                  On import, each OpenQASM operation shall be   Medium
                          placed in the next editor column in statement
                          order. The first operation is placed in column
                          0, the second in column 1, and so on.

  FR-6.9                  Import/export shall use Qiskit-compatible    Medium
                          qubit ordering.

  FR-6.10                 The application shall not import or export    Medium
                          Qiskit Python source code. OpenQASM 2.0 is the
                          supported interchange format.

  FR-6.11                 A successful Import OpenQASM operation shall  Medium
                          replace the current session with the imported circuit as a
                          new unsaved `.qcs` session (no file path, Save
                          status `Dirty`), clear
                          any existing simulation result so Simulation
                          status becomes `None`, and clear undo/redo history.

  FR-6.12                 A failed Import OpenQASM operation shall      High
                          leave the current circuit, Save status,
                          Simulation status, and undo/redo history
                          unchanged and shall report the failure using the
                          standard error mechanism.

  FR-6.13                 OpenQASM `cx` and `ccx` shall use  Medium
                          Qiskit argument order: `cx
                          control,target;` and `ccx
                          control1,control2,target;`. On
                          import either `ccx` control order
                          is accepted and stored ascending;
                          on export controls are written
                          ascending, then the target.

  FR-6.14                 The importer shall require both    Medium
                          header lines, ignore `//`
                          comments and insignificant
                          whitespace, and accept a
                          classical register with no
                          Measurement statements (ignored,
                          not preserved on export).

  FR-6.15                 Every export shall begin with      Medium
                          `OPENQASM 2.0;`, `include
                          "qelib1.inc";`, and `qreg q[n];`,
                          followed by `creg c[n];` only
                          when at least one Measurement
                          exists.

  FR-6.16                 Importing OpenQASM shall create a  Medium
                          new unsaved `.qcs` session as
                          defined by LC-10; it shall never
                          make the `.qasm` file the session
                          file.
  --------------------------------------------------------------------------

## 12. User guidance

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  FR-7.1                  The application shall   Medium
                          provide a Quick Start   
                          guide showing           
                          construction and        
                          simulation of a 2-qubit 
                          Bell state.             

  FR-7.2                  The Quick Start guide   Medium
                          shall be sufficient for 
                          a first-time user to    
                          complete the Bell-state 
                          workflow within the     
                          5-minute usability      
                          target.                 

  FR-7.3                  Each gate in the        Medium
                          palette shall have a    
                          concise tooltip         
                          describing its          
                          function.               

  FR-7.4                  The application shall   Medium
                          provide concise         
                          explanations of the     
                          Bloch sphere and        
                          probability histogram.  

  FR-7.5                  The application shall   Medium
                          provide user            
                          documentation for the   
                          `.qcs` schema and       
                          supported OpenQASM 2.0  
                          subset.                 
  FR-7.6                  The circuit editor shall display standard gate symbols
                          on the circuit, and the compact gate palette shall
                          present symbolic icons with a tooltip for each gate.
                          The palette shall be arranged vertically.

  FR-7.7                  The main window shall place simulation results below
                          the circuit workspace, with the Bloch and probability
                          views available side by side.

  FR-7.8                  The main window shall show an editable OpenQASM 2.0
                          editor beside the circuit canvas. It shall display a
                          deterministic export of the current circuit, check
                          syntax as the text changes, report syntax and
                          supported-subset errors, and apply valid supported
                          programs to the circuit when requested.
  -----------------------------------------------------------------------

## 13. Non-functional requirements

### 13.1 Performance

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  NFR-1.1                 On the reference hardware, a valid     High
                          circuit containing up to 10 qubits and
                          50 gates, and a fully populated 10-qubit,
                          50-column circuit (500 single-qubit gates), shall
                          have its statevector,
                          basis probabilities, and Bloch vectors
                          computed within 2 seconds of Run
                          activation. Qt rendering time is excluded
                          from this measurement.

  NFR-1.2                 Circuit-edit handlers shall return     High
                          within 100 ms for circuits of up to
                          10 qubits. This applies to successful and
                          rejected editor mutations; rendering is
                          excluded from the timing boundary only when
                          explicitly measured separately.
  -----------------------------------------------------------------------

### 13.2 Usability

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  NFR-2.1                 A first-time user with no prior Open  High
                          QSim instruction shall be able to build
                          and simulate a 2-qubit Bell-state circuit
                          within 5 minutes.

  NFR-2.2                 Error messages shall use the standard  High
                          error mechanism, shall use plain language,
                          and shall not expose raw exceptions or
                          stack traces.

  NFR-2.3                 The main window shall keep the circuit  Medium
                          canvas and result visualisations accessible
                          without requiring separate application windows.

  NFR-2.4                 Target qubits, control qubits, and       Medium
                          Measurement markers shall use consistent
                          visual conventions.

  NFR-2.5                 Each qubit's circuit wire shall remain   Medium
                          visually associated with its corresponding
                          Bloch sphere.

  NFR-2.6                 The editor shall clearly communicate the  Medium
                          selected gate(s) and shall apply the
                          click/Ctrl/Cmd/marquee selection rules in
                          Section 6.3 consistently.

  NFR-2.7                 The circuit canvas shall provide   High
                          all qubit wires and all 50
                          columns and may scroll
                          horizontally and vertically. At
                          1920x1080 with the window filling
                          the screen, the palette, the
                          scrollable canvas, OpenQASM
                          editor, and access to the
                          Bloch-sphere and histogram views
                          shall all be available in the
                          same window. Simulation results
                          shall appear below the workspace.
                          Drag/drop,
                          selection, paste, and arrow-key
                          movement shall behave identically
                          for cells reached by scrolling,
                          and a moved or pasted selection
                          shall be scrolled into view.
  -----------------------------------------------------------------------

### 13.3 Reliability

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  NFR-3.1                 Malformed circuits, malformed `.qcs`  High
                          files, malformed OpenQASM input, and
                          unsupported OpenQASM constructs shall not
                          crash the application.

  NFR-3.2                 A failed simulation shall leave the     High
                          current circuit intact and the application
                          usable.

  NFR-3.3                 A failed save or load operation shall    High
                          leave the current in-memory circuit unchanged.

  NFR-3.4                 Failed editing mutations, including      High
                          invalid drag/drop, move, and paste, shall
                          be atomic: no partial mutation and no undo
                          entry.

  NFR-3.5                 Failed Load/Open and Import operations    High
                          shall preserve the complete pre-operation
                          application state as defined in Section 6.5.
  -----------------------------------------------------------------------

### 13.4 Security and privacy

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  NFR-4.1                 The application shall   High
                          perform no network      
                          communication during    
                          normal operation.       

  NFR-4.2                 The application shall   High
                          not transmit circuit    
                          data, simulation data,  
                          or user-created files   
                          to external services.   

  NFR-4.3                 No user account,        High
                          authentication system,  
                          or remote access        
                          mechanism shall be      
                          required.               
  -----------------------------------------------------------------------

### 13.5 Maintainability

  -------------------------------------------------------------------------------
  ID                      Requirement                     Priority
  ----------------------- ------------------------------- -----------------------
  NFR-5.1                 The circuit domain model and    High
                          simulation layer shall not      
                          depend on PySide6 UI classes.   

  NFR-5.2                 Circuit validation shall be     High
                          callable independently of the   
                          GUI.                            

  NFR-5.3                 QCS                             Medium
                          serialization/deserialization   
                          shall be callable independently 
                          of the GUI.                     

  NFR-5.4                 OpenQASM parsing and generation Medium
                          shall be callable independently 
                          of the GUI.                     

  NFR-5.5                 The application session layer    High
                          (current circuit, saved
                          baseline, Save/Simulation
                          status, undo/redo, and the
                          candidate/commit mutation
                          pipeline) shall not depend on
                          PySide6.
  -------------------------------------------------------------------------------

### 13.6 Portability

  -----------------------------------------------------------------------
  ID                      Requirement                         Priority
  ----------------------- ------------------------------- ---------
  NFR-6.1                 The application shall run without source- Medium
                          code modification on CachyOS under
                          Hyprland (Wayland) when the exact tested
                          dependency versions are installed.

  NFR-6.2                 The application shall use only platform-      Medium
                          independent Python, PySide6, Qiskit,
                          Qiskit Aer, and standard local-file APIs for
                          core functionality.

  NFR-6.3                 The release shall be source-run and shall    Medium
                          not require a packaged executable or installer.

  NFR-6.4                 Drag-and-drop, keyboard          Medium
                          shortcuts, file dialogs, and
                          PNG export shall work in a
                          native Wayland session under
                          Hyprland, in both tiled and
                          floating window states.
  -----------------------------------------------------------------------

### 13.7 Testability

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  NFR-7.1                 Every supported gate    High
                          operation shall be      
                          unit-testable           
                          independently of the    
                          GUI.                    

  NFR-7.2                 Gate matrix definitions High
                          shall be testable       
                          against known reference 
                          matrices.               

  NFR-7.3                 The simulation engine   High
                          shall expose a non-GUI  
                          API that accepts a      
                          circuit and returns     
                          simulation results.     

  NFR-7.4                 Validation shall be     High
                          independently testable  
                          using valid and invalid 
                          circuit fixtures.       

  NFR-7.5                 QCS round trips shall   High
                          be independently        
                          testable without        
                          launching the GUI.      

  NFR-7.6                 OpenQASM import and     High
                          export shall be         
                          independently testable  
                          without launching the   
                          GUI.                    

  NFR-7.7                 Floating-point          High
                          comparison of           
                          simulation-derived      
                          values shall use an     
                          absolute tolerance of   
                          1e-9 unless a test      
                          explicitly specifies a  
                          stricter tolerance.     

  NFR-7.8                 Application-state         High
                          transitions in Section
                          6.5 shall be testable
                          without constructing Qt
                          objects.
  -----------------------------------------------------------------------

## 14. Data requirements

### 14.1 In-memory circuit

A circuit shall contain:

-   `num_qubits`;
-   an ordered collection of gate placements.

Each placement shall contain:

-   gate type;
-   target qubit indices;
-   control qubit indices where applicable;
-   column index in the release editor range `0..49`.

Two circuit definitions are equal when they have the same `num_qubits` and the
same set of gate placements. The order of the placement collection and the
order of control indices within a placement do not affect equality. Save
status shall be computed with this equality.

### 14.2 Simulation result

Simulation results shall exist only in memory and shall contain:

-   full statevector;
-   basis-state probabilities;
-   reduced Bloch vector for each qubit.

### 14.3 `.qcs`

The `.qcs` format shall persist only the circuit definition and schema
version. It shall not persist simulation results.

### 14.4 OpenQASM

Imported and exported OpenQASM shall use the supported subset defined in
Section 11.

### 14.5 Images

PNG exports shall contain only the rendered circuit, Bloch-sphere view,
or histogram view requested by the user.

## 15. External interfaces

### 15.1 GUI

The main window shall provide:

-   gate palette;
-   circuit canvas with 1--10 qubits and 50 columns;
-   editable OpenQASM 2.0 panel beside the circuit canvas;
-   simulation results below the workspace, with Bloch spheres and the
    probability histogram side by side;
-   Bloch-sphere visualisation;
-   probability histogram;
-   New;
-   Save;
-   Save As;
-   Load/Open;
-   Import OpenQASM;
-   Export OpenQASM;
-   Export image;
-   Change target command for a selected CNOT or Toffoli;
-   Run;
-   visible Save status (`Clean` or `Dirty`);
-   visible Simulation status (`None`, `Current`, or `Stale`);
-   the standard error presentation mechanism.

The gate palette shall be a compact vertical column of symbolic icons. Each
icon shall have an accessible name and a tooltip describing the gate. Circuit
gates shall use conventional quantum-circuit notation, including control dots,
target circled-plus symbols, and the measurement marker.

The OpenQASM editor shall display the current circuit's canonical OpenQASM
representation. Editing the text shall not modify the circuit until the user
applies it. Syntax feedback shall use Qiskit's OpenQASM 2 parser; the app's
supported-subset importer shall then determine whether the program can be
applied. Invalid text shall leave the circuit and session state unchanged.

The circuit canvas shall provide a clear grid position for each
wire/column cell so that drag/drop, paste anchoring, and arrow-key
movement can be implemented against discrete qubit/column coordinates.

### 15.2 Hardware

The application shall require only:

-   keyboard;
-   mouse or trackpad;
-   display.

### 15.3 Software

The application shall interface locally with:

-   Python 3.13;
-   PySide6 / Qt 6;
-   Qiskit;
-   Qiskit Aer;
-   NumPy where required;
-   local filesystem.

No network API is required.

## 16. Error-handling requirements

The application shall use one shared standard error presentation
mechanism for user-facing failures and rejected operations. The
mechanism shall present a visible plain-language error message (for
example, the product's standard error dialog/banner) and shall not expose
raw Python exceptions or stack traces.

The application shall handle at least the following errors without
crashing:

1.  Invalid gate arity.
2.  Invalid qubit index.
3.  Duplicate qubit reference.
4.  Wire/column collision.
5.  Gate or second Measurement after Measurement.
6.  Invalid circuit size.
7.  Negative or out-of-range column index, including columns beyond 49.
8.  Non-contiguous CNOT or Toffoli placement.
9.  Invalid `.qcs` JSON.
10. Unsupported `.qcs` schema version.
11. Missing `.qcs` file.
12. File read/write failure.
13. Invalid OpenQASM syntax.
14. Unsupported OpenQASM construct.
15. OpenQASM circuit exceeding 10 qubits.
16. Invalid OpenQASM Measurement mapping.
17. OpenQASM operation count exceeding the 50-column import limit.
18. Invalid drag/drop placement.
19. Invalid gate movement.
20. Invalid multi-selection movement.
21. Paste extending beyond the 1--10 qubit or 50-column bounds.
22. Paste collision or other paste validation failure.
23. Simulation failure.

Rejected drag/drop, movement, multi-selection movement, and paste
operations shall leave the circuit unchanged and shall not create an
undo-history entry.

A failed Run shall leave the current circuit unchanged and shall preserve
any previous result and its Simulation status unchanged.

A failed Load/Open or Import operation shall leave the current circuit,
Save status, Simulation status, and undo/redo history unchanged.

A failed Save shall leave the current in-memory circuit, Save status,
and simulation status unchanged.

Each error shall leave existing circuit data unchanged unless the user
explicitly confirms a destructive editing operation.

## 17. Correctness requirements

The implementation shall include automated tests for at least:

  -----------------------------------------------------------------------
  Test                                Expected result
  ----------------------------------- -----------------------------------
  Application startup                 Empty 2-qubit circuit; Save=`Clean`;
                                      Simulation=`None`; no history

  Empty 1-qubit circuit               `|0>` state

  X on q0                             `|1>` state

  H on q0                             probabilities approximately 0.5 /
                                      0.5

  H followed by H                     original state restored

  H on control + CNOT, two qubits     Bell-state probabilities for `00`
                                      and `11`

  Z on `|0>`                          computational probability unchanged

  S and T                             correct Qiskit-compatible phase
                                      behavior

  CNOT contiguous wires               one target, one control; either wire
                                      may be the target

  Toffoli contiguous wires            one target, two controls; any of the
                                      three wires may be the target

  Toffoli with controls not both 1    target unchanged

  Toffoli with both controls 1        target flipped

  Measurement marker                  statevector unchanged

  Second Measurement on one qubit    validation failure

  Gate after Measurement              validation failure

  Column 50                           placement rejected

  Invalid drag/drop                   circuit unchanged; no undo entry;
                                      standard error shown

  Invalid single-gate movement        circuit unchanged; no undo entry;
                                      standard error shown

  Invalid multi-selection movement    entire move rejected atomically;
                                      circuit unchanged; no undo entry

  Out-of-bounds paste                 circuit unchanged; no undo entry;
                                      standard error shown

  Paste anchor                        copied selection's minimum
                                      qubit/column maps to destination cell

  Click selection                     replaces previous selection

  Ctrl/Cmd selection                  adds/removes individual gate objects

  Marquee selection                   replaces selection unless Ctrl/Cmd is held

  Undo to saved baseline              Save status becomes `Clean`

  Redo away from saved baseline       Save status becomes `Dirty`

  Edit after Undo                     redo history cleared

  New/Load success                    Save=`Clean`; Simulation=`None`;
                                      undo/redo history cleared

  Import success                      new unsaved session: Save=`Dirty`;
                                      no file path; Simulation=`None`;
                                      undo/redo history cleared

  Failed Load/Import                  complete pre-operation application
                                      state unchanged

  Failed Run                          previous result and its status
                                      unchanged; circuit unchanged

  Save on unsaved circuit             file-save dialog opens

  Save/Save As                        current circuit becomes clean baseline

  QCS save/load                       exact circuit-definition round trip

  QASM import ordering                each statement placed in next column

  QASM export ordering                increasing column order; same-column
                                      operations ordered by lowest occupied
                                      qubit index

  QASM Measurement mapping            exactly `c[n]`; `q[i] -> c[i]`

  QASM import/export                  supported gate type, qubits, and
                                      execution order preserved

  Entangled qubit Bloch vector        reduced vector may lie inside the
                                      sphere

  Invalid overlapping gates           validation failure

  Y on q0                             statevector `i|1>` (Qiskit Y matrix)

  Known Bloch vectors                 `|+>` = (1,0,0); S on `|+>` = (0,1,0);
                                      `|1>` = (0,0,-1)

  3-qubit basis ordering              X on q0 only: probability 1 at `001`;
                                      X on q2 only: probability 1 at `100`

  CNOT control above target           X on q0 + control q0/target q1 gives
                                      `11`

  CNOT control below target           X on q1 + control q1/target q0 gives
                                      `11`

  Toffoli target on middle wire       controls q0,q2 both 1 flips q1

  Default CNOT/Toffoli drop           controls on upper wires, target on
                                      bottom wire

  Change target                       CNOT swaps roles; Toffoli cycles;
                                      one undo entry each

  No-op mutation                      no undo entry; statuses unchanged

  Move onto self-vacated cells        valid; overlap with an unselected
                                      gate rejected atomically

  Empty selection / clipboard         arrow keys and Ctrl+V do nothing

  Ctrl+V without prior click          pastes at last click, else q0/col 0

  Circuit equality                    placement and control order ignored;
                                      Undo to baseline is `Clean`

  Destructive resize, confirmed       affected gates removed; one undo entry

  Destructive resize, cancelled       circuit unchanged

  PNG export                          circuit, Bloch, and histogram each
                                      write a valid PNG

  Keyboard shortcuts                  each of FR-1.31 to FR-1.44 works

  QASM cx/ccx argument order          controls first, target last on import
                                      and export

  QASM operation limit                50 operations accepted; 51 rejected;
                                      state unchanged

  QASM invalid operands               repeated, out-of-range,
                                      non-contiguous, or `h q;` rejected

  QASM header/register rules          missing include or register not `q`
                                      rejected; `//` comments ignored

  QASM export preamble                OPENQASM, include, qreg; creg only
                                      with Measurement

  Import when Dirty                   Save/Don't Save/Cancel offered;
                                      Cancel keeps all state

  Save after Import                   file-save dialog opens; then `Clean`

  QCS loader strictness               unknown field, float/bool integer,
                                      or version `1.1` rejected

  QCS canonical order                 placements by column then lowest
                                      qubit; controls ascending

  Headless session tests              Section 6.5 transitions run without Qt

  Layout at 1920x1080                 palette, scrollable canvas, OpenQASM
                                      editor, and bottom results in one window

  Wayland interaction                 drag/drop, shortcuts, dialogs, PNG
                                      export work; tiled and floating
  -----------------------------------------------------------------------

## 18. Acceptance criteria

The release shall be accepted only when all of the following are true:

### 18.1 Functional acceptance

-   Every High-priority FR and NFR is implemented and verified. Every
    Medium-priority FR and NFR is implemented, or is listed as a known
    limitation in the release notes.
-   The full gate palette works.
-   CNOT and Toffoli are atomic, single-column, contiguous-wire objects
    with the specified target/control arrangement.
-   Rectangular selection and the defined click/Ctrl/Cmd selection rules
    work.
-   Copy/paste uses the clicked cell as the top-left anchor and never
    silently overwrites existing gates.
-   Invalid drag/drop, movement, and paste operations are rejected
    atomically and show a standard error message.
-   Arrow keys move selections by exactly one grid cell per press.
-   Undo/redo works for every successful circuit mutation and follows the
    saved-baseline rules.
-   New/Load/Import clear undo/redo history only after successful
    completion.
-   Qubit resizing follows the confirmation rules and records a
    destructive resize as one mutation.
-   Validation prevents invalid circuits from reaching simulation.
-   Run produces the required statevector-derived outputs.
-   Run is synchronous in the GUI thread for this release.
-   Save/load preserves the circuit definition.
-   New/Load/Import clear simulation results.
-   OpenQASM import/export works for the defined subset and preserves
    execution order and supported gate semantics.
-   PNG exports work for circuit, Bloch-sphere, and histogram views.

### 18.2 State-management acceptance

-   Startup state is a new empty 2-qubit circuit with Save=`Clean` and
    Simulation=`None`.
-   Save status is based on equality with the current saved baseline.
-   Undo/Redo correctly move Save status between `Clean` and `Dirty`.
-   Any successful circuit mutation makes retained simulation results
    `Stale`.
-   Successful Run makes Simulation=`Current` without changing Save status.
-   Failed Run leaves the previous result and its Simulation status unchanged.
-   Successful New/Load sets Save=`Clean`; successful Import sets
    Save=`Dirty` (new unsaved session); both set Simulation=`None` and
    clear history.
-   Failed Load/Import leaves the complete pre-operation state unchanged.
-   Dirty New/Load/Import/Exit prompts offer exactly `Save`, `Don't Save`, and
    `Cancel` with the required behavior.

### 18.3 Simulation acceptance

The reference circuits in Section 17 shall pass within the defined
numerical tolerance.

### 18.4 Performance acceptance

The NFR-1.1 and NFR-1.2 thresholds shall be met on the reference hardware.

### 18.5 Usability acceptance

A first-time user shall be able to construct and simulate the specified
2-qubit Bell-state circuit within five minutes without external
instruction.

### 18.6 Reliability acceptance

Malformed circuit data, malformed session files, unsupported OpenQASM,
invalid editor operations, and simulation failures shall not crash the
application or destroy the current circuit.

### 18.7 Offline/security acceptance

The application shall make no network requests during functional
testing.

### 18.8 Platform acceptance

Acceptance testing shall be performed on the reference machine described in
Section 4.3 (CachyOS, Hyprland/Wayland, 1920x1080) using the pinned
dependency versions. Other platforms are not part of release acceptance.

## 19. Traceability

  -----------------------------------------------------------------------
  Requirement group       Primary implementation  Primary verification
                          area                    area
  ----------------------- ----------------------- -----------------------
  FR-1                    Circuit model, editor,  Editor integration and
                          selection, history      interaction tests

  FR-2                    Circuit validator       Validation unit tests

  FR-3                    Simulator               Reference-circuit tests

  FR-4                    Visualisation layer     GUI/integration tests

  FR-5                    Session manager         QCS round-trip and
                                                  lifecycle tests

  FR-6                    QASM parser/exporter    QASM fixture and
                                                  deterministic-order tests

  FR-7                    Documentation/UI        Usability inspection

  NFR-1                   Simulator/editor        Performance tests

  NFR-2                   GUI                     Usability and state-UI tests

  NFR-3                   Application error       Failure-injection tests
                          handling

  NFR-4                   Application/network     Offline test
                          boundary

  NFR-5                   Architecture            Dependency inspection

  NFR-6                   Source runtime          Smoke tests on CachyOS/Hyprland

  NFR-7                   Core APIs               Automated unit/integration
                                                  tests

  State/lifecycle         Application state       State-transition tests
                         model
  -----------------------------------------------------------------------

## 20. Implementation boundaries

The implementation shall maintain the following separation:

``` text
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
 │    ├── current circuit
 │    ├── current file path and saved baseline
 │    └── Save status / Simulation status
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

The domain, application session, simulation, persistence, and
interoperability layers shall remain usable without creating the PySide6
main window.

The 50-column limit shall be represented as a release-level editor
constraint rather than an intrinsic domain-model impossibility, so a
future revision can lift the editor limit without changing the basic
circuit model. Scrolling the canvas is permitted in this release.

## 21. Explicit design decisions

The following decisions are normative for the current release:

1.  The first release is a general circuit editor and simulator, not an
    algorithm-specific application.
2.  Grover and Shor are not release acceptance requirements.
3.  The release uses a fixed gate palette: H, X, Y, Z, S, T, CNOT,
    Toffoli, Measurement.
4.  Parameterized gates are out of scope for the release.
5.  The application starts with a new empty 2-qubit circuit.
6.  Save status and simulation status are independent state dimensions.
7.  Save status is `Clean` or `Dirty` based on whether the session has a
    saved baseline that the current circuit equals (Section 14.1).
8.  Simulation status is `None`, `Current`, or `Stale`.
9.  Every successful circuit mutation makes any retained simulation result
    `Stale`; Save status is independently recalculated against the saved
    baseline.
10. Undo and Redo recalculate Save status from the saved baseline and make
    retained simulation results `Stale`; historical simulation results are
    not restored, and Undo/Redo do not create additional history entries.
11. A new mutation after Undo clears the redo history.
12. Every successful circuit mutation creates exactly one undo-history
    entry.
13. Run, Save, Save As, Load, Import, Export, and selection changes do not
    create undo-history entries.
14. Successful New, Load, and Import clear undo/redo history; failed
    operations do not.
15. Successful New and Load establish the resulting circuit as `Clean`; a
    successful Import creates a new unsaved session that is `Dirty`. All
    three clear simulation results to `None`.
16. Run occurs synchronously on the GUI thread in the current release.
17. Run changes only simulation state; it does not affect Save status.
18. A failed Run leaves any previous result and its Simulation status
    unchanged.
19. Load/Open and Import are atomic; failure leaves the complete prior
    application state unchanged.
20. Save and Save As establish the current circuit as the clean baseline
    after successful completion.
21. Save on a never-saved circuit opens a file-save dialog.
22. Dirty New, Load, Import, and Exit use exactly `Save`, `Don't Save`, and `Cancel`.
23. Invalid drag/drop, movement, multi-selection movement, and paste are
    rejected atomically, show the standard error message, and create no
    undo entry.
24. Arrow-key movement is exactly one grid cell per key press.
25. Selection uses click-to-replace, Ctrl/Cmd toggle, and marquee replace
    unless Ctrl/Cmd is held.
26. Paste uses the clicked destination cell as the top-left anchor and
    preserves the selection's relative structure.
27. CNOT and Toffoli are contiguous-wire, single-column atomic objects.
28. For CNOT and Toffoli, the target may be any occupied wire; the other
    occupied wire(s) are controls. OpenQASM uses Qiskit argument order
    (controls first, target last).
29. The release editor has a hard limit of 50 columns (`0..49`).
30. The canvas may scroll in this release. A future revision may remove the
    finite column limit entirely; that capability is not part of this
    release.
31. Each qubit may contain at most one Measurement, and Measurement must be
    the final operation on that qubit.
32. OpenQASM import preserves statement order by placing each statement in
    the next editor column.
33. OpenQASM export preserves gate type, qubit assignments, and execution
    order, but exact editor columns are not required to round-trip.
34. OpenQASM export orders operations by increasing column, then by the
    lowest-indexed qubit occupied by each operation within a column.
35. When any Measurement exists, OpenQASM uses exactly one classical
    register `c[n]` and maps `q[i]` to `c[i]`.
36. The release is source-run; packaged installers and bundled executables
    are out of scope.
37. Exact tested dependency versions shall be pinned in the project's
    checked-in dependency/environment file.
38. The application is fully offline.
39. Qiskit Python source code is not imported or exported.
40. The private project SRS is not a repository dependency and shall not be
    required at runtime, build time, or test time.
41. The public requirements document shall contain no private SRS content
    beyond the functional decisions necessary to implement and verify Open
    QSim.
42. The application always edits a `.qcs` session. Import OpenQASM creates
    a new unsaved session (`Dirty`, no file path, no saved baseline); the
    `.qasm` file never becomes the session file.
43. A session with no saved baseline is always `Dirty`.
44. Circuit equality ignores the order of placements and of control indices.
45. An operation that leaves the circuit definition unchanged is not a
    mutation.
46. A newly dropped CNOT or Toffoli has its controls on the upper wires and
    its target on the bottom wire; a Change target command alters the
    target wire.
47. The sole tested platform is CachyOS (Arch based) under Hyprland/Wayland
    on the reference laptop at 1920x1080; Windows, macOS, and other Linux
    distributions are not claimed in this release.

## Appendix A. Revision decisions captured for the speedrun baseline

This revision incorporates the implementation decisions made during the
requirements review on 2026-10-05. No additional product behavior is
intentionally introduced by this appendix; it records the decisions that
resolved previously ambiguous requirements.

## Appendix B. Revision decisions from the 2026-10-06 review

This revision resolves inconsistencies found in review:

-   CNOT and Toffoli now follow the Qiskit/OpenQASM convention: the target may
    be any wire of the contiguous block, and OpenQASM arguments are written
    controls first, target last. Default drop orientation and a Change target
    command were added (FR-1.49, FR-1.50).
-   The application always edits a `.qcs` session. Import OpenQASM creates a
    new unsaved session (`Dirty`) and, like New, Load, and Exit, prompts when
    Save status is `Dirty` (LC-10, LC-12).
-   Circuit equality is defined over a canonical form (Section 14.1).
-   A failed Run leaves the previous result and its status unchanged (LC-8).
-   Lifecycle rules received IDs (LC-1 to LC-17) and Section 6.5 governs when
    restatements conflict.
-   Added a headless application session layer (Section 20, NFR-5.5, NFR-7.8).
-   The supported and tested platform is CachyOS/Hyprland (Wayland) on the
    reference laptop; the reference hardware, Python provisioning, a
    1920x1080 layout requirement (NFR-2.7, with a scrollable canvas), and
    Wayland interaction requirement (NFR-6.4) were added or updated
    accordingly.
-   Added editing clarifications (Section 6.6), QCS loader strictness
    (FR-5.15 to FR-5.18), OpenQASM syntax and export-preamble rules
    (FR-6.13 to FR-6.16), a worst-case performance case, a definition of
    mandatory requirements, and additional tests (Section 17).