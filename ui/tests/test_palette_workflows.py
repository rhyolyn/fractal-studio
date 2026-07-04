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
    get_app,
)


@pytest.mark.integration
class TestPaletteWorkflowService(unittest.TestCase):
    def test_save_palette_json_exports_and_reports_status(self) -> None:
        from fractal_studio.services.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []
        target = Path(tempfile.mkdtemp(prefix="fs_palette_save_")) / "palette.json"

        result = service.save_palette_json(
            path=target,
            backend=backend,
            control_points=[(10, 20, 30)],
            palette_size=2048,
            set_status=messages.append,
        )

        self.assertTrue(result)
        self.assertEqual(backend.saved, [(str(target), [(10, 20, 30)], 2048)])
        self.assertEqual(messages[-1], f"Saved palette to {target}")

    def test_load_palette_json_applies_control_points_and_reports_status(self) -> None:
        from fractal_studio.services.palette_service import PaletteWorkflowService

        backend = DummyPaletteBackend()
        service = PaletteWorkflowService()
        messages: list[str] = []
        control_points: list[tuple[int, int, int]] = []
        target = Path(tempfile.mkdtemp(prefix="fs_palette_load_")) / "palette.json"

        result = service.load_palette_json(
            path=target,
            backend=backend,
            set_control_points=control_points.extend,
            set_status=messages.append,
        )

        self.assertTrue(result)
        self.assertEqual(backend.loaded_paths, [str(target)])
        self.assertEqual(control_points, [(1, 2, 3), (4, 5, 6)])


@pytest.mark.integration
class TestPalettePanelCoordinator(unittest.TestCase):
    def test_save_palette_json_returns_false_without_editor(self) -> None:
        from fractal_studio.application.coordinators.palette_panel_coordinator import (
            PalettePanelCoordinator,
        )

        class WorkflowStub:
            def save_palette_json(self, **kwargs) -> bool:
                raise AssertionError("should not be called")

        coordinator = PalettePanelCoordinator(WorkflowStub())

        result = coordinator.save_palette_json(
            path=None,
            editor=None,
            backend=object(),
            palette_size=256,
            set_status=lambda _: None,
        )

        self.assertFalse(result)

    def test_load_palette_json_delegates_with_editor(self) -> None:
        from fractal_studio.application.coordinators.palette_panel_coordinator import (
            PalettePanelCoordinator,
        )

        class EditorStub:
            def set_control_points(self, points) -> None:
                pass

        class WorkflowStub:
            def __init__(self) -> None:
                self.called = False

            def load_palette_json(self, **kwargs) -> bool:
                self.called = True
                return True

        workflow = WorkflowStub()
        coordinator = PalettePanelCoordinator(workflow)

        result = coordinator.load_palette_json(
            path=Path(tempfile.mkdtemp()) / "p.json",
            editor=EditorStub(),
            backend=DummyPaletteBackend(),
            set_status=lambda _: None,
        )

        self.assertTrue(result)
        self.assertTrue(workflow.called)

    def test_export_legacy_map_delegates_control_points(self) -> None:
        from fractal_studio.application.coordinators.palette_panel_coordinator import (
            PalettePanelCoordinator,
        )

        class EditorStub:
            control_points = [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)]

        class WorkflowStub:
            def __init__(self) -> None:
                self.points = None

            def export_legacy_map(self, **kwargs) -> bool:
                self.points = kwargs["control_points"]
                return True

        workflow = WorkflowStub()
        coordinator = PalettePanelCoordinator(workflow)

        result = coordinator.export_legacy_map(
            path=Path(tempfile.mkdtemp()) / "palette.map",
            editor=EditorStub(),
            backend=DummyPaletteBackend(),
            legacy_palette_size=256,
            set_status=lambda _: None,
        )

        self.assertTrue(result)
        self.assertEqual(workflow.points, EditorStub.control_points)


@pytest.mark.integration
class TestPalettePreviewCoordinator(unittest.TestCase):
    def test_update_control_summary_sets_expected_text(self) -> None:
        from fractal_studio.application.coordinators.palette_preview_coordinator import (
            PalettePreviewCoordinator,
        )

        class FavoritesControllerStub:
            def update_palette_previews(self, **kwargs) -> None:
                pass

        class LabelStub:
            def __init__(self) -> None:
                self.text = ""

            def setText(self, text: str) -> None:
                self.text = text

        coordinator = PalettePreviewCoordinator(FavoritesControllerStub())
        label = LabelStub()

        coordinator.update_control_summary(label, [(1, 2, 3), (4, 5, 6)])

        self.assertEqual(label.text, "2 control points")

    def test_update_palette_previews_delegates_to_favorites_controller(self) -> None:
        from fractal_studio.application.coordinators.palette_preview_coordinator import (
            PalettePreviewCoordinator,
        )

        class FavoritesControllerStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def update_palette_previews(self, **kwargs) -> None:
                self.calls.append(kwargs)

        controller = FavoritesControllerStub()
        coordinator = PalettePreviewCoordinator(controller)
        marker = object()

        coordinator.update_palette_previews(
            palette=[(1, 2, 3)],
            editor=marker,
            backend=marker,
            legacy_palette_size=256,
            preview_palette=marker,
            preview_legacy=marker,
            palette_summary=marker,
        )

        self.assertEqual(len(controller.calls), 1)
        self.assertEqual(controller.calls[0]["palette"], [(1, 2, 3)])
        self.assertEqual(controller.calls[0]["legacy_palette_size"], 256)


@pytest.mark.integration
class TestPalettePreviewWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def test_paint_event_handles_empty_palette(self) -> None:
        from fractal_studio.editor import PalettePreviewWidget

        widget = PalettePreviewWidget("Preview")
        widget.resize(160, 100)
        widget.paintEvent(QPaintEvent(widget.rect()))

    def test_paint_event_draws_non_empty_palette(self) -> None:
        from fractal_studio.editor import PalettePreviewWidget

        widget = PalettePreviewWidget("Preview")
        widget.resize(160, 100)
        widget.set_palette([(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0)])
        widget.paintEvent(QPaintEvent(widget.rect()))


