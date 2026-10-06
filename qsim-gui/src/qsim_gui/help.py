"""Help viewer and documentation resolution for OpenQSim."""

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QTextBrowser, QWidget

DOC_MAPPING: dict[str, str] = {
    "quick-start": "quick-start.md",
    "qcs-format": "qcs-format.md",
    "qasm-support": "qasm-support.md",
}

ABOUT_MARKDOWN = """# About OpenQSim

OpenQSim is an offline PySide6 desktop application for constructing, editing,
validating, simulating, and visualising small quantum circuits.

It performs exact, noiseless statevector simulation on a classical computer using
Qiskit Aer.

**Version:** 0.1.0  
**License:** Educational and prototyping desktop software  
**Environment:** Fully offline
"""


def get_docs_dir() -> Path:
    """Find the directory containing project documentation."""
    cwd_docs = Path.cwd() / "docs"
    if cwd_docs.is_dir():
        return cwd_docs
    # Relative to this source file: qsim-gui/src/qsim_gui/help.py -> repo_root/docs
    repo_docs = Path(__file__).resolve().parents[3] / "docs"
    if repo_docs.is_dir():
        return repo_docs
    return cwd_docs


def resolve_doc_path(name: str) -> Path:
    """Resolve a documentation file path by key."""
    docs_dir = get_docs_dir()
    filename = DOC_MAPPING.get(name, f"{name}.md")
    return docs_dir / filename


class HelpWindow(QMainWindow):
    """Read-only documentation viewer window rendering Markdown."""

    def __init__(
        self,
        title: str,
        content: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{title} - OpenQSim Help")
        self.resize(780, 560)

        self._browser = QTextBrowser(self)
        self._browser.setReadOnly(True)
        # Fully offline: disable opening external links
        self._browser.setOpenExternalLinks(False)
        self._browser.setOpenLinks(False)
        self._browser.setMarkdown(content)

        self.setCentralWidget(self._browser)

    @property
    def browser(self) -> QTextBrowser:
        return self._browser


def open_help_window(
    doc_key: str,
    title: str,
    parent: QWidget | None = None,
) -> HelpWindow:
    """Open and return a HelpWindow displaying the requested doc."""
    if doc_key == "about":
        content = ABOUT_MARKDOWN
    else:
        path = resolve_doc_path(doc_key)
        content = path.read_text(encoding="utf-8")
    window = HelpWindow(title=title, content=content, parent=parent)
    window.show()
    return window
