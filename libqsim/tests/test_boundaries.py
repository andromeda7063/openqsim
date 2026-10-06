"""Boundary and isolation tests for libqsim (NFR-5.1, NFR-5.5).

Verifies that libqsim never imports PySide6 or Qt modules, and that
no Qt references exist within libqsim source files.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SUBPACKAGES = [
    "libqsim",
    "libqsim.domain",
    "libqsim.application",
    "libqsim.simulation",
    "libqsim.persistence",
    "libqsim.qasm",
]


@pytest.mark.req("NFR-5.1", "NFR-5.5")
@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackage_does_not_import_qt(subpackage: str) -> None:
    """Importing each libqsim subpackage in a fresh process must not import Qt."""
    check_script = f"""
import sys
import {subpackage}

forbidden = ['PySide6', 'shiboken6', 'PyQt5', 'PyQt6']
loaded_forbidden = [mod for mod in forbidden if mod in sys.modules]
if loaded_forbidden:
    print(f"Forbidden Qt modules loaded by {subpackage}: {{loaded_forbidden}}")
    sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", check_script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Subprocess importing '{subpackage}' failed:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


@pytest.mark.req("NFR-5.1", "NFR-5.5")
def test_no_qt_references_in_libqsim_src() -> None:
    """libqsim/src must not mention PySide6 or PyQt in any source file."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    assert src_dir.is_dir(), f"Source directory not found: {src_dir}"

    forbidden_tokens = ["PySide6", "PyQt"]
    violations: list[str] = []

    for file_path in src_dir.rglob("*.py"):
        text = file_path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{file_path} contains forbidden token '{token}'")

    assert not violations, "Forbidden Qt references found in libqsim/src:\n" + "\n".join(violations)
