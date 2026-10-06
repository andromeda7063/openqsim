"""OpenQASM 2.0 subset exporter."""

from libqsim.domain.models import Circuit

__all__ = ["export_text"]


def export_text(circuit: Circuit) -> str:
    """Serialize a Circuit to an OpenQASM 2.0 string."""
    raise NotImplementedError
