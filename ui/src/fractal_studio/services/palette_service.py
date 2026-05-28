from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from fractal_studio.backend import CoreBackend


class PaletteWorkflowService:
    def save_palette_json(
        self,
        parent: QWidget | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        palette_size: int,
        set_status: Callable[[str], None],
        get_save_file_name: Callable[
            ..., tuple[str, str]
        ] = QFileDialog.getSaveFileName,
    ) -> bool:
        if not backend.available:
            return False

        path, _ = get_save_file_name(
            parent,
            "Save palette",
            str(Path.cwd() / "palette.json"),
            "Fractal Studio Palette (*.json)",
        )
        if not path:
            return False

        backend.export_palette_json(path, control_points, palette_size)
        set_status(f"Saved palette to {path}")
        return True

    def load_palette_json(
        self,
        parent: QWidget | None,
        backend: CoreBackend,
        set_control_points: Callable[[list[tuple[int, int, int]]], None],
        set_status: Callable[[str], None],
        get_open_file_name: Callable[
            ..., tuple[str, str]
        ] = QFileDialog.getOpenFileName,
    ) -> bool:
        if not backend.available:
            return False

        path, _ = get_open_file_name(
            parent,
            "Load palette",
            str(Path.cwd()),
            "Fractal Studio Palette (*.json)",
        )
        if not path:
            return False

        palette_size, control_points = backend.import_palette_json(path)
        set_control_points(control_points)
        set_status(
            f"Loaded palette with {len(control_points)} control points. Saved palette size was {palette_size}."
        )
        return True

    def export_legacy_map(
        self,
        parent: QWidget | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        legacy_palette_size: int,
        set_status: Callable[[str], None],
        get_save_file_name: Callable[
            ..., tuple[str, str]
        ] = QFileDialog.getSaveFileName,
    ) -> bool:
        if not backend.available or len(control_points) < 4:
            set_status(
                "Add at least four control points before exporting a legacy map."
            )
            return False

        path, _ = get_save_file_name(
            parent,
            "Export legacy palette",
            str(Path.cwd() / "palette.map"),
            "Legacy Palette (*.map)",
        )
        if not path:
            return False

        palette = backend.generate_palette(control_points, legacy_palette_size)
        backend.export_legacy_map(path, palette)
        set_status(f"Exported legacy palette to {path}")
        return True
