from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class AppearanceSettingsDialog(QDialog):
    theme_preview_requested = Signal(str)

    def __init__(self, current_theme: str, parent=None) -> None:
        super().__init__(parent)
        self._configure_window(current_theme)
        root = self._build_root(current_theme)
        self._set_root_layout(root)

    def _configure_window(self, current_theme: str) -> None:
        self.setWindowTitle("Settings")
        self.setObjectName("settingsDialog")
        self.resize(860, 520)
        self._initial_theme = current_theme
        self._selected_theme = current_theme

    def _build_root(self, current_theme: str) -> QWidget:
        root = QWidget()
        root.setObjectName("settingsRoot")
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content(current_theme), 1)
        root.setLayout(root_layout)
        return root

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("Preferences")
        sidebar_title.setObjectName("settingsSidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        appearance_tab = QPushButton("Appearance")
        appearance_tab.setObjectName("settingsNavActive")
        appearance_tab.setEnabled(False)
        sidebar_layout.addWidget(appearance_tab)

        for label in ("Rendering", "Export", "Behavior", "Advanced"):
            tab = QPushButton(label)
            tab.setObjectName("settingsNavDisabled")
            tab.setEnabled(False)
            sidebar_layout.addWidget(tab)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)
        return sidebar

    def _build_content(self, current_theme: str) -> QWidget:
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 18, 20, 18)
        content_layout.setSpacing(14)

        title = QLabel("Appearance")
        title.setObjectName("settingsHeading")
        subtitle = QLabel(
            "Choose a UI theme. Select a theme to preview it, then click Apply to keep it."
        )
        subtitle.setObjectName("settingsSubtitle")
        section_label = QLabel("Theme")
        section_label.setObjectName("settingsSectionTitle")

        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addWidget(section_label)
        content_layout.addWidget(self._build_theme_card(current_theme))
        content_layout.addStretch()
        content_layout.addWidget(self._build_buttons())
        content.setLayout(content_layout)
        return content

    def _build_theme_card(self, current_theme: str) -> QFrame:
        theme_card = QFrame()
        theme_card.setObjectName("settingsThemeCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        self._buttons = {
            "light": QRadioButton("Light"),
            "dark": QRadioButton("Dark"),
            "sepia": QRadioButton("Sepia"),
        }
        self._buttons.get(current_theme, self._buttons["light"]).setChecked(True)

        for key, button in self._buttons.items():
            button.setObjectName("settingsThemeOption")
            button.toggled.connect(
                lambda checked, name=key: self._on_theme_toggled(name, checked)
            )
            card_layout.addWidget(button)

        theme_card.setLayout(card_layout)
        return theme_card

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.setObjectName("settingsButtons")
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if apply_button is not None:
            apply_button.clicked.connect(self.accept)
        if close_button is not None:
            close_button.clicked.connect(self.reject)
        return buttons

    def _set_root_layout(self, root: QWidget) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(root)
        self.setLayout(layout)

    def _on_theme_toggled(self, theme_name: str, checked: bool) -> None:
        if checked:
            self._selected_theme = theme_name
            self.theme_preview_requested.emit(theme_name)

    def selected_theme(self) -> str:
        return self._selected_theme
