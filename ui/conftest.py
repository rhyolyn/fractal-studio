from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SOURCE_ROOT))

collect_ignore_glob: list[str] = []

try:
    import PySide6  # noqa: F401
except ModuleNotFoundError:
    collect_ignore_glob = [
        "tests/test_color_editor.py",
        "tests/test_colormap_panel_state.py",
        "tests/test_colormap_panel_wiring.py",
        "tests/test_export_panel.py",
        "tests/test_favorites_controllers.py",
        "tests/test_favorites_widgets.py",
        "tests/test_main_window_shell.py",
        "tests/test_package_layout_smoke.py",
        "tests/test_palette_workflows.py",
        "tests/test_params_panel.py",
        "tests/test_section_panel.py",
        "tests/test_main_window_section_panel_states.py",
        "tests/test_settings_and_theme.py",
        "tests/test_startup_smoke.py",
        "tests/test_viewport_widget.py",
    ]
