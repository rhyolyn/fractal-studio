from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SETTINGS_SCHEMA_VERSION = 1
FAVORITES_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class UiSettings:
    theme: str = "light"
    sidebar_collapsed: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UiSettings:
        theme = raw.get("theme", "light") if isinstance(raw, dict) else "light"
        if not isinstance(theme, str):
            theme = "light"
        if theme not in {"light", "dark", "sepia"}:
            theme = "light"
        sidebar_collapsed: dict[str, bool] = {}
        if isinstance(raw, dict):
            sc = raw.get("sidebar_collapsed")
            if isinstance(sc, dict):
                sidebar_collapsed = {
                    k: bool(v) for k, v in sc.items() if isinstance(k, str)
                }
        return cls(theme=theme, sidebar_collapsed=sidebar_collapsed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "sidebar_collapsed": dict(self.sidebar_collapsed),
        }


@dataclass(frozen=True)
class StandardParams:
    pass


@dataclass(frozen=True)
class JuliaParams:
    cx: float = -0.8
    cy: float = 0.156


@dataclass(frozen=True)
class PhoenixParams:
    real: float = 0.5
    imag: float = 0.0


@dataclass(frozen=True)
class NewtonParams:
    trap_x: float = 0.0
    trap_y: float = 0.0


FormulaParams = StandardParams | JuliaParams | PhoenixParams | NewtonParams


@dataclass(frozen=True)
class ViewportState:
    formula: str
    center_x: float
    center_y: float
    scale: float
    max_iterations: int
    is_julia: bool
    formula_params: FormulaParams
    coloring_mode: str
    palette_offset: float
    power: int = 3

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ViewportState:
        formula = str(raw.get("formula", "standard"))

        if "formula_params" in raw:
            fp_raw = raw["formula_params"]
            fp_type = fp_raw.get("type", "standard")
            if fp_type == "julia":
                formula_params: FormulaParams = JuliaParams(
                    cx=float(fp_raw.get("cx", -0.8)),
                    cy=float(fp_raw.get("cy", 0.156)),
                )
            elif fp_type == "phoenix":
                formula_params = PhoenixParams(
                    real=float(fp_raw.get("real", 0.5)),
                    imag=float(fp_raw.get("imag", 0.0)),
                )
            elif fp_type == "newton":
                formula_params = NewtonParams(
                    trap_x=float(fp_raw.get("trap_x", 0.0)),
                    trap_y=float(fp_raw.get("trap_y", 0.0)),
                )
            else:
                formula_params = StandardParams()
        else:
            # Legacy flat format
            is_julia = bool(raw.get("is_julia", False))
            if formula == "phoenix":
                formula_params = PhoenixParams(
                    real=float(raw.get("phoenix_real", 0.5)),
                    imag=float(raw.get("phoenix_imag", 0.0)),
                )
            elif formula == "newton":
                formula_params = NewtonParams(
                    trap_x=float(raw.get("trap_x", 0.0)),
                    trap_y=float(raw.get("trap_y", 0.0)),
                )
            elif is_julia or formula == "julia":
                formula_params = JuliaParams(
                    cx=float(raw.get("julia_real", -0.8)),
                    cy=float(raw.get("julia_imag", 0.156)),
                )
            else:
                formula_params = StandardParams()

        return cls(
            formula=formula,
            center_x=float(raw.get("center_x", -0.5)),
            center_y=float(raw.get("center_y", 0.0)),
            scale=max(1e-12, float(raw.get("scale", 3.0))),
            max_iterations=max(1, int(raw.get("max_iterations", 256))),
            is_julia=bool(raw.get("is_julia", False)),
            formula_params=formula_params,
            coloring_mode=str(raw.get("coloring_mode", "smooth_escape")),
            palette_offset=float(raw.get("palette_offset", 0.0)) % 1.0,
            power=max(2, int(raw.get("power", 3))),
        )

    def to_render_kwargs(self) -> dict[str, float]:
        fp = self.formula_params
        return {
            "julia_real": fp.cx if isinstance(fp, JuliaParams) else 0.0,
            "julia_imag": fp.cy if isinstance(fp, JuliaParams) else 0.0,
            "phoenix_real": fp.real if isinstance(fp, PhoenixParams) else 0.0,
            "phoenix_imag": fp.imag if isinstance(fp, PhoenixParams) else 0.0,
            "trap_x": fp.trap_x if isinstance(fp, NewtonParams) else 0.0,
            "trap_y": fp.trap_y if isinstance(fp, NewtonParams) else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        fp = self.formula_params
        if isinstance(fp, JuliaParams):
            fp_dict: dict[str, Any] = {"type": "julia", "cx": fp.cx, "cy": fp.cy}
        elif isinstance(fp, PhoenixParams):
            fp_dict = {"type": "phoenix", "real": fp.real, "imag": fp.imag}
        elif isinstance(fp, NewtonParams):
            fp_dict = {"type": "newton", "trap_x": fp.trap_x, "trap_y": fp.trap_y}
        else:
            fp_dict = {"type": "standard"}

        return {
            "formula": self.formula,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "scale": self.scale,
            "max_iterations": self.max_iterations,
            "is_julia": self.is_julia,
            "formula_params": fp_dict,
            "coloring_mode": self.coloring_mode,
            "palette_offset": self.palette_offset,
            "power": self.power,
        }


@dataclass(frozen=True)
class RenderRequest:
    generation: int
    viewport_state: ViewportState
    palette: tuple[tuple[int, int, int], ...]
    width: int
    height: int


@dataclass(frozen=True)
class ParamsState:
    formula: str
    is_julia: bool
    power: int
    formula_params: FormulaParams
    max_iterations: int
    scale: float
    coloring_mode: str
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
            formula_params=viewport.formula_params,
            max_iterations=viewport.max_iterations,
            scale=viewport.scale,
            coloring_mode=viewport.coloring_mode,
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
            formula_params=self.formula_params,
            coloring_mode=self.coloring_mode,
            palette_offset=palette_offset,
            power=self.power,
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
