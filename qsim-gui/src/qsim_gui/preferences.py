"""Application Preferences dialog."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QWidget,
)

from qsim_gui.theme import Theme


class PreferencesDialog(QDialog):
    """Preferences for the local OpenQSim desktop application."""

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setObjectName("preferences_dialog")

        layout = QFormLayout(self)
        self.theme_picker = QComboBox(self)
        self.theme_picker.setObjectName("theme_picker")
        self.theme_picker.addItems([item.value for item in Theme])
        self.theme_picker.setCurrentText(theme.value)
        layout.addRow("Color theme", self.theme_picker)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def selected_theme(self) -> Theme:
        """Return the theme selected in the dialog."""
        return Theme(self.theme_picker.currentText())
