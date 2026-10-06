"""PySide6 spike opening an empty QMainWindow titled 'OpenQSim spike'."""

import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow


def main() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("OpenQSim spike")
    window.resize(800, 600)
    window.show()

    platform = app.platformName()
    print(
        f"PySide6 QMainWindow created successfully. Title: '{window.windowTitle()}' (Platform: {platform})"
    )

    if platform == "offscreen" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        app.processEvents()
        return 0

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
