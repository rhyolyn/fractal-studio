from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))


@pytest.mark.integration
class TestMainWindowSectionPanelStates(unittest.TestCase):
    def _favorite_snapshot(self):
        from fractal_studio.state import FavoriteSnapshot, StandardParams, ViewportState

        viewport = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            formula_params=StandardParams(),
            power=2,
            coloring_mode="smooth",
            palette_offset=0.0,
        )
        return FavoriteSnapshot(
            favorite_id="fav-1",
            saved_at="2026-05-27T10:00:00",
            aspect_ratio_mode="square",
            name="Favorite",
            viewport=viewport,
            control_points=[(1, 2, 3)],
            palette=[(4, 5, 6)],
            thumbnail="thumb",
        )

    def test_viewport_state_uses_bound_collaborators(self) -> None:
        from fractal_studio.ui.sections.panel_state import (
            MainWindowViewportState,
        )

        class ControllerStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def apply_aspect_ratio_mode(self, **kwargs):
                self.calls.append(kwargs)
                kwargs["refresh_export_presets"]()
                return "portrait"

        class ExportPanelStub:
            def on_aspect_ratio_changed(
                self, *, index: int, apply_aspect_ratio_mode
            ) -> None:
                self.index = index
                apply_aspect_ratio_mode("portrait", False)

        controller = ControllerStub()
        export_panel = ExportPanelStub()
        refreshed: list[str] = []
        state = MainWindowViewportState(
            controller=controller,
            export_panel=export_panel,
            refresh_export_presets=lambda: refreshed.append("done"),
        )
        state.set_viewport(object())
        state.set_aspect_ratio_combo(object())

        state.handle_aspect_ratio_changed(2)

        self.assertEqual(export_panel.index, 2)
        self.assertEqual(state.aspect_ratio_mode, "portrait")
        self.assertEqual(refreshed, ["done"])
        self.assertEqual(controller.calls[0]["update_combo"], False)

    def test_sidebar_state_uses_bound_collaborators(self) -> None:
        from fractal_studio.ui.sections.panel_state import (
            MainWindowSidebarState,
        )

        class WiringStub:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object]] = []

            def connect_params_and_viewport(self, params_panel, viewport) -> None:
                self.calls.append((params_panel, viewport))

        class SettingsStub:
            def backend_state_message(
                self, backend_loaded: bool, backend_available: bool
            ) -> str:
                return f"loaded={backend_loaded}, available={backend_available}"

        params_panel = object()
        viewport = object()
        wiring = WiringStub()
        state = MainWindowSidebarState(
            sidebar_wiring=wiring,
            viewport_getter=lambda: viewport,
            settings_service=SettingsStub(),
            backend_loaded_getter=lambda: True,
            backend_available_getter=lambda: False,
        )
        state.set_params_panel(params_panel)

        state.connect_params_and_viewport()

        self.assertEqual(wiring.calls, [(params_panel, viewport)])
        self.assertEqual(state.backend_state_message(), "loaded=True, available=False")

    def test_palette_and_colormap_states_use_bound_collaborators(self) -> None:
        from fractal_studio.ui.sections.panel_state import (
            MainWindowColormapState,
            MainWindowPaletteState,
        )

        class PalettePreviewStub:
            def __init__(self) -> None:
                self.preview_calls: list[dict[str, object]] = []
                self.summary_calls: list[tuple[object, object]] = []

            def update_palette_previews(self, **kwargs) -> None:
                self.preview_calls.append(kwargs)

            def update_control_summary(self, label, points) -> None:
                self.summary_calls.append((label, points))

        class PalettePanelStub:
            def __init__(self) -> None:
                self.load_calls: list[dict[str, object]] = []
                self.export_calls: list[dict[str, object]] = []

            def load_palette_json(self, **kwargs) -> None:
                self.load_calls.append(kwargs)

            def export_legacy_map(self, **kwargs) -> None:
                self.export_calls.append(kwargs)

        preview = PalettePreviewStub()
        palette_state = MainWindowPaletteState(
            palette_preview=preview,
            backend="backend",
            legacy_palette_size_getter=lambda: 256,
            editor_getter=lambda: "editor",
        )
        palette_state.set_preview_widgets("preview", "legacy")
        palette_state.set_palette_summary_labels("points", "summary")
        palette_state.update_palette_previews([(1, 2, 3)])
        palette_state.update_control_summary([(4, 5, 6)])

        self.assertEqual(preview.preview_calls[0]["backend"], "backend")
        self.assertEqual(preview.preview_calls[0]["editor"], "editor")
        self.assertEqual(preview.preview_calls[0]["legacy_palette_size"], 256)
        self.assertEqual(preview.summary_calls, [("points", [(4, 5, 6)])])

        panel = PalettePanelStub()
        colormap_state = MainWindowColormapState(
            palette_panel=panel,
            backend="backend",
            on_status=lambda msg: None,
            legacy_palette_size_getter=lambda: 512,
        )
        colormap_state.set_editor("editor")
        dialog_target = "fractal_studio.ui.sections.panel_state.QFileDialog"
        with patch(dialog_target) as mock_dialog:
            mock_dialog.getOpenFileName.return_value = ("", "")
            mock_dialog.getSaveFileName.return_value = ("", "")
            colormap_state.load_palette_json()
            colormap_state.export_legacy_map()

        self.assertEqual(panel.load_calls[0]["backend"], "backend")
        self.assertEqual(panel.export_calls[0]["legacy_palette_size"], 512)

    def test_export_state_uses_bound_collaborators(self) -> None:
        from fractal_studio.ui.sections.panel_state import (
            MainWindowExportState,
        )

        class ExportPanelStub:
            def __init__(self) -> None:
                self.refresh_calls: list[dict[str, object]] = []
                self.click_calls: list[dict[str, object]] = []

            def refresh_export_presets(self, **kwargs):
                self.refresh_calls.append(kwargs)
                return [("Portrait", 900, 1200)]

            def on_export_clicked(self, **kwargs) -> None:
                self.click_calls.append(kwargs)
                kwargs["set_custom_size"](900, 1200)
                # export_callback is intentionally not called here to avoid
                # opening a native file dialog in tests

        class ViewportStub:
            def to_state(self):
                return "viewport_state"

            def palette(self):
                return []

        controller = object()
        export_panel = ExportPanelStub()
        state = MainWindowExportState(
            export_panel=export_panel,
            controller=controller,
            on_status=lambda msg: None,
            viewport_getter=lambda: ViewportStub(),
            aspect_ratio_mode_getter=lambda: "portrait",
        )
        state.set_export_combo(object())

        state.refresh_export_presets()
        state.on_export_clicked()

        self.assertEqual(state.export_presets, [("Portrait", 900, 1200)])
        self.assertEqual(export_panel.refresh_calls[0]["aspect_ratio_mode"], "portrait")
        self.assertEqual(state.custom_width, 900)
        self.assertEqual(state.custom_height, 1200)

    def test_favorites_state_uses_bound_collaborators(self) -> None:
        from fractal_studio.ui.sections.panel_state import (
            MainWindowFavoritesState,
        )

        snapshot = self._favorite_snapshot()

        class FavoritesControllerStub:
            def __init__(self) -> None:
                self.persisted: list[list[object]] = []

            def load_favorites(self, loader):
                return loader()

            def persist_favorites(self, favorites, save) -> None:
                self.persisted.append(list(favorites))
                save(list(favorites))

        class FavoritesPanelStub:
            def __init__(self) -> None:
                self.build_calls: list[dict[str, object]] = []
                self.appended: list[object] = []
                self.selected: list[tuple[object, object]] = []

            def build_row_with_callbacks(self, **kwargs):
                self.build_calls.append(kwargs)
                return "row-1"

            def append_row(self, row, rows, layout) -> None:
                rows.append(row)
                self.appended.append((row, layout))

            def select_row(self, selected_row, row):
                self.selected.append((selected_row, row))
                return row

        class FavoritesWorkflowStub:
            def __init__(self) -> None:
                self.saved: list[dict[str, object]] = []
                self.loaded: list[dict[str, object]] = []
                self.deleted: list[dict[str, object]] = []

            def save_favorite(self, **kwargs) -> None:
                self.saved.append(kwargs)

            def build_favorite_name(self, **kwargs) -> str:
                return "favorite name"

            def load_favorite_row(self, **kwargs) -> None:
                self.loaded.append(kwargs)

            def delete_selected_favorite(self, **kwargs):
                self.deleted.append(kwargs)
                kwargs["persist_favorites"]()
                return None

        class RepoStub:
            def __init__(self) -> None:
                self.saved: list[list[object]] = []

            def load(self):
                return [snapshot]

            def save(self, favorites) -> None:
                self.saved.append(list(favorites))

        controller = FavoritesControllerStub()
        panel = FavoritesPanelStub()
        workflow = FavoritesWorkflowStub()
        repo = RepoStub()
        state = MainWindowFavoritesState(
            favorites_controller=controller,
            favorites_panel=panel,
            favorites_workflow=workflow,
            favorites_repo=repo,
            on_status=lambda msg: None,
            hover_panel_getter=lambda: "hover",
            viewport_getter=lambda: "viewport",
            params_panel_getter=lambda: "params",
            editor_getter=lambda: "editor",
            preview_palette_getter=lambda: "preview",
            apply_aspect_ratio_mode=lambda mode, update_combo=True: mode,
            aspect_ratio_mode_getter=lambda: "square",
        )
        state.set_favorites_scroll_container("widget", "layout")

        loaded = state.load_favorites()
        state.add_favorite_row(snapshot)
        state.select_favorite_row("row-1")
        state.activate_favorite_row("row-1")
        state.save_favorite()
        state.delete_selected_favorite()

        self.assertEqual(loaded, [snapshot])
        self.assertEqual(panel.build_calls[0]["owner"], None)
        self.assertEqual(panel.build_calls[0]["hover_panel"], "hover")
        self.assertEqual(state.selected_row, None)
        self.assertEqual(workflow.loaded[0]["viewport"], "viewport")
        self.assertEqual(workflow.loaded[0]["params_panel"], "params")
        self.assertEqual(workflow.saved[0]["aspect_ratio_mode"], "square")
        self.assertEqual(controller.persisted[0], [snapshot])
        self.assertEqual(repo.saved[0], [snapshot])


if __name__ == "__main__":
    unittest.main()
