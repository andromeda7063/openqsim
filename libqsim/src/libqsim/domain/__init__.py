"""Domain layer for OpenQSim: circuit, gates, and validation."""

from libqsim.domain.gates import GATE_ARITY, GateType, matrix
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import ValidationError, ValidationErrorCode, validate

__all__ = [
    "GATE_ARITY",
    "Circuit",
    "GatePlacement",
    "GateType",
    "ValidationError",
    "ValidationErrorCode",
    "matrix",
    "validate",
]
