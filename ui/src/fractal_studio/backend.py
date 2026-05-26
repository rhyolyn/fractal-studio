from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType

Color = tuple[int, int, int]


@dataclass(frozen=True)
class BackendProfile:
    palette_size: int
    legacy_palette_size: int
    coloring_model: str
    render_strategy: str
    preview_width: int
    preview_height: int
    supersampling_enabled: bool
    export_presets: tuple[str, ...]


def default_profile() -> BackendProfile:
    return BackendProfile(
        palette_size=2048,
        legacy_palette_size=256,
        coloring_model="smooth_escape",
        render_strategy="multithreaded_cpu",
        preview_width=1280,
        preview_height=720,
        supersampling_enabled=True,
        export_presets=("2K", "4K", "8K", "Tiled"),
    )


class CoreBackend:
    def __init__(self, module: ModuleType | None) -> None:
        self._module = module

    @property
    def available(self) -> bool:
        return self._module is not None

    def profile(self) -> BackendProfile:
        if self._module is None:
            return default_profile()

        width, height = self._module.default_preview_size()
        return BackendProfile(
            palette_size=self._module.recommended_palette_size(),
            legacy_palette_size=self._module.legacy_palette_size(),
            coloring_model=self._module.coloring_model(),
            render_strategy=self._module.render_strategy(),
            preview_width=width,
            preview_height=height,
            supersampling_enabled=self._module.supports_supersampling(),
            export_presets=tuple(self._module.export_presets()),
        )

    def color_from_face(self, face: int, position: tuple[float, float]) -> Color:
        return self._require().color_from_face(face, position)

    def project_color_to_face(self, face: int, color: Color) -> tuple[float, float]:
        return self._require().project_color_to_face(face, color)

    def update_control_point_from_face(
        self,
        face: int,
        color: Color,
        position: tuple[float, float],
    ) -> Color:
        return self._require().update_control_point_from_face(face, color, position)

    def generate_palette(self, control_points: list[Color], palette_size: int) -> list[Color]:
        return list(self._require().generate_palette(control_points, palette_size))

    def render_fractal(
        self,
        formula: str,
        width: int,
        height: int,
        *,
        is_julia: bool = False,
        julia_real: float = 0.0,
        julia_imag: float = 0.0,
        power: int = 2,
        phoenix_real: float = 0.5,
        phoenix_imag: float = 0.0,
        center_x: float = -0.5,
        center_y: float = 0.0,
        scale: float = 3.0,
        max_iterations: int = 512,
        palette: list[Color] | None = None,
        coloring_mode: str = "smooth_escape",
        trap_x: float = 0.0,
        trap_y: float = 0.0,
        palette_offset: float = 0.0,
    ) -> bytes:
        return bytes(
            self._require().render_fractal(
                formula, width, height,
                center_x=center_x,
                center_y=center_y,
                scale=scale,
                max_iterations=max_iterations,
                power=power,
                julia_real=julia_real,
                julia_imag=julia_imag,
                is_julia=is_julia,
                phoenix_real=phoenix_real,
                phoenix_imag=phoenix_imag,
                palette=palette or [],
                coloring_mode=coloring_mode,
                trap_x=trap_x,
                trap_y=trap_y,
                palette_offset=palette_offset,
            )
        )

    def render_mandelbrot(
        self,
        width: int,
        height: int,
        center_x: float,
        center_y: float,
        scale: float,
        max_iterations: int,
        palette: list[Color],
    ) -> bytes:
        return bytes(
            self._require().render_mandelbrot(
                width,
                height,
                center_x,
                center_y,
                scale,
                max_iterations,
                palette,
            )
        )

    def render_julia(
        self,
        width: int,
        height: int,
        constant_real: float,
        constant_imaginary: float,
        center_x: float,
        center_y: float,
        scale: float,
        max_iterations: int,
        palette: list[Color],
    ) -> bytes:
        return bytes(
            self._require().render_julia(
                width,
                height,
                constant_real,
                constant_imaginary,
                center_x,
                center_y,
                scale,
                max_iterations,
                palette,
            )
        )

    def export_legacy_map(self, path: str, palette: list[Color]) -> None:
        self._require().export_legacy_map(path, palette)

    def export_palette_json(
        self,
        path: str,
        control_points: list[Color],
        palette_size: int,
    ) -> None:
        self._require().export_palette_json(path, control_points, palette_size)

    def import_palette_json(self, path: str) -> tuple[int, list[Color]]:
        palette_size, control_points = self._require().import_palette_json(path)
        return palette_size, list(control_points)

    def _require(self) -> ModuleType:
        if self._module is None:
            raise RuntimeError("Rust backend is not available. Build fractal_core before using the editor.")
        return self._module


def load_backend() -> CoreBackend:
    try:
        return CoreBackend(import_module("fractal_core"))
    except ModuleNotFoundError:
        return CoreBackend(None)


def load_backend_profile() -> tuple[BackendProfile, bool]:
    backend = load_backend()
    return backend.profile(), backend.available
