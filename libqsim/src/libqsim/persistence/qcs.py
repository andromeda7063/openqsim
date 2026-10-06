"""QCS file format persistence for OpenQSim circuits."""

from pathlib import Path

from libqsim.domain.models import Circuit

__all__ = ["QcsError", "dumps", "loads", "read", "write"]


class QcsError(Exception):
    """Raised when QCS parsing, schema validation, or file IO fails."""


def dumps(circuit: Circuit) -> str:
    """Serialize a Circuit to canonical QCS JSON string."""
    raise NotImplementedError


def loads(text: str) -> Circuit:
    """Parse and validate a QCS JSON string into a Circuit."""
    raise NotImplementedError


def write(path: Path | str, circuit: Circuit) -> None:
    """Write a Circuit atomically to a QCS file."""
    raise NotImplementedError


def read(path: Path | str) -> Circuit:
    """Read and validate a Circuit from a QCS file."""
    raise NotImplementedError
