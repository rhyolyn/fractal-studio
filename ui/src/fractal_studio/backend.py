from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType

from fractal_studio.state import RenderRequest

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


@dataclass(frozen=True)
class BackendCapabilities:
    can_render: bool
    can_generate_palette: bool
    can_import_palette: bool
    can_export_palette: bool


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

    @property
    def capabilities(self) -> BackendCapabilities:
        available = self._module is not None
        return BackendCapabilities(
            can_render=available,
            can_generate_palette=available,
            can_import_palette=available,
            can_export_palette=available,
        )

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
        if self._module is None:
            return (0, 0, 0)
        return self._module.color_from_face(face, position)

    def project_color_to_face(self, face: int, color: Color) -> tuple[float, float]:
        if self._module is None:
            return (0.0, 0.0)
        return self._module.project_color_to_face(face, color)

    def update_control_point_from_face(
        self,
        face: int,
        color: Color,
        position: tuple[float, float],
    ) -> Color:
        if self._module is None:
            return color
        return self._module.update_control_point_from_face(face, color, position)

    def generate_palette(
        self, control_points: list[Color], palette_size: int
    ) -> list[Color]:
        if self._module is None:
            return []
        return list(self._module.generate_palette(control_points, palette_size))

    def render(self, request: RenderRequest) -> bytes:
        state = request.viewport_state
        kwargs = state.to_render_kwargs()
        return self.render_fractal(
            state.formula,
            request.width,
            request.height,
            is_julia=state.is_julia,
            julia_real=kwargs["julia_real"],
            julia_imag=kwargs["julia_imag"],
            power=state.power,
            phoenix_real=kwargs["phoenix_real"],
            phoenix_imag=kwargs["phoenix_imag"],
            center_x=state.center_x,
            center_y=state.center_y,
            scale=state.scale,
            max_iterations=state.max_iterations,
            palette=list(request.palette),
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=state.palette_offset,
        )

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
        if self._module is None:
            return b""
        return bytes(
            self._module.render_fractal(
                formula, width, height,
                center_x=center_x, center_y=center_y, scale=scale,
                max_iterations=max_iterations, power=power,
                julia_real=julia_real, julia_imag=julia_imag, is_julia=is_julia,
                phoenix_real=phoenix_real, phoenix_imag=phoenix_imag,
                palette=palette or [], coloring_mode=coloring_mode,
                trap_x=trap_x, trap_y=trap_y, palette_offset=palette_offset,
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
        if self._module is None:
            return b""
        return bytes(
            self._module.render_mandelbrot(
                width, height, center_x, center_y, scale, max_iterations, palette
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
        if self._module is None:
            return b""
        return bytes(
            self._module.render_julia(
                width, height, constant_real, constant_imaginary,
                center_x, center_y, scale, max_iterations, palette,
            )
        )

    def export_legacy_map(self, path: str, palette: list[Color]) -> None:
        if self._module is None:
            return
        self._module.export_legacy_map(path, palette)

    def export_palette_json(
        self,
        path: str,
        control_points: list[Color],
        palette_size: int,
    ) -> None:
        if self._module is None:
            return
        self._module.export_palette_json(path, control_points, palette_size)

    def import_palette_json(self, path: str) -> tuple[int, list[Color]]:
        if self._module is None:
            return (0, [])
        palette_size, control_points = self._module.import_palette_json(path)
        return palette_size, list(control_points)


def load_backend() -> CoreBackend:
    try:
        return CoreBackend(import_module("fractal_core"))
    except ModuleNotFoundError:
        return CoreBackend(None)


def load_backend_profile() -> tuple[BackendProfile, bool]:
    backend = load_backend()
    return backend.profile(), backend.available
