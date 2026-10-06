"""Application entrypoint for OpenQSim GUI."""

import sys

from libqsim.application.session import EditorSession
from PySide6.QtWidgets import QApplication

from qsim_gui.main_window import MainWindow
from qsim_gui.state import SessionAdapter


def main() -> int:
    """Create and start the OpenQSim GUI application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    session = EditorSession()
    adapter = SessionAdapter(session)
    window = MainWindow(adapter=adapter)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
