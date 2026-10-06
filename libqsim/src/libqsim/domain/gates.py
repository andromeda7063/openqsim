"""Gate definitions, arities, and single-qubit action matrices."""

from enum import Enum

import numpy as np
import numpy.typing as npt


class GateType(str, Enum):
    """Supported gate and visual marker types in OpenQSim."""

    H = "H"
    X = "X"
    Y = "Y"
    Z = "Z"
    S = "S"
    T = "T"
    CNOT = "CNOT"
    Toffoli = "Toffoli"
    Measurement = "Measurement"


GATE_ARITY: dict[GateType, tuple[int, int]] = {
    GateType.H: (1, 0),
    GateType.X: (1, 0),
    GateType.Y: (1, 0),
    GateType.Z: (1, 0),
    GateType.S: (1, 0),
    GateType.T: (1, 0),
    GateType.CNOT: (1, 1),
    GateType.Toffoli: (1, 2),
    GateType.Measurement: (1, 0),
}

_H_MAT: npt.NDArray[np.complex128] = (1.0 / np.sqrt(2.0)) * np.array(
    [[1.0, 1.0], [1.0, -1.0]], dtype=np.complex128
)
_X_MAT: npt.NDArray[np.complex128] = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
_Y_MAT: npt.NDArray[np.complex128] = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
_Z_MAT: npt.NDArray[np.complex128] = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)
_S_MAT: npt.NDArray[np.complex128] = np.array([[1.0, 0.0], [0.0, 1.0j]], dtype=np.complex128)
_T_MAT: npt.NDArray[np.complex128] = np.array(
    [[1.0, 0.0], [0.0, np.exp(1.0j * np.pi / 4.0)]], dtype=np.complex128
)

_MATRICES: dict[GateType, npt.NDArray[np.complex128] | None] = {
    GateType.H: _H_MAT,
    GateType.X: _X_MAT,
    GateType.Y: _Y_MAT,
    GateType.Z: _Z_MAT,
    GateType.S: _S_MAT,
    GateType.T: _T_MAT,
    GateType.CNOT: _X_MAT,
    GateType.Toffoli: _X_MAT,
    GateType.Measurement: None,
}


def matrix(gate_type: GateType) -> npt.NDArray[np.complex128] | None:
    """Return a 2x2 complex NumPy array representing the single-qubit action of the gate.

    For CNOT and Toffoli, returns the Pauli-X matrix representing the target action.
    For Measurement, returns None.
    Matrices follow Qiskit conventions. Returns a copy so caller modifications
    do not alter the cached definition.
    """
    if isinstance(gate_type, str) and not isinstance(gate_type, GateType):
        gate_type = GateType(gate_type)
    mat = _MATRICES[gate_type]
    return mat.copy() if mat is not None else None
