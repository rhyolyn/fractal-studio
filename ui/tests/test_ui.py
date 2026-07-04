from __future__ import annotations

import gc
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path

import pytest

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QComboBox, QSpinBox
from tests.support import (
    DummyEditorBackend,
    DummyPaletteBackend,
    DummyUnavailableBackend,
    QtWindowTestCase,
    _FULL_CAPS,
    get_app as _get_app,
)


@pytest.mark.integration
class TestMainWindowController(unittest.TestCase):
    def test_on_export_clicked_uses_custom_dimensions(self) -> None:
        from fractal_studio.application.controllers.export_controller import (
            ExportController,
        )

        class Box:
            def __init__(self, value: int) -> None:
                self._value = value

            def value(self) -> int:
                return self._value

        controller = ExportController(export_service=object())
        captured: list[tuple[int, int]] = []
        custom_sizes: list[tuple[int, int]] = []

        controller.on_export_clicked(
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            index=1,
            custom_width_box=Box(1234),
            custom_height_box=Box(567),
            set_custom_size=lambda w, h: custom_sizes.append((w, h)),
            export_callback=lambda w, h: captured.append((w, h)),
        )

        self.assertEqual(custom_sizes, [(1234, 567)])
        self.assertEqual(captured, [(1234, 567)])

    def test_on_export_clicked_uses_selected_preset_dimensions(self) -> None:
        from fractal_studio.application.controllers.export_controller import (
            ExportController,
        )

        controller = ExportController(export_service=object())
        captured: list[tuple[int, int]] = []
        custom_sizes: list[tuple[int, int]] = []

        controller.on_export_clicked(
            export_presets=[("1080 × 1080", 1080, 1080), ("Custom…", 0, 0)],
            index=0,
            custom_width_box=None,
            custom_height_box=None,
            set_custom_size=lambda w, h: custom_sizes.append((w, h)),
            export_callback=lambda w, h: captured.append((w, h)),
        )

        self.assertEqual(custom_sizes, [])
        self.assertEqual(captured, [(1080, 1080)])


@pytest.mark.integration
class TestWorkspaceLayout(QtWindowTestCase):
    def test_viewport_default_min_width_matches_preview_column(self) -> None:
        w = self.make_window()
        self.assertIsNotNone(w.viewport)
        self.assertEqual(w.viewport.minimumWidth(), 520)


@pytest.mark.integration
class TestFavoritesController(unittest.TestCase):
    def test_persist_favorites_passes_snapshots_to_repo(self) -> None:
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        captured: list[list[object]] = []
        controller = FavoritesController()
        from fractal_studio.state import StandardParams
        base_viewport = ViewportState(
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
        snapshot_one = FavoriteSnapshot(
            favorite_id="1",
            saved_at="2026-05-25T12:34:56",
            aspect_ratio_mode="square",
            name="One",
            viewport=base_viewport,
            control_points=[(1, 2, 3)],
            palette=[(4, 5, 6)],
            thumbnail="thumb-1",
        )
        snapshot_two = FavoriteSnapshot(
            favorite_id="2",
            saved_at="2026-05-25T12:34:57",
            aspect_ratio_mode="landscape",
            name="Two",
            viewport=base_viewport,
            control_points=[(7, 8, 9)],
            palette=[(10, 11, 12)],
            thumbnail="thumb-2",
        )

        controller.persist_favorites(
            favorites=[snapshot_one, snapshot_two],
            save_to_repo=lambda snapshots: captured.append(snapshots),
        )

        self.assertEqual(len(captured), 1)
        self.assertEqual([snapshot.favorite_id for snapshot in captured[0]], ["1", "2"])

    def test_load_favorites_returns_snapshots(self) -> None:
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        from fractal_studio.state import StandardParams
        controller = FavoritesController()
        snapshot = FavoriteSnapshot(
            favorite_id="fav-1",
            saved_at="2026-05-25T12:34:56",
            aspect_ratio_mode="square",
            name="Favorite",
            viewport=ViewportState(
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
            ),
            control_points=[(1, 2, 3)],
            palette=[(4, 5, 6)],
            thumbnail="thumb",
        )

        loaded = controller.load_favorites(lambda: [snapshot])

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].favorite_id, "fav-1")
        self.assertEqual(loaded[0].name, "Favorite")

    def test_build_favorite_name_adds_suffix_when_base_exists(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import StandardParams, ViewportState

        controller = FavoritesController()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            formula_params=StandardParams(),
            power=2,
            coloring_mode=default_profile().coloring_model,
            palette_offset=0.0,
        )

        def fixed_now() -> object:
            import datetime

            return datetime.datetime(2026, 5, 25, 12, 34, 56)

        base_name = "Mandelbrot (-0.750, 0.100) 2026-05-25 12:34:56"
        result = controller.build_favorite_name(
            state, {base_name, f"{base_name} (2)"}, fixed_now
        )

        self.assertEqual(result, f"{base_name} (3)")

    def test_build_favorite_name_uses_base_when_available(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import StandardParams, ViewportState

        controller = FavoritesController()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            formula_params=StandardParams(),
            power=2,
            coloring_mode=default_profile().coloring_model,
            palette_offset=0.0,
        )

        def fixed_now() -> object:
            import datetime

            return datetime.datetime(2026, 5, 25, 12, 34, 56)

        result = controller.build_favorite_name(state, set(), fixed_now)

        self.assertEqual(result, "Mandelbrot (-0.750, 0.100) 2026-05-25 12:34:56")

    def test_save_favorite_orchestrates_callbacks(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import StandardParams, ViewportState

        controller = FavoritesController()
        calls: list[object] = []
        viewport_state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            formula_params=StandardParams(),
            power=2,
            coloring_mode=default_profile().coloring_model,
            palette_offset=0.0,
        )

        snapshot = controller.save_favorite(
            viewport_state=viewport_state,
            palette=[(9, 8, 7)],
            control_points=[],
            aspect_ratio_mode="square",
            favorites=[],
            build_name=lambda state: f"{state.formula} saved",
            capture_thumbnail=lambda: "thumb",
            add_favorite=lambda fav: calls.append(("favorite", fav.name)),
            add_row=lambda fav: calls.append(("row", fav.thumbnail)),
            persist=lambda: calls.append("persist"),
            show_status=lambda text: calls.append(("status", text)),
        )

        self.assertEqual(snapshot.name, "Mandelbrot saved")
        self.assertEqual(calls[0], ("favorite", "Mandelbrot saved"))
        self.assertEqual(calls[1], ("row", "thumb"))
        self.assertEqual(calls[2], "persist")
        self.assertEqual(calls[3], ("status", "Saved favorite: Mandelbrot saved"))

    def test_load_favorite_row_orchestrates_restore_and_selection(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        class EditorStub:
            def __init__(self) -> None:
                self.points = []

            def set_control_points(self, points) -> None:
                self.points = list(points)

        class PreviewStub:
            def __init__(self) -> None:
                self.palette = []

            def set_palette(self, palette) -> None:
                self.palette = list(palette)

        from fractal_studio.state import StandardParams
        controller = FavoritesController()
        editor = EditorStub()
        preview_palette = PreviewStub()
        state = ViewportState(
            formula="Mandelbrot",
            center_x=-0.75,
            center_y=0.1,
            scale=0.003,
            max_iterations=256,
            is_julia=False,
            formula_params=StandardParams(),
            power=2,
            coloring_mode=default_profile().coloring_model,
            palette_offset=0.0,
        )
        snapshot = FavoriteSnapshot(
            favorite_id="1",
            saved_at="now",
            aspect_ratio_mode="portrait",
            name="Saved Favorite",
            viewport=state,
            control_points=[(1, 2, 3)],
            palette=[(9, 8, 7)],
            thumbnail="thumb",
        )
        favorites = [snapshot]
        rows = [object()]
        selected: list[object] = []
        messages: list[str] = []
        aspect_modes: list[str] = []

        def restore_snapshot(snap: FavoriteSnapshot) -> None:
            controller.restore_snapshot(
                snapshot=snap,
                apply_viewport_state=lambda state, rerender: None,
                apply_control_points=lambda pts: editor.set_control_points(pts),
                apply_palette=lambda pal: preview_palette.set_palette(pal),
                apply_params=lambda params: None,
                set_cycle_active=lambda active: None,
                apply_aspect_ratio_mode=aspect_modes.append,
            )

        controller.load_favorite_row(
            row=rows[0],
            favorites=favorites,
            rows=rows,
            restore_snapshot=restore_snapshot,
            select_row=selected.append,
            show_status=messages.append,
        )

        self.assertEqual(aspect_modes, ["portrait"])
        self.assertEqual(selected, [rows[0]])
        self.assertEqual(messages, ["Restored: Saved Favorite"])
        self.assertEqual(editor.points, [(1, 2, 3)])
        self.assertEqual(preview_palette.palette, [(9, 8, 7)])

    def test_update_palette_previews_sets_summary_and_preview_palettes(self) -> None:
        from fractal_studio.backend import default_profile
        from fractal_studio.application.controllers.favorites_controller import (
            FavoritesController,
        )

        control_points = [
            (10, 20, 30),
            (40, 50, 60),
            (70, 80, 90),
            (100, 110, 120),
        ]

        class BackendStub:
            available = True

            def generate_palette(self, pts, palette_size):
                return list(pts[:palette_size])

        controller = FavoritesController()
        preview_palette_result: list[list] = [[]]
        legacy_palette_result: list[list] = [[]]
        summary_texts: list[str] = []
        backend = BackendStub()

        controller.update_palette_previews(
            palette=[(1, 2, 3), (4, 5, 6)],
            get_control_points=lambda: control_points,
            backend=backend,
            legacy_palette_size=default_profile().legacy_palette_size,
            set_preview_palette=lambda pal: preview_palette_result.__setitem__(0, list(pal)),
            set_legacy_palette=lambda pal: legacy_palette_result.__setitem__(0, list(pal)),
            set_summary_text=summary_texts.append,
        )

        self.assertEqual(preview_palette_result[0], [(1, 2, 3), (4, 5, 6)])
        self.assertEqual(legacy_palette_result[0], control_points)
        self.assertTrue(summary_texts)
        self.assertIn("Generated 2 internal colors", summary_texts[0])


@pytest.mark.integration
class TestFavoritesPanelCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _get_app()

    def test_build_row_uses_placeholder_for_invalid_thumbnail(self) -> None:
        from fractal_studio.application.coordinators.favorites_panel_coordinator import (
            FavoritesPanelCoordinator,
        )
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}

        def row_factory(*args, **kwargs):
            captured["pixmap"] = args[0]
            captured["hover_presenter"] = kwargs.get("hover_presenter")
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#ff0000"))
            return pixmap

        row = coordinator.build_row(
            favorite={"name": "sample", "thumbnail": "broken"},
            hover_panel=hover_panel,
            on_select=lambda _: None,
            on_activate=lambda _: None,
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        self.assertIsNotNone(row)
        self.assertFalse(captured["pixmap"].isNull())

    def test_select_row_deselects_previous(self) -> None:
        from fractal_studio.application.coordinators.favorites_panel_coordinator import (
            FavoritesPanelCoordinator,
        )

        class Row:
            def __init__(self) -> None:
                self.calls: list[bool] = []

            def set_selected(self, selected: bool) -> None:
                self.calls.append(selected)

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        old_row = Row()
        new_row = Row()

        selected = coordinator.select_row(old_row, new_row)

        self.assertIs(selected, new_row)
        self.assertEqual(old_row.calls, [False])
        self.assertEqual(new_row.calls, [True])

    def test_delete_selected_removes_row_and_favorite(self) -> None:
        from fractal_studio.application.coordinators.favorites_panel_coordinator import (
            FavoritesPanelCoordinator,
        )

        class Row:
            def __init__(self, name: str) -> None:
                self.name = name
                self.deleted = False

            def set_selected(self, selected: bool) -> None:
                pass

            def deleteLater(self) -> None:
                self.deleted = True

        class Layout:
            def __init__(self) -> None:
                self.removed: list[Row] = []

            def removeWidget(self, row: Row) -> None:
                self.removed.append(row)

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        row_a = Row("a")
        row_b = Row("b")
        rows = [row_a, row_b]
        favorites = [{"id": "a"}, {"id": "b"}]
        layout = Layout()

        selected = coordinator.delete_selected(
            selected_row=row_b,
            rows=rows,
            favorites=favorites,
            scroll_layout=layout,
        )

        self.assertIsNone(selected)
        self.assertEqual(rows, [row_a])
        self.assertEqual(favorites, [{"id": "a"}])
        self.assertEqual(layout.removed, [row_b])
        self.assertTrue(row_b.deleted)

    def test_build_row_with_callbacks_invokes_owner_handlers(self) -> None:
        from fractal_studio.application.coordinators.favorites_panel_coordinator import (
            FavoritesPanelCoordinator,
        )
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}

        class Owner:
            def __init__(self) -> None:
                self.selected: list[object] = []
                self.activated: list[object] = []

            def on_selected(self, row: object) -> None:
                self.selected.append(row)

            def on_activated(self, row: object) -> None:
                self.activated.append(row)

        owner = Owner()

        def row_factory(*args, **kwargs):
            captured["on_select"] = args[3]
            captured["on_activate"] = args[4]
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#00ff00"))
            return pixmap

        row = coordinator.build_row_with_callbacks(
            favorite={"name": "sample", "thumbnail": "broken"},
            owner=owner,
            hover_panel=hover_panel,
            on_select_row=lambda current_owner, current_row: current_owner.on_selected(
                current_row
            ),
            on_activate_row=lambda current_owner, current_row: (
                current_owner.on_activated(current_row)
            ),
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        captured["on_select"](row)
        captured["on_activate"](row)

        self.assertEqual(owner.selected, [row])
        self.assertEqual(owner.activated, [row])

    def test_build_row_with_callbacks_noops_after_owner_collected(self) -> None:
        from fractal_studio.application.coordinators.favorites_panel_coordinator import (
            FavoritesPanelCoordinator,
        )
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QLabel

        coordinator = FavoritesPanelCoordinator(hover_presenter=object())
        hover_panel = QLabel()
        captured: dict[str, object] = {}
        calls: list[str] = []

        class Owner:
            pass

        owner = Owner()

        def row_factory(*args, **kwargs):
            captured["on_select"] = args[3]
            captured["on_activate"] = args[4]
            return object()

        def placeholder() -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor("#0000ff"))
            return pixmap

        coordinator.build_row_with_callbacks(
            favorite={"name": "sample", "thumbnail": "broken"},
            owner=owner,
            hover_panel=hover_panel,
            on_select_row=lambda current_owner, current_row: calls.append("select"),
            on_activate_row=lambda current_owner, current_row: calls.append("activate"),
            row_factory=row_factory,
            decode_thumbnail=lambda _: QPixmap(),
            placeholder_pixmap=placeholder,
        )

        del owner
        gc.collect()
        captured["on_select"](object())
        captured["on_activate"](object())

        self.assertEqual(calls, [])


@pytest.mark.integration
class TestFavoritesWorkflowCoordinator(unittest.TestCase):
    def test_save_favorite_returns_early_without_viewport(self) -> None:
        from fractal_studio.application.workflows.favorites_workflow_coordinator import (
            FavoritesWorkflowCoordinator,
        )

        class ControllerStub:
            def __init__(self) -> None:
                self.called = False

            def save_favorite(self, **kwargs):
                self.called = True

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        controller = ControllerStub()
        coordinator = FavoritesWorkflowCoordinator(controller, PanelStub())

        coordinator.save_favorite(
            viewport=None,
            editor=None,
            aspect_ratio_mode="square",
            favorites=[],
            build_name=lambda state: "name",
            capture_thumbnail=lambda: "thumb",
            add_favorite=lambda fav: None,
            add_row=lambda fav: None,
            persist_favorites=lambda: None,
            show_status=lambda msg: None,
        )

        self.assertFalse(controller.called)

    def test_load_selected_favorite_calls_load_row_only_when_ready(self) -> None:
        from fractal_studio.application.workflows.favorites_workflow_coordinator import (
            FavoritesWorkflowCoordinator,
        )

        class ControllerStub:
            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        coordinator = FavoritesWorkflowCoordinator(ControllerStub(), PanelStub())
        calls: list[object] = []

        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=object(),
            selected_row="row-1",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=None,
            params_panel=object(),
            selected_row="row-2",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=None,
            selected_row="row-3",
            load_row=calls.append,
        )
        coordinator.load_selected_favorite(
            viewport=object(),
            params_panel=object(),
            selected_row=None,
            load_row=calls.append,
        )

        self.assertEqual(calls, ["row-1"])

    def test_delete_selected_favorite_persists_when_selection_cleared(self) -> None:
        from fractal_studio.application.workflows.favorites_workflow_coordinator import (
            FavoritesWorkflowCoordinator,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        class ControllerStub:
            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return None

        from fractal_studio.state import StandardParams
        coordinator = FavoritesWorkflowCoordinator(ControllerStub(), PanelStub())
        persisted: list[str] = []
        snapshot = FavoriteSnapshot(
            favorite_id="a",
            saved_at="2026-05-25T12:34:56",
            aspect_ratio_mode="square",
            name="A",
            viewport=ViewportState(
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
            ),
            control_points=[],
            palette=[],
            thumbnail="",
        )

        selected = coordinator.delete_selected_favorite(
            selected_row=object(),
            rows=[object()],
            favorites=[snapshot],
            scroll_layout=object(),
            persist_favorites=lambda: persisted.append("saved"),
        )

        self.assertIsNone(selected)
        self.assertEqual(persisted, ["saved"])

    def test_build_favorite_name_delegates_with_existing_names(self) -> None:
        from fractal_studio.application.workflows.favorites_workflow_coordinator import (
            FavoritesWorkflowCoordinator,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        class ControllerStub:
            def __init__(self) -> None:
                self.existing_names: set[str] | None = None

            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                self.existing_names = existing_names
                return "resolved-name"

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        from fractal_studio.state import StandardParams
        controller = ControllerStub()
        coordinator = FavoritesWorkflowCoordinator(controller, PanelStub())
        state = ViewportState(
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

        name = coordinator.build_favorite_name(
            state=state,
            favorites=[
                FavoriteSnapshot(
                    favorite_id="1",
                    saved_at="2026-05-25T12:34:56",
                    aspect_ratio_mode="square",
                    name="A",
                    viewport=state,
                    control_points=[],
                    palette=[],
                    thumbnail="",
                ),
                FavoriteSnapshot(
                    favorite_id="2",
                    saved_at="2026-05-25T12:34:57",
                    aspect_ratio_mode="landscape",
                    name="B",
                    viewport=state,
                    control_points=[],
                    palette=[],
                    thumbnail="",
                ),
            ],
            now=lambda: None,
        )

        self.assertEqual(name, "resolved-name")
        self.assertEqual(controller.existing_names, {"A", "B"})

    def test_load_favorite_row_delegates_to_controller(self) -> None:
        from fractal_studio.application.workflows.favorites_workflow_coordinator import (
            FavoritesWorkflowCoordinator,
        )
        from fractal_studio.state import FavoriteSnapshot, ViewportState

        class ControllerStub:
            def __init__(self) -> None:
                self.called: dict[str, object] | None = None

            def save_favorite(self, **kwargs):
                return None

            def build_favorite_name(self, state, existing_names, now):
                return "unused"

            def load_favorite_row(self, **kwargs):
                self.called = kwargs

        class PanelStub:
            def delete_selected(self, **kwargs):
                return kwargs["selected_row"]

        from fractal_studio.state import StandardParams
        controller = ControllerStub()
        coordinator = FavoritesWorkflowCoordinator(controller, PanelStub())
        row = object()
        rows = [row]
        favorites = [
            FavoriteSnapshot(
                favorite_id="fav-1",
                saved_at="2026-05-25T12:34:56",
                aspect_ratio_mode="square",
                name="Favorite",
                viewport=ViewportState(
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
                ),
                control_points=[],
                palette=[],
                thumbnail="",
            )
        ]

        coordinator.load_favorite_row(
            row=row,
            favorites=favorites,
            rows=rows,
            viewport=object(),
            params_panel=object(),
            editor=object(),
            preview_palette=object(),
            apply_aspect_ratio_mode=lambda mode: None,
            select_row=lambda selected: None,
            show_status=lambda message: None,
        )

        self.assertIsNotNone(controller.called)
        self.assertIs(controller.called["row"], row)
        self.assertIs(controller.called["rows"], rows)
        self.assertIs(controller.called["favorites"], favorites)


if __name__ == "__main__":
    unittest.main()
