from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.integration

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from fractal_studio.backend import CoreBackend, default_profile  # noqa: E402
from fractal_studio.ui.sections.ports import MainWindowSectionsPorts  # noqa: E402
from fractal_studio.ui.sections.sections import MainWindowSections  # noqa: E402


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class RecordingColormapPorts:
    """Implements ColormapPanelPorts, recording which port methods fire."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.backend = CoreBackend(None)
        self.backend_profile = default_profile()
        self.viewport = None

    def show_status(self, message: str) -> None:
        self.calls.append("show_status")

    def set_editor(self, editor) -> None:
        self.calls.append("set_editor")

    def update_palette_previews(self, palette) -> None:
        pass

    def update_control_summary(self, points) -> None:
        pass

    def save_favorite(self) -> None:
        self.calls.append("save_favorite")

    def save_palette_json(self) -> None:
        self.calls.append("save_palette_json")

    def load_palette_json(self) -> None:
        self.calls.append("load_palette_json")

    def export_legacy_map(self) -> None:
        self.calls.append("export_legacy_map")


def _find_button(panel, label: str) -> QPushButton:
    buttons = [b for b in panel.findChildren(QPushButton) if b.text() == label]
    assert len(buttons) == 1, f"expected exactly one '{label}' button, found {len(buttons)}"
    return buttons[0]


class TestColormapSaveJsonWiring(unittest.TestCase):
    def test_save_json_button_triggers_palette_save_not_favorite(self) -> None:
        _get_app()
        colormap_ports = RecordingColormapPorts()
        sections = MainWindowSections(
            MainWindowSectionsPorts(
                viewport=None,
                palette=None,
                colormap=colormap_ports,
                backend=None,
                export=None,
                favorites=None,
                sidebar=None,
            )
        )
        panel = sections.build_colormap_panel()

        _find_button(panel, "Save JSON").click()

        self.assertIn("save_palette_json", colormap_ports.calls)
        self.assertNotIn("save_favorite", colormap_ports.calls)
