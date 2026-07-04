from __future__ import annotations

import unittest
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from fractal_studio.ui.sections import panel_state as panel_state_module  # noqa: E402
from fractal_studio.ui.sections.panel_state import MainWindowColormapState  # noqa: E402


class RecordingPalettePanel:
    def __init__(self) -> None:
        self.save_kwargs: dict | None = None

    def save_palette_json(self, **kwargs) -> bool:
        self.save_kwargs = kwargs
        return True


class TestColormapStateSavePaletteJson(unittest.TestCase):
    def test_save_palette_json_delegates_with_profile_palette_size(self) -> None:
        panel = RecordingPalettePanel()
        statuses: list[str] = []
        state = MainWindowColormapState(
            palette_panel=panel,
            backend=object(),
            on_status=statuses.append,
            legacy_palette_size_getter=lambda: 256,
            palette_size_getter=lambda: 2048,
        )
        state.set_editor(object())

        original_dialog = panel_state_module.QFileDialog.getSaveFileName
        panel_state_module.QFileDialog.getSaveFileName = staticmethod(
            lambda *args, **kwargs: (str(Path("C:/tmp/out.json")), "")
        )
        try:
            state.save_palette_json()
        finally:
            panel_state_module.QFileDialog.getSaveFileName = original_dialog

        assert panel.save_kwargs is not None
        self.assertEqual(panel.save_kwargs["palette_size"], 2048)
        self.assertEqual(panel.save_kwargs["path"], Path("C:/tmp/out.json"))

    def test_save_palette_json_passes_none_path_when_dialog_cancelled(self) -> None:
        panel = RecordingPalettePanel()
        state = MainWindowColormapState(
            palette_panel=panel,
            backend=object(),
            on_status=lambda _msg: None,
            legacy_palette_size_getter=lambda: 256,
            palette_size_getter=lambda: 2048,
        )
        original_dialog = panel_state_module.QFileDialog.getSaveFileName
        panel_state_module.QFileDialog.getSaveFileName = staticmethod(
            lambda *args, **kwargs: ("", "")
        )
        try:
            state.save_palette_json()
        finally:
            panel_state_module.QFileDialog.getSaveFileName = original_dialog

        assert panel.save_kwargs is not None
        self.assertIsNone(panel.save_kwargs["path"])
