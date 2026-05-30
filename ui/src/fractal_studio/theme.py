from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    window_bg: str
    surface_bg: str
    panel_bg: str
    text: str
    muted: str
    border: str
    accent: str
    accent_soft: str
    selection_bg: str
    hover_bg: str
    selected_border: str
    hover_border: str
    stats_label: str
    stats_value: str
    hover_panel_bg: str
    hover_panel_border: str
    hint_text: str
    section_heading: str
    panel_surface: str
    primary_button: str
    checker_a: str
    checker_b: str
    primary_button_hover: str


LIGHT_THEME = ThemeSpec(
    name="light",
    window_bg="#f4f4f7",
    surface_bg="#ffffff",
    panel_bg="#ffffff",
    text="#1f2933",
    muted="#667085",
    border="#d0d5dd",
    accent="#3563e9",
    accent_soft="#8fb0ff",
    selection_bg="rgba(53,99,233,0.10)",
    hover_bg="rgba(53,99,233,0.06)",
    selected_border="#3563e9",
    hover_border="#8fb0ff",
    stats_label="#6b7280",
    stats_value="#111827",
    hover_panel_bg="#ffffff",
    hover_panel_border="#cbd5e1",
    hint_text="#6b7280",
    section_heading="#8b91a2",
    panel_surface="#ffffff",
    primary_button="#1f9e89",
    checker_a="#e3e6ec",
    checker_b="#d8dce4",
    primary_button_hover="#1a8574",
)

DARK_THEME = ThemeSpec(
    name="dark",
    window_bg="#111318",
    surface_bg="#181c24",
    panel_bg="#1b1f26",
    text="#e6edf3",
    muted="#9aa7b8",
    border="#313848",
    accent="#7aa2f7",
    accent_soft="#b3c7ff",
    selection_bg="rgba(122,162,247,0.12)",
    hover_bg="rgba(148,163,184,0.10)",
    selected_border="#7aa2f7",
    hover_border="#94a3b8",
    stats_label="#8b93a7",
    stats_value="#d6deea",
    hover_panel_bg="#181825",
    hover_panel_border="#45475a",
    hint_text="#9aa7b8",
    section_heading="#6b7080",
    panel_surface="#161821",
    primary_button="#2fd4b8",
    checker_a="#0a0b0e",
    checker_b="#101116",
    primary_button_hover="#29b9a0",
)

SEPIA_THEME = ThemeSpec(
    name="sepia",
    window_bg="#f3e8d7",
    surface_bg="#f8f0e4",
    panel_bg="#f4e7d6",
    text="#2f2415",
    muted="#6f5c47",
    border="#d0bea4",
    accent="#a56a32",
    accent_soft="#d2a06c",
    selection_bg="rgba(165,106,50,0.12)",
    hover_bg="rgba(165,106,50,0.08)",
    selected_border="#a56a32",
    hover_border="#cc955d",
    stats_label="#7c6349",
    stats_value="#2f2415",
    hover_panel_bg="#f8efe1",
    hover_panel_border="#c9b292",
    hint_text="#7c6349",
    section_heading="#9a8b7a",
    panel_surface="#f4ebd9",
    primary_button="#b3673b",
    checker_a="#ddd0b5",
    checker_b="#d2c4a7",
    primary_button_hover="#9a5832",
)

THEMES: dict[str, ThemeSpec] = {
    theme.name: theme for theme in (LIGHT_THEME, DARK_THEME, SEPIA_THEME)
}


def theme_names() -> tuple[str, ...]:
    return tuple(THEMES)


def get_theme(name: str) -> ThemeSpec:
    return THEMES.get(name, LIGHT_THEME)


def build_palette(theme: ThemeSpec) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme.window_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme.surface_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.panel_bg))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.hover_panel_bg))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme.panel_bg))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor(theme.accent))
    return palette


def build_stylesheet(theme: ThemeSpec) -> str:
    sections = (
        _base_surface_styles(theme),
        _control_styles(theme),
        _viewport_styles(theme),
        _settings_dialog_styles(theme),
    )
    return "\n".join(sections)


def _base_surface_styles(theme: ThemeSpec) -> str:
    return f"""
        QMainWindow, QDialog {{
            background: {theme.window_bg};
            color: {theme.text};
        }}
        QWidget {{
            color: {theme.text};
        }}
        QGroupBox {{
            background: {theme.panel_bg};
            border: 1px solid {theme.border};
            border-radius: 12px;
            margin-top: 14px;
            padding: 12px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: {theme.text};
        }}
        QLabel#sectionTitle {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: {theme.section_heading};
        }}
    """


def _control_styles(theme: ThemeSpec) -> str:
    return f"""
        QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox {{
            background: {theme.surface_bg};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 8px;
            padding: 6px 10px;
        }}
        QPushButton:hover, QToolButton:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
            border-color: {theme.accent};
        }}
        QPushButton:pressed, QToolButton:pressed {{
            background: {theme.selection_bg};
        }}
        QComboBox::drop-down {{
            border-left: 1px solid {theme.border};
            width: 24px;
        }}
        QScrollArea {{
            background: transparent;
            border: 1px solid {theme.border};
            border-radius: 10px;
        }}
        QToolButton#settingsButton {{
            min-width: 34px;
            max-width: 34px;
            min-height: 34px;
            max-height: 34px;
            font-size: 16px;
            font-weight: 700;
            padding: 0;
        }}
        QRadioButton {{
            spacing: 8px;
        }}
        QDialogButtonBox QPushButton {{
            min-width: 84px;
        }}
        QPushButton#primaryButton {{
            background: {theme.primary_button};
            color: #ffffff;
            border: none;
            font-weight: 600;
            padding: 6px 14px;
        }}
        QPushButton#primaryButton:hover {{
            background: {theme.primary_button_hover};
        }}
    """


def _viewport_styles(theme: ThemeSpec) -> str:
    return f"""
        QLabel#hoverPanel {{
            background: {theme.hover_panel_bg};
            color: {theme.text};
            border: 1px solid {theme.hover_panel_border};
            border-radius: 6px;
            padding: 8px 10px;
        }}
        QLabel#viewportHint {{
            color: {theme.hint_text};
            font-size: 10px;
        }}
    """


def _settings_dialog_styles(theme: ThemeSpec) -> str:
    return f"""
        QDialog#settingsDialog {{
            background: {theme.window_bg};
        }}
        QWidget#settingsRoot {{
            background: {theme.window_bg};
        }}
        QFrame#settingsSidebar {{
            background: {theme.panel_bg};
            border-right: 1px solid {theme.border};
        }}
        QLabel#settingsSidebarTitle {{
            color: {theme.muted};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 2px 6px 6px 6px;
        }}
        QPushButton#settingsNavActive {{
            text-align: left;
            background: {theme.selection_bg};
            border: 1px solid {theme.selected_border};
            color: {theme.text};
            border-radius: 10px;
            padding: 9px 10px;
            font-weight: 600;
        }}
        QPushButton#settingsNavDisabled {{
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            color: {theme.muted};
            border-radius: 10px;
            padding: 9px 10px;
        }}
        QLabel#settingsHeading {{
            font-size: 34px;
            font-weight: 750;
            color: {theme.text};
        }}
        QLabel#settingsSubtitle {{
            color: {theme.muted};
            font-size: 14px;
            margin-bottom: 8px;
        }}
        QLabel#settingsSectionTitle {{
            color: {theme.text};
            font-size: 20px;
            font-weight: 650;
            margin-top: 6px;
        }}
        QFrame#settingsThemeCard {{
            background: {theme.surface_bg};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        QRadioButton#settingsThemeOption {{
            spacing: 10px;
            font-size: 15px;
            padding: 8px 6px;
            color: {theme.text};
        }}
        QDialogButtonBox#settingsButtons {{
            border-top: 1px solid {theme.border};
            padding-top: 10px;
        }}
    """


def apply_theme(app: QApplication, theme_name: str) -> ThemeSpec:
    theme = get_theme(theme_name)
    if app is not None:
        app.setPalette(build_palette(theme))
        app.setStyleSheet(build_stylesheet(theme))
    return theme
