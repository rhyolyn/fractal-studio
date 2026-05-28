from __future__ import annotations

collect_ignore_glob: list[str] = []

try:
    import PySide6  # noqa: F401
except ModuleNotFoundError:
    collect_ignore_glob = [
        "tests/test_ui_redesign.py",
        "tests/test_package_layout_smoke.py",
        "tests/test_main_window_section_panel_states.py",
    ]
