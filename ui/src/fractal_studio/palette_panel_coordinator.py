from __future__ import annotations

from collections.abc import Callable

from fractal_studio.editor import ColorCubeEditor
from fractal_studio.palette_service import PaletteWorkflowService


class PalettePanelCoordinator:
    def __init__(self, workflow_service: PaletteWorkflowService) -> None:
        self._workflow_service = workflow_service

    def save_palette_json(
        self,
        *,
        parent,
        editor: ColorCubeEditor | None,
        backend,
        palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if editor is None:
            return False
        return self._workflow_service.save_palette_json(
            parent=parent,
            backend=backend,
            control_points=editor.control_points,
            palette_size=palette_size,
            set_status=set_status,
        )

    def load_palette_json(
        self,
        *,
        parent,
        editor: ColorCubeEditor | None,
        backend,
        set_status: Callable[[str], None],
    ) -> bool:
        if editor is None:
            return False
        return self._workflow_service.load_palette_json(
            parent=parent,
            backend=backend,
            set_control_points=editor.set_control_points,
            set_status=set_status,
        )

    def export_legacy_map(
        self,
        *,
        parent,
        editor: ColorCubeEditor | None,
        backend,
        legacy_palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if editor is None:
            return False
        return self._workflow_service.export_legacy_map(
            parent=parent,
            backend=backend,
            control_points=editor.control_points,
            legacy_palette_size=legacy_palette_size,
            set_status=set_status,
        )
