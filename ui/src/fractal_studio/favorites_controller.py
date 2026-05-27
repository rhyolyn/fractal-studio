from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.state import FavoriteSnapshot, ParamsState
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class FavoritesController:
    def build_favorite_name(
        self,
        state,
        existing_names: set[str],
        now: Callable[[], datetime.datetime],
    ) -> str:
        timestamp = now().strftime("%Y-%m-%d %H:%M:%S")
        base_name = f"{state.formula} ({state.center_x:.3f}, {state.center_y:.3f}) {timestamp}"
        if base_name not in existing_names:
            return base_name

        suffix = 2
        while f"{base_name} ({suffix})" in existing_names:
            suffix += 1
        return f"{base_name} ({suffix})"

    def build_snapshot(
        self,
        viewport: FractalViewportWidget,
        aspect_ratio_mode: str,
        name: str,
        control_points: list[tuple[int, int, int]],
        thumbnail: str,
    ) -> FavoriteSnapshot:
        state = viewport.to_state()
        return FavoriteSnapshot(
            favorite_id=str(uuid.uuid4()),
            saved_at=datetime.datetime.now().isoformat(timespec="seconds"),
            aspect_ratio_mode=aspect_ratio_mode,
            name=name,
            viewport=state,
            control_points=[(int(p[0]), int(p[1]), int(p[2])) for p in control_points],
            palette=[(int(c[0]), int(c[1]), int(c[2])) for c in viewport.palette()],
            thumbnail=thumbnail,
        )

    def save_favorite(
        self,
        viewport: FractalViewportWidget,
        editor: ColorCubeEditor | None,
        aspect_ratio_mode: str,
        favorites: list[dict],
        build_name: Callable[[object], str],
        capture_thumbnail: Callable[[], str],
        add_favorite: Callable[[dict], None],
        add_row: Callable[[dict], None],
        persist: Callable[[], None],
        show_status: Callable[[str], None],
    ) -> FavoriteSnapshot:
        state = viewport.to_state()
        control_points = editor.control_points if editor is not None else []
        snapshot = self.build_snapshot(
            viewport=viewport,
            aspect_ratio_mode=aspect_ratio_mode,
            name=build_name(state),
            control_points=control_points,
            thumbnail=capture_thumbnail(),
        )
        favorite = snapshot.to_dict()
        add_favorite(favorite)
        add_row(favorite)
        persist()
        show_status(f"Saved favorite: {snapshot.name}")
        return snapshot

    def persist_favorites(
        self,
        favorites: list[dict],
        save_to_repo: Callable[[list[FavoriteSnapshot]], None],
    ) -> None:
        snapshots: list[FavoriteSnapshot] = []
        for favorite in favorites:
            if not isinstance(favorite, dict):
                continue
            try:
                snapshots.append(FavoriteSnapshot.from_dict(favorite))
            except (TypeError, ValueError):
                continue
        save_to_repo(snapshots)

    def load_favorites(
        self,
        load_from_repo: Callable[[], list[FavoriteSnapshot]],
    ) -> list[dict]:
        try:
            snapshots = load_from_repo()
            return [snapshot.to_dict() for snapshot in snapshots]
        except (TypeError, ValueError):
            return []

    def load_favorite_row(
        self,
        row,
        favorites: list[dict],
        rows: list,
        viewport: FractalViewportWidget | None,
        params_panel: FractalParamsPanel | None,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
        select_row: Callable[[object], None],
        show_status: Callable[[str], None],
    ) -> None:
        if viewport is None or params_panel is None:
            return
        idx = rows.index(row)
        favorite = favorites[idx]
        snapshot = FavoriteSnapshot.from_dict(favorite)
        self.restore_snapshot(
            snapshot=snapshot,
            viewport=viewport,
            params_panel=params_panel,
            editor=editor,
            preview_palette=preview_palette,
            apply_aspect_ratio_mode=apply_aspect_ratio_mode,
        )
        select_row(row)
        show_status(f"Restored: {snapshot.name}")

    def update_palette_previews(
        self,
        palette: list[tuple[int, int, int]],
        editor: ColorCubeEditor | None,
        backend,
        legacy_palette_size: int,
        preview_palette: PalettePreviewWidget | None,
        preview_legacy: PalettePreviewWidget | None,
        palette_summary,
    ) -> None:
        if preview_palette is None or preview_legacy is None or palette_summary is None:
            return

        preview_palette.set_palette(palette)
        legacy_palette = (
            backend.generate_palette(editor.control_points, legacy_palette_size)
            if editor is not None and len(editor.control_points) >= 4 and backend.available
            else []
        )
        preview_legacy.set_palette(legacy_palette)

        if palette:
            palette_summary.setText(
                f"Generated {len(palette)} internal colors and {len(legacy_palette)} legacy export colors."
            )
        else:
            palette_summary.setText("Add four control points to generate a palette.")

    def restore_snapshot(
        self,
        snapshot: FavoriteSnapshot,
        viewport: FractalViewportWidget,
        params_panel: FractalParamsPanel,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
    ) -> None:
        viewport.apply_state(snapshot.viewport, rerender=False)
        apply_aspect_ratio_mode(snapshot.aspect_ratio_mode)

        restored_points = snapshot.control_points
        if editor is not None and restored_points:
            # Restore editor state first; this also updates preview/viewport palette.
            editor.set_control_points(restored_points)

        if snapshot.palette and len(restored_points) < 4:
            # If control points are insufficient to regenerate a palette, restore exact saved colors.
            viewport.set_palette(snapshot.palette)
            if preview_palette is not None:
                preview_palette.set_palette(snapshot.palette)

        self.sync_params_panel(snapshot, params_panel)
        viewport.set_cycle_active(False)
        viewport.apply_state(snapshot.viewport, rerender=True)

    def sync_params_panel(self, snapshot: FavoriteSnapshot, params_panel: FractalParamsPanel) -> None:
        params_state = ParamsState.from_viewport_state(snapshot.viewport, cycle_active=False)
        params_panel.apply_state(params_state)
