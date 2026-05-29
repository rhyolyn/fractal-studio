from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from fractal_studio.backend import default_profile, load_backend_profile


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
    def test_validate_raises_when_collaborator_unbound(self) -> None:
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
        state.owner = None
        with self.assertRaises(RuntimeError) as ctx:
            state.validate()
        self.assertIn("owner", str(ctx.exception))


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


if __name__ == "__main__":
    unittest.main()
