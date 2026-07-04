from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from fractal_studio.backend import CoreBackend, default_profile, load_backend_profile


@pytest.mark.unit
class BackendProfileTests(unittest.TestCase):
    def test_default_profile_uses_modernized_defaults(self) -> None:
        profile = default_profile()
        self.assertEqual(profile.palette_size, 2048)
        self.assertEqual(profile.legacy_palette_size, 256)
        self.assertEqual(profile.coloring_model, "smooth_escape")
        self.assertEqual(profile.render_strategy, "multithreaded_cpu")
        self.assertTrue(profile.supersampling_enabled)

    def test_loader_falls_back_when_rust_extension_is_missing(self) -> None:
        with patch(
            "fractal_studio.backend.import_module", side_effect=ModuleNotFoundError
        ):
            profile, backend_loaded = load_backend_profile()
        self.assertFalse(backend_loaded)
        self.assertEqual(profile, default_profile())


def _ensure_pyside6_mocked() -> None:
    """Insert lightweight stubs so Qt-heavy modules can be imported without PySide6."""
    from types import ModuleType
    from unittest.mock import MagicMock

    pyside6_submodules = [
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ]
    for name in pyside6_submodules:
        if name not in sys.modules:
            sys.modules[name] = MagicMock()


@pytest.mark.unit
class ValidateTest(unittest.TestCase):
    def test_validate_raises_when_panel_state_is_none(self) -> None:
        _ensure_pyside6_mocked()
        # Re-import after mocking; evict any cached partially-imported modules.
        for key in list(sys.modules):
            if key.startswith("fractal_studio.ui.sections") or key in (
                "fractal_studio.viewport",
                "fractal_studio.editor",
            ):
                del sys.modules[key]
        from fractal_studio.ui.sections.state import MainWindowSectionsState
        state = MainWindowSectionsState.__new__(MainWindowSectionsState)
        # Set all panel-state fields to None to simulate an uninitialised instance.
        state.viewport = None
        state.sidebar = None
        state.palette = None
        state.colormap = None
        state.favorites = None
        state.export = None
        with self.assertRaises(RuntimeError) as ctx:
            state.validate()
        self.assertIn("viewport", str(ctx.exception))


@pytest.mark.unit
class ViewportStateFormulaParamsTests(unittest.TestCase):
    def test_julia_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, JuliaParams
        original = ViewportState(
            formula="standard",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=True,
            formula_params=JuliaParams(cx=-0.8, cy=0.156),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertEqual(restored.formula_params, original.formula_params)

    def test_phoenix_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, PhoenixParams
        original = ViewportState(
            formula="phoenix",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=False,
            formula_params=PhoenixParams(real=0.5, imag=0.0),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertEqual(restored.formula_params, original.formula_params)

    def test_newton_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, NewtonParams
        original = ViewportState(
            formula="newton",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=False,
            formula_params=NewtonParams(trap_x=0.3, trap_y=-0.1),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertEqual(restored.formula_params, original.formula_params)

    def test_standard_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, StandardParams
        original = ViewportState(
            formula="standard",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=False,
            formula_params=StandardParams(),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertIsInstance(restored.formula_params, StandardParams)

    def test_legacy_flat_format_phoenix_loads_correctly(self) -> None:
        from fractal_studio.state import ViewportState, PhoenixParams
        legacy = {
            "formula": "phoenix", "center_x": 0.0, "center_y": 0.0,
            "scale": 3.0, "max_iterations": 256, "is_julia": False,
            "phoenix_real": 0.5, "phoenix_imag": 0.1,
            "coloring_mode": "smooth_escape",
            "palette_offset": 0.0,
        }
        state = ViewportState.from_dict(legacy)
        self.assertIsInstance(state.formula_params, PhoenixParams)
        self.assertAlmostEqual(state.formula_params.real, 0.5)
        self.assertAlmostEqual(state.formula_params.imag, 0.1)

    def test_legacy_flat_format_newton_loads_correctly(self) -> None:
        from fractal_studio.state import ViewportState, NewtonParams
        legacy = {
            "formula": "newton", "center_x": 0.0, "center_y": 0.0,
            "scale": 3.0, "max_iterations": 256, "is_julia": False,
            "trap_x": 0.3, "trap_y": -0.1,
            "coloring_mode": "smooth_escape",
            "palette_offset": 0.0,
        }
        state = ViewportState.from_dict(legacy)
        self.assertIsInstance(state.formula_params, NewtonParams)
        self.assertAlmostEqual(state.formula_params.trap_x, 0.3)
        self.assertAlmostEqual(state.formula_params.trap_y, -0.1)

    def test_legacy_flat_format_loads_correctly(self) -> None:
        from fractal_studio.state import ViewportState, JuliaParams
        legacy = {
            "formula": "standard", "center_x": 0.0, "center_y": 0.0,
            "scale": 3.0, "max_iterations": 256, "is_julia": True,
            "julia_real": -0.8, "julia_imag": 0.156,
            "phoenix_real": 0.5, "phoenix_imag": 0.0,
            "coloring_mode": "smooth_escape",
            "trap_x": 0.0, "trap_y": 0.0, "palette_offset": 0.0,
            "power": 3,
        }
        state = ViewportState.from_dict(legacy)
        self.assertIsInstance(state.formula_params, JuliaParams)
        self.assertAlmostEqual(state.formula_params.cx, -0.8)


@pytest.mark.unit
def test_capabilities_all_false_when_no_module() -> None:
    backend = CoreBackend(None)
    caps = backend.capabilities
    assert caps.can_render is False
    assert caps.can_generate_palette is False
    assert caps.can_import_palette is False
    assert caps.can_export_palette is False


@pytest.mark.unit
def test_capabilities_is_frozen() -> None:
    from fractal_studio.backend import BackendCapabilities
    caps = BackendCapabilities(
        can_render=True,
        can_generate_palette=True,
        can_import_palette=True,
        can_export_palette=True,
    )
    import dataclasses
    assert dataclasses.is_dataclass(caps)
    with pytest.raises(Exception):
        caps.can_render = False  # type: ignore[misc]


@pytest.mark.unit
def test_generate_palette_returns_empty_list_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.generate_palette([(0, 0, 0), (255, 255, 255)], 256)
    assert result == []


@pytest.mark.unit
def test_color_from_face_returns_black_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.color_from_face(0, (0.5, 0.5))
    assert result == (0, 0, 0)


@pytest.mark.unit
def test_render_fractal_returns_empty_bytes_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.render_fractal("standard", 4, 4)
    assert isinstance(result, bytes)
    assert len(result) == 0


@pytest.mark.unit
def test_import_palette_json_returns_empty_when_no_module() -> None:
    backend = CoreBackend(None)
    size, points = backend.import_palette_json("fake.json")
    assert size == 0
    assert points == []


@pytest.mark.unit
def test_available_property_false_when_no_module() -> None:
    backend = CoreBackend(None)
    assert backend.available is False


class RecordingRenderModule:
    """Stands in for the fractal_core module; records render_fractal kwargs."""

    def __init__(self) -> None:
        self.args: tuple | None = None
        self.kwargs: dict | None = None

    def render_fractal(self, *args, **kwargs) -> bytes:
        self.args = args
        self.kwargs = kwargs
        return b"\x01\x02\x03\x04"


@pytest.mark.unit
def test_backend_render_unpacks_request_fields() -> None:
    from fractal_studio.state import JuliaParams, RenderRequest, ViewportState

    module = RecordingRenderModule()
    backend = CoreBackend(module)
    state = ViewportState(
        formula="standard",
        center_x=-0.5,
        center_y=0.25,
        scale=1.5,
        max_iterations=333,
        is_julia=True,
        formula_params=JuliaParams(cx=-0.7, cy=0.2),
        coloring_mode="orbit_trap_circle",
        palette_offset=0.125,
        power=4,
    )
    request = RenderRequest(
        generation=7,
        viewport_state=state,
        palette=((1, 2, 3), (4, 5, 6)),
        width=64,
        height=48,
    )

    raw = backend.render(request)

    assert raw == b"\x01\x02\x03\x04"
    assert module.args == ("standard", 64, 48)
    assert module.kwargs is not None
    assert module.kwargs["is_julia"] is True
    assert module.kwargs["julia_real"] == -0.7
    assert module.kwargs["julia_imag"] == 0.2
    assert module.kwargs["power"] == 4
    assert module.kwargs["center_x"] == -0.5
    assert module.kwargs["center_y"] == 0.25
    assert module.kwargs["scale"] == 1.5
    assert module.kwargs["max_iterations"] == 333
    assert module.kwargs["palette"] == [(1, 2, 3), (4, 5, 6)]
    assert module.kwargs["coloring_mode"] == "orbit_trap_circle"
    assert module.kwargs["palette_offset"] == 0.125


@pytest.mark.unit
def test_backend_render_returns_empty_without_module() -> None:
    from fractal_studio.state import RenderRequest, StandardParams, ViewportState

    state = ViewportState(
        formula="standard", center_x=-0.5, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    request = RenderRequest(generation=1, viewport_state=state, palette=(), width=8, height=8)
    assert CoreBackend(None).render(request) == b""


if __name__ == "__main__":
    unittest.main()
