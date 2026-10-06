"""OpenQASM 2.0 subset parser and importer."""

from libqsim.domain.models import Circuit

__all__ = ["QasmError", "import_text"]


class QasmError(Exception):
    """Raised when OpenQASM 2.0 syntax, subset, or semantic validation fails."""


def import_text(text: str) -> Circuit:
    """Parse and validate an OpenQASM 2.0 string into a Circuit."""
    raise NotImplementedError
