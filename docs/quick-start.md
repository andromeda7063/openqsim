# Quick Start

This guide walks through a 2-qubit Bell-state circuit.

## 1. Start OpenQSim

Launch the application.

Open **Edit -> Preferences...** to choose **Dark** or **Dark Purple**. The
selection is saved for the next launch.

The compact gate palette is the vertical icon column at the left; hover over
an icon to read its tooltip. The circuit uses conventional quantum gate
symbols. The OpenQASM 2.0 editor is beside the canvas and simulation results
appear below the workspace.

A new application starts with:

- 2 qubits;
- no gate placements;
- Save status `Clean`;
- Simulation status `None`.

## Load an example

Open the **Examples** menu and choose one of the five circuits. Each entry
shows a short description in its tooltip. Loading an example replaces the
current circuit and opens it as an unsaved session (`Save: Dirty`,
`Simulation: None`). If your current session is dirty, choose **Save**,
**Don't Save**, or **Cancel**. Examples are editable; use **Save As** to keep
one as a `.qcs` file. Try **Bell state**, then Run to inspect its entangled
output.

## 2. Add an H Gate

Add an `H` gate to qubit 0 in the first available column.

Qubit 0 is the top wire.

## 3. Add a CNOT

Place a CNOT using the two qubit wires in the next column.

For a CNOT:

- the occupied wires must be contiguous;
- one occupied wire is the control and the other is the target;
- a newly placed CNOT puts the control on the wire where you drop it and the
  target on the wire below;
- use **Change Target** on a selected CNOT to swap control and target.

Dropping the CNOT on qubit 0 gives control = q0 and target = q1, matching the
OpenQASM statement `cx q[0],q[1];`. Because the H gate acts on the control, the
CNOT then produces the Bell state.

## 4. Run the Circuit

Activate **Run**.

Simulation does not happen automatically when the circuit is edited.

A successful Run produces:

- a statevector;
- probabilities for all computational-basis states;
- a reduced Bloch vector for each qubit.

## 5. Inspect the Histogram

The probability histogram displays the full computational-basis distribution.

For the Bell-state circuit, the expected non-zero probabilities are for:

```text
00
11
```

The basis-state ordering follows the application's Qiskit-compatible bit
ordering.

## 6. Inspect the Bloch Spheres

OpenQSim displays one reduced Bloch sphere for each qubit.

The Bloch vector represents the reduced state of that qubit. For an entangled
state, the reduced vector may lie inside the sphere rather than on its surface.

## 7. Edit After Running

Make a circuit edit.

The previous simulation result remains visible, but its Simulation status
becomes:

```text
Stale
```

The simulator does not automatically re-run.

Run the circuit again to replace the retained result and return the status to:

```text
Current
```

## 8. Save the Circuit

Use Save or Save As to write the circuit to a `.qcs` file.

The `.qcs` file stores the circuit definition, not the simulation result.

OpenQASM import and export convert to and from a circuit only. Importing a
`.qasm` file creates a new unsaved circuit; use Save As to store it as `.qcs`.
The OpenQASM editor shows the current circuit and checks syntax as you edit.
Use **Apply to Circuit** to replace the circuit with valid supported QASM.

## 9. Useful Keyboard Shortcuts

```text
Ctrl/Cmd+Z          Undo
Ctrl/Cmd+Y          Redo where applicable
Ctrl/Cmd+C          Copy
Ctrl/Cmd+V          Paste
Delete/Backspace    Delete selection
Ctrl/Cmd+A          Select all
Arrow keys          Move selection one grid cell
Ctrl/Cmd+S          Save
Ctrl/Cmd+O          Open
Ctrl/Cmd+N          New circuit
Ctrl/Cmd+Shift+S    Save As
Ctrl/Cmd+E          Export OpenQASM
```

## Circuit Convention

Remember:

```text
q0 = top wire
q0 = least-significant bit
```

For two qubits:

```text
01
```

means:

```text
q1 = 0
q0 = 1
```
