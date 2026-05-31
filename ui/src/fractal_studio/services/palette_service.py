from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fractal_studio.backend import CoreBackend


class PaletteWorkflowService:
    def save_palette_json(
        self,
        path: Path | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if path is None:
            return False
        backend.export_palette_json(str(path), control_points, palette_size)
        set_status(f"Saved palette to {path}")
        return True

    def load_palette_json(
        self,
        path: Path | None,
        backend: CoreBackend,
        set_control_points: Callable[[list[tuple[int, int, int]]], None],
        set_status: Callable[[str], None],
    ) -> bool:
        if path is None:
            return False
        palette_size, control_points = backend.import_palette_json(str(path))
        if not control_points:
            return False
        set_control_points(control_points)
        set_status(
            f"Loaded palette with {len(control_points)} control points. "
            f"Saved palette size was {palette_size}."
        )
        return True

    def export_legacy_map(
        self,
        path: Path | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        legacy_palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if path is None or len(control_points) < 4:
            set_status("Add at least four control points before exporting a legacy map.")
            return False
        palette = backend.generate_palette(control_points, legacy_palette_size)
        if not palette:
            return False
        backend.export_legacy_map(str(path), palette)
        set_status(f"Exported legacy palette to {path}")
        return True
