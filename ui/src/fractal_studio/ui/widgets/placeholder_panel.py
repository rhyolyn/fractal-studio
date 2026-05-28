from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class PlaceholderPanel(QGroupBox):
    def __init__(self, title: str, lines: list[str]) -> None:
        super().__init__(title)
        layout = QVBoxLayout()
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)
