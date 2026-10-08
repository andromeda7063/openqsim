"""Flat application themes and persisted appearance preferences."""

from enum import StrEnum

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class Theme(StrEnum):
    """Appearance options available in Preferences."""

    DARK = "Dark"
    DARK_PURPLE = "Dark Purple"


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Apply a flat dark palette and widget styling to the application."""
    purple = theme == Theme.DARK_PURPLE
    accent = "#a78bfa" if purple else "#58a6ff"
    accent_hover = "#8b5cf6" if purple else "#388bfd"
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#17191f"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6e8ee"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#101217"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1d2028"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#252936"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f3f4f6"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6e8ee"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#252936"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6e8ee"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#101217"))
    palette.setColor(QPalette.ColorRole.Mid, QColor("#414653"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#858b99"))
    app.setStyle("Fusion")
    app.setPalette(palette)
    app.setStyleSheet(
        f"""
        QWidget {{ color: #e6e8ee; }}
        QMainWindow, QWidget#central_widget, QWidget#results_panel {{
            background: #17191f;
        }}
        QMenuBar, QMenu, QToolBar, QStatusBar {{ background: #1d2028; }}
        QMenuBar::item {{ padding: 6px 10px; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: #303541; }}
        QToolBar {{ border: 0; spacing: 6px; padding: 6px; }}
        QToolButton, QPushButton {{
            background: #252936; border: 1px solid #3b414f; border-radius: 6px;
            padding: 6px 10px;
        }}
        QToolButton:hover, QPushButton:hover {{ border-color: {accent}; }}
        QPushButton:default, QPushButton#apply_qasm_button {{
            background: {accent}; color: #101217; border-color: {accent};
            font-weight: 600;
        }}
        QPushButton:default:hover, QPushButton#apply_qasm_button:hover {{
            background: {accent_hover}; border-color: {accent_hover};
        }}
        QPushButton:disabled {{ color: #858b99; background: #20232b; }}
        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
            background: #101217; border: 1px solid #3b414f; border-radius: 5px;
            padding: 5px;
            selection-background-color: {accent};
        }}
        QPlainTextEdit#qasm_editor {{
            font-family: monospace; font-size: 10pt; border-radius: 7px;
        }}
        QScrollArea, QSplitter::handle {{ background: #17191f; }}
        QSplitter::handle {{ width: 3px; height: 3px; }}
        QWidget#palette_region, QWidget#qasm_region {{
            background: #1d2028; border: 1px solid #303541; border-radius: 8px;
        }}
        QPushButton[gateButton="true"] {{
            background: #252936; border: 1px solid #414653; border-radius: 8px;
            font-size: 15px;
        }}
        QLabel#section_title {{ font-weight: 600; }}
        QLabel#stale_banner {{
            background: #3a2e17; color: #f4c66a; border: 1px solid #80652d;
            border-radius: 6px; padding: 6px; font-weight: 600;
        }}
        QLabel#empty_state_label, QLabel#explanation_label {{ color: #a9afbd; }}
        QLabel#save_status_label[status="dirty"] {{ color: #f4c66a; font-weight: 600; }}
        QLabel#sim_status_label[status="stale"] {{ color: #f4c66a; font-weight: 600; }}
        QLabel#sim_status_label[status="current"] {{ color: #75d6a4; font-weight: 600; }}
        QLabel#qasm_status[state="error"] {{ color: #ff8585; }}
        QLabel#qasm_status[state="warning"] {{ color: #f4c66a; }}
        QLabel#qasm_status[state="valid"] {{ color: #75d6a4; }}
        """
    )
