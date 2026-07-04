from __future__ import annotations

import re
from pathlib import Path

import pytest

FORBIDDEN_ROOT_SHIM_MODULES = (
    "appearance_settings_dialog",
    "custom_resolution_dialog",
    "favorite_hover_presenter",
    "favorite_row_style_presenter",
    "favorite_thumbnail_row",
    "placeholder_panel",
    "settings_service",
    "export_service",
    "palette_service",
    "favorites_workflow_coordinator",
    "startup_coordinator",
    "theme_workflow_coordinator",
    "export_panel_coordinator",
    "favorites_panel_coordinator",
    "palette_panel_coordinator",
    "palette_preview_coordinator",
    "settings_dialog_coordinator",
    "sidebar_wiring_coordinator",
    "favorites_controller",
    "main_window_controller",
    "theme_controller",
    "editor_controller",
    "viewport_controller",
    "params_panel_controller",
    "main_window_sections",
    "main_window_sections_adapters",
    "main_window_sections_backend_adapter",
    "main_window_sections_base",
    "main_window_sections_colormap_adapter",
    "main_window_sections_export_adapter",
    "main_window_sections_favorites_adapter",
    "main_window_sections_mediator",
    "main_window_sections_palette_adapter",
    "main_window_sections_panel_state",
    "main_window_sections_ports",
    "main_window_sections_sidebar_adapter",
    "main_window_sections_state",
    "main_window_sections_viewport_adapter",
)

_FROM_IMPORT_PATTERN = re.compile(
    r"^\s*from\s+fractal_studio\.([a-zA-Z_][a-zA-Z0-9_]*)\s+import\b"
)
_IMPORT_PATTERN = re.compile(r"^\s*import\s+fractal_studio\.([a-zA-Z_][a-zA-Z0-9_]*)\b")
UI_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _scan_forbidden_imports(file_path: Path) -> list[tuple[int, str, str]]:
    violations: list[tuple[int, str, str]] = []
    lines = file_path.read_text(encoding="utf-8").splitlines()
    forbidden = set(FORBIDDEN_ROOT_SHIM_MODULES)

    for line_no, line in enumerate(lines, start=1):
        from_match = _FROM_IMPORT_PATTERN.match(line)
        if from_match is not None:
            module = from_match.group(1)
            if module in forbidden:
                violations.append((line_no, module, line.strip()))
            continue

        import_match = _IMPORT_PATTERN.match(line)
        if import_match is not None:
            module = import_match.group(1)
            if module in forbidden:
                violations.append((line_no, module, line.strip()))

    return violations


@pytest.mark.unit
def test_no_legacy_root_shim_imports_in_source_or_tests() -> None:
    src_root = UI_PACKAGE_ROOT / "src"
    tests_root = UI_PACKAGE_ROOT / "tests"

    scoped_files = _iter_python_files(src_root) + _iter_python_files(tests_root)
    assert scoped_files, (
        f"import-policy guard scanned zero files under {src_root} and {tests_root} — "
        "the directory layout changed; update this test's paths"
    )
    assert any(p.name == "main_window.py" for p in scoped_files), (
        "expected main_window.py in scan scope — paths look wrong"
    )
    all_violations: list[str] = []

    for file_path in scoped_files:
        for line_no, module, line in _scan_forbidden_imports(file_path):
            rel = file_path.relative_to(UI_PACKAGE_ROOT)
            all_violations.append(f"{rel}:{line_no}: {line} (legacy module: {module})")

    assert not all_violations, (
        "Legacy root-shim imports are disallowed. Use canonical package paths instead.\n"
        + "\n".join(all_violations)
    )


_SERVICES_ROOTS = ("services",)
_QT_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+PySide6\b"
)
_WIDGET_IMPORT_PATTERN = re.compile(
    r"^\s*from\s+fractal_studio\.ui\.widgets\b"
)


@pytest.mark.unit
def test_no_qt_imports_in_services() -> None:
    src_root = UI_PACKAGE_ROOT / "src" / "fractal_studio"

    violations: list[str] = []
    for layer in _SERVICES_ROOTS:
        layer_root = src_root / layer
        assert layer_root.exists(), f"expected service layer missing: {layer_root}"
        scoped_files = _iter_python_files(layer_root)
        assert scoped_files, (
            f"service import-policy guard scanned zero files under {layer_root} — "
            "the directory layout changed; update this test's paths"
        )
        for file_path in scoped_files:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for line_no, line in enumerate(lines, start=1):
                if _QT_IMPORT_PATTERN.match(line) or _WIDGET_IMPORT_PATTERN.match(line):
                    rel = file_path.relative_to(UI_PACKAGE_ROOT)
                    violations.append(f"{rel}:{line_no}: {line.strip()}")

    assert not violations, (
        "PySide6 and ui.widgets imports are forbidden in services/.\n"
        + "\n".join(violations)
    )
