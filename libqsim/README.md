# libqsim

Core quantum simulation library and headless editor application layer for OpenQSim.

## Public API Overview

- **Domain Model**:
  - `Circuit(num_qubits, placements)`: Immutable circuit model.
  - `GatePlacement(gate_type, targets, controls, column)`: Immutable gate placement.
  - `GateType`: Supported gate types (`H`, `X`, `Y`, `Z`, `S`, `T`, `CNOT`, `Toffoli`, `Measurement`).
  - `validate(circuit)`: Validates circuits against domain rules.

- **Application Session**:
  - `EditorSession`: Manages circuit lifecycle, undo/redo history, save status, and simulation.
  - `SaveStatus` (`CLEAN`, `DIRTY`), `SimulationStatus` (`NONE`, `CURRENT`, `STALE`).
  - `place_gate`, `move_gates`, `delete_gates`, `clear`, `copy_gates`, `paste`, `change_target`, `resize`.
  - `run_guarded`: Executes lifecycle actions with clean/dirty prompt guards.

- **Simulation**:
  - `simulate(circuit)`: Exact noiseless statevector simulation via Qiskit Aer.
  - `SimulationResult`: Holds statevector, probabilities, and reduced Bloch vectors.

- **Persistence (QCS)**:
  - `dumps(circuit)` / `loads(text)`: Canonical `.qcs` JSON serializer and strict parser.
  - `write(path, circuit)` / `read(path)`: Atomic file read and write operations.

- **Interoperability (OpenQASM 2.0)**:
  - `import_text(text)`: Imports supported OpenQASM 2.0 subset into a Circuit.
  - `export_text(circuit)`: Exports a Circuit to canonical OpenQASM 2.0.

## Quick Example

```python
import libqsim

session = libqsim.EditorSession()
session.apply(libqsim.place_gate(session.circuit, libqsim.GateType.H, 0, 0))
session.apply(libqsim.place_gate(session.circuit, libqsim.GateType.CNOT, 0, 1))

outcome = session.run()
if outcome.ok and session.simulation_result is not None:
    print("Probabilities:", session.simulation_result.probabilities)
    print("Bloch vectors:", session.simulation_result.bloch_vectors)
```
