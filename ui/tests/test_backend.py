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


if __name__ == "__main__":
    unittest.main()
