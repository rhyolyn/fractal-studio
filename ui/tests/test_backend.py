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


if __name__ == "__main__":
    unittest.main()
