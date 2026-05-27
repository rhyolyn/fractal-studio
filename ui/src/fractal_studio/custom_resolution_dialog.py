from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox


class CustomResolutionDialog(QDialog):
    def __init__(self, default_width: int = 1920, default_height: int = 1080, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Custom Resolution")
        self._width_box = QSpinBox()
        self._width_box.setRange(64, 16384)
        self._width_box.setValue(default_width)
        self._height_box = QSpinBox()
        self._height_box.setRange(64, 16384)
        self._height_box.setValue(default_height)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout()
        layout.addRow("Width:", self._width_box)
        layout.addRow("Height:", self._height_box)
        layout.addRow(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[int, int]:
        return self._width_box.value(), self._height_box.value()
