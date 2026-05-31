from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

from fractal_studio.state import FavoriteSnapshot, ParamsState, ViewportState


class FavoritesController:
    def build_favorite_name(
        self,
        state: ViewportState,
        existing_names: set[str],
        now: Callable[[], datetime.datetime],
    ) -> str:
        timestamp = now().strftime("%Y-%m-%d %H:%M:%S")
        base_name = (
            f"{state.formula} ({state.center_x:.3f}, {state.center_y:.3f}) {timestamp}"
        )
        if base_name not in existing_names:
            return base_name
        suffix = 2
        while f"{base_name} ({suffix})" in existing_names:
            suffix += 1
        return f"{base_name} ({suffix})"

    def build_snapshot(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        control_points: list[tuple[int, int, int]],
        aspect_ratio_mode: str,
        name: str,
        thumbnail: str,
    ) -> FavoriteSnapshot:
        return FavoriteSnapshot(
            favorite_id=str(uuid.uuid4()),
            saved_at=datetime.datetime.now().isoformat(timespec="seconds"),
            aspect_ratio_mode=aspect_ratio_mode,
            name=name,
            viewport=viewport_state,
            control_points=[(int(p[0]), int(p[1]), int(p[2])) for p in control_points],
            palette=[(int(c[0]), int(c[1]), int(c[2])) for c in palette],
            thumbnail=thumbnail,
        )

    def save_favorite(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        control_points: list[tuple[int, int, int]],
        aspect_ratio_mode: str,
        favorites: list[FavoriteSnapshot],
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
        add_favorite: Callable[[FavoriteSnapshot], None],
        add_row: Callable[[FavoriteSnapshot], None],
        persist: Callable[[], None],
        show_status: Callable[[str], None],
    ) -> FavoriteSnapshot:
        snapshot = self.build_snapshot(
            viewport_state=viewport_state,
            palette=palette,
            control_points=control_points,
            aspect_ratio_mode=aspect_ratio_mode,
            name=build_name(viewport_state),
            thumbnail=capture_thumbnail(),
        )
        add_favorite(snapshot)
        add_row(snapshot)
        persist()
        show_status(f"Saved favorite: {snapshot.name}")
        return snapshot

    def persist_favorites(
        self,
        favorites: list[FavoriteSnapshot],
        save_to_repo: Callable[[list[FavoriteSnapshot]], None],
    ) -> None:
        save_to_repo(list(favorites))

    def load_favorites(
        self,
        load_from_repo: Callable[[], list[FavoriteSnapshot]],
    ) -> list[FavoriteSnapshot]:
        try:
            return list(load_from_repo())
        except (TypeError, ValueError):
            return []

    def load_favorite_row(
        self,
        row: object,
        favorites: list[FavoriteSnapshot],
        rows: list[object],
        restore_snapshot: Callable[[FavoriteSnapshot], None],
        select_row: Callable[[object], None],
        show_status: Callable[[str], None],
    ) -> None:
        idx = rows.index(row)
        snapshot = favorites[idx]
        restore_snapshot(snapshot)
        select_row(row)
        show_status(f"Restored: {snapshot.name}")

    def update_palette_previews(
        self,
        palette: list[tuple[int, int, int]],
        get_control_points: Callable[[], list[tuple[int, int, int]]],
        backend,
        legacy_palette_size: int,
        set_preview_palette: Callable[[list[tuple[int, int, int]]], None],
        set_legacy_palette: Callable[[list[tuple[int, int, int]]], None],
        set_summary_text: Callable[[str], None],
    ) -> None:
        set_preview_palette(palette)
        control_points = get_control_points()
        legacy_palette = (
            backend.generate_palette(control_points, legacy_palette_size)
            if len(control_points) >= 4
            else []
        )
        set_legacy_palette(legacy_palette)
        if palette:
            set_summary_text(
                f"Generated {len(palette)} internal colors and "
                f"{len(legacy_palette)} legacy export colors."
            )
        else:
            set_summary_text("Add four control points to generate a palette.")

    def restore_snapshot(
        self,
        snapshot: FavoriteSnapshot,
        apply_viewport_state: Callable[[ViewportState, bool], None],
        apply_control_points: Callable[[list[tuple[int, int, int]]], None],
        apply_palette: Callable[[list[tuple[int, int, int]]], None],
        apply_params: Callable[[ParamsState], None],
        set_cycle_active: Callable[[bool], None],
        apply_aspect_ratio_mode: Callable[[str], None],
    ) -> None:
        apply_viewport_state(snapshot.viewport, False)
        apply_aspect_ratio_mode(snapshot.aspect_ratio_mode)

        if snapshot.control_points:
            apply_control_points(snapshot.control_points)

        if snapshot.palette and len(snapshot.control_points) < 4:
            apply_palette(snapshot.palette)

        params_state = ParamsState.from_viewport_state(
            snapshot.viewport, cycle_active=False
        )
        apply_params(params_state)
        set_cycle_active(False)
        apply_viewport_state(snapshot.viewport, True)
