from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SETTINGS_SCHEMA_VERSION = 1
FAVORITES_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class UiSettings:
    theme: str = "light"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UiSettings:
        theme = raw.get("theme", "light") if isinstance(raw, dict) else "light"
        if not isinstance(theme, str):
            theme = "light"
        if theme not in {"light", "dark", "sepia"}:
            theme = "light"
        return cls(theme=theme)

    def to_dict(self) -> dict[str, str]:
        return {"theme": self.theme}


@dataclass(frozen=True)
class ViewportState:
    formula: str
    center_x: float
    center_y: float
    scale: float
    max_iterations: int
    is_julia: bool
    julia_real: float
    julia_imag: float
    power: int
    phoenix_real: float
    phoenix_imag: float
    coloring_mode: str
    trap_x: float
    trap_y: float
    palette_offset: float

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ViewportState:
        return cls(
            formula=str(raw.get("formula", "standard")),
            center_x=float(raw.get("center_x", -0.5)),
            center_y=float(raw.get("center_y", 0.0)),
            scale=float(raw.get("scale", 3.0)),
            max_iterations=int(raw.get("max_iterations", 256)),
            is_julia=bool(raw.get("is_julia", False)),
            julia_real=float(raw.get("julia_real", -0.8)),
            julia_imag=float(raw.get("julia_imag", 0.156)),
            power=int(raw.get("power", 3)),
            phoenix_real=float(raw.get("phoenix_real", 0.5)),
            phoenix_imag=float(raw.get("phoenix_imag", 0.0)),
            coloring_mode=str(raw.get("coloring_mode", "smooth_escape")),
            trap_x=float(raw.get("trap_x", 0.0)),
            trap_y=float(raw.get("trap_y", 0.0)),
            palette_offset=float(raw.get("palette_offset", 0.0)) % 1.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula": self.formula,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "scale": self.scale,
            "max_iterations": self.max_iterations,
            "is_julia": self.is_julia,
            "julia_real": self.julia_real,
            "julia_imag": self.julia_imag,
            "power": self.power,
            "phoenix_real": self.phoenix_real,
            "phoenix_imag": self.phoenix_imag,
            "coloring_mode": self.coloring_mode,
            "trap_x": self.trap_x,
            "trap_y": self.trap_y,
            "palette_offset": self.palette_offset,
        }


@dataclass(frozen=True)
class ParamsState:
    formula: str
    is_julia: bool
    power: int
    phoenix_real: float
    phoenix_imag: float
    julia_real: float
    julia_imag: float
    max_iterations: int
    scale: float
    coloring_mode: str
    trap_x: float
    trap_y: float
    cycle_active: bool = False
    cycle_speed: float = 10.0

    @classmethod
    def from_viewport_state(
        cls,
        viewport: ViewportState,
        *,
        cycle_active: bool = False,
        cycle_speed: float = 10.0,
    ) -> ParamsState:
        return cls(
            formula=viewport.formula,
            is_julia=viewport.is_julia,
            power=viewport.power,
            phoenix_real=viewport.phoenix_real,
            phoenix_imag=viewport.phoenix_imag,
            julia_real=viewport.julia_real,
            julia_imag=viewport.julia_imag,
            max_iterations=viewport.max_iterations,
            scale=viewport.scale,
            coloring_mode=viewport.coloring_mode,
            trap_x=viewport.trap_x,
            trap_y=viewport.trap_y,
            cycle_active=cycle_active,
            cycle_speed=cycle_speed,
        )

    def to_viewport_state(
        self,
        *,
        center_x: float = -0.5,
        center_y: float = 0.0,
        palette_offset: float = 0.0,
    ) -> ViewportState:
        return ViewportState(
            formula=self.formula,
            center_x=center_x,
            center_y=center_y,
            scale=self.scale,
            max_iterations=self.max_iterations,
            is_julia=self.is_julia,
            julia_real=self.julia_real,
            julia_imag=self.julia_imag,
            power=self.power,
            phoenix_real=self.phoenix_real,
            phoenix_imag=self.phoenix_imag,
            coloring_mode=self.coloring_mode,
            trap_x=self.trap_x,
            trap_y=self.trap_y,
            palette_offset=palette_offset,
        )


@dataclass(frozen=True)
class FavoriteSnapshot:
    favorite_id: str
    saved_at: str
    aspect_ratio_mode: str
    name: str
    viewport: ViewportState
    control_points: list[tuple[int, int, int]]
    palette: list[tuple[int, int, int]]
    thumbnail: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> FavoriteSnapshot:
        if not isinstance(raw, dict):
            raise ValueError("Favorite data must be a dictionary")

        return cls(
            favorite_id=str(raw.get("id", "")),
            saved_at=str(raw.get("saved_at", "")),
            aspect_ratio_mode=str(raw.get("aspect_ratio_mode", "square")),
            name=str(raw.get("name", "Unnamed")),
            viewport=ViewportState.from_dict(raw),
            control_points=_coerce_rgb_triplets(raw.get("control_points")),
            palette=_coerce_rgb_triplets(raw.get("palette")),
            thumbnail=str(raw.get("thumbnail", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.favorite_id,
            "saved_at": self.saved_at,
            "aspect_ratio_mode": self.aspect_ratio_mode,
            "name": self.name,
            "control_points": [list(p) for p in self.control_points],
            "palette": [list(c) for c in self.palette],
            "thumbnail": self.thumbnail,
        }
        data.update(self.viewport.to_dict())
        return data


def _coerce_rgb_triplets(value: Any) -> list[tuple[int, int, int]]:
    if not isinstance(value, list):
        return []

    normalized: list[tuple[int, int, int]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            continue
        try:
            normalized.append((int(item[0]), int(item[1]), int(item[2])))
        except (TypeError, ValueError):
            continue
    return normalized


def serialize_settings_payload(settings: UiSettings) -> dict[str, Any]:
    return {
        "version": SETTINGS_SCHEMA_VERSION,
        "data": settings.to_dict(),
    }


def deserialize_settings_payload(raw: Any) -> UiSettings:
    if isinstance(raw, dict):
        if isinstance(raw.get("data"), dict):
            return UiSettings.from_dict(raw["data"])
        return UiSettings.from_dict(raw)
    return UiSettings()


def serialize_favorites_payload(favorites: list[FavoriteSnapshot]) -> dict[str, Any]:
    return {
        "version": FAVORITES_SCHEMA_VERSION,
        "favorites": [fav.to_dict() for fav in favorites],
    }


def deserialize_favorites_payload(raw: Any) -> list[FavoriteSnapshot]:
    records: list[Any] = []
    if isinstance(raw, list):
        # Legacy unversioned format.
        records = raw
    elif isinstance(raw, dict):
        payload = raw.get("favorites")
        if isinstance(payload, list):
            records = payload

    snapshots: list[FavoriteSnapshot] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            snapshots.append(FavoriteSnapshot.from_dict(record))
        except (TypeError, ValueError):
            continue
    return snapshots
