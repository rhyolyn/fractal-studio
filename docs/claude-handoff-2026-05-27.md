# Handoff for Claude

## Live checkpoint (update this first each step)
- Date: 2026-05-27
- Current pause point: Directory reorganization and sections naming polish are complete (main_window_sections_* module prefixes removed).
- Last verified command: `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest c:/git/graphics/fractal-studio/ui/tests`
- Last verified result: 131 passed
- Immediate next action: optional workflow class naming polish or CI lint wiring.
- If handoff now: continue from "Recommended next slice" step 1.

## Objective and current state
- UI package reorganization is complete.
- Canonical package paths are now in place for dialogs/widgets/presenters, services, workflows, coordinators, application controllers, and widget-facing UI controllers.
- Full test suite was green at last verification: 131 passed.
- No active architecture deficiencies remain in the reviewed UI reorganization scope.

## What was completed
1. New organized package structure introduced:
- `ui/src/fractal_studio/ui/dialogs`
- `ui/src/fractal_studio/ui/widgets`
- `ui/src/fractal_studio/ui/presenters`
- `ui/src/fractal_studio/services`
- `ui/src/fractal_studio/application/workflows`

11. Main-window sections package boundary introduced:
- `ui/src/fractal_studio/ui/sections/sections.py`
- `ui/src/fractal_studio/ui/sections/adapters.py`
- `ui/src/fractal_studio/ui/sections/backend_adapter.py`
- `ui/src/fractal_studio/ui/sections/base.py`
- `ui/src/fractal_studio/ui/sections/colormap_adapter.py`
- `ui/src/fractal_studio/ui/sections/export_adapter.py`
- `ui/src/fractal_studio/ui/sections/favorites_adapter.py`
- `ui/src/fractal_studio/ui/sections/mediator.py`
- `ui/src/fractal_studio/ui/sections/palette_adapter.py`
- `ui/src/fractal_studio/ui/sections/panel_state.py`
- `ui/src/fractal_studio/ui/sections/ports.py`
- `ui/src/fractal_studio/ui/sections/sidebar_adapter.py`
- `ui/src/fractal_studio/ui/sections/state.py`
- `ui/src/fractal_studio/ui/sections/viewport_adapter.py`
- `ui/src/fractal_studio/ui/sections/__init__.py`

2. Legacy root shim modules were retired in verified batches and removed.

9. Shim retirement batches completed:
- Removed root dialog/widget/presenter shims.
- Removed root service/workflow shims.
- Removed root coordinator shims.
- Removed root controller and UI-controller shims.

3. Core composition/runtime imports were moved to canonical package paths in:
- `ui/src/fractal_studio/main_window.py`
- `ui/src/fractal_studio/main_window_factory.py`
- `ui/src/fractal_studio/application/controllers/main_window_controller.py`
- `ui/src/fractal_studio/ui/sections/state.py`
- `ui/src/fractal_studio/ui/sections/panel_state.py`
- `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/settings_dialog_coordinator.py`

4. Coordinator package boundary introduced:
- `ui/src/fractal_studio/application/coordinators/export_panel_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/favorites_panel_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/palette_preview_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/settings_dialog_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/sidebar_wiring_coordinator.py`
- `ui/src/fractal_studio/application/coordinators/__init__.py`

5. Controller package boundary introduced:
- `ui/src/fractal_studio/application/controllers/favorites_controller.py`
- `ui/src/fractal_studio/application/controllers/main_window_controller.py`
- `ui/src/fractal_studio/application/controllers/theme_controller.py`
- `ui/src/fractal_studio/application/controllers/__init__.py`

6. Test imports were canonicalized in:
- `ui/tests/test_ui_redesign.py`

7. Widget-facing controller package boundary introduced:
- `ui/src/fractal_studio/ui/controllers/editor_controller.py`
- `ui/src/fractal_studio/ui/controllers/viewport_controller.py`
- `ui/src/fractal_studio/ui/controllers/params_panel_controller.py`
- `ui/src/fractal_studio/ui/controllers/__init__.py`

8. Import policy guard introduced:
- `ui/tests/test_import_policy.py`

10. Package layout smoke test introduced:
- `ui/tests/test_package_layout_smoke.py`

12. Lint/format normalization pass completed:
- Installed Ruff in the project virtual environment.
- Added Ruff config in `ui/pyproject.toml` (`[tool.ruff.lint.per-file-ignores]`, `tests/*.py = ["E402"]`) to preserve intentional test bootstrap import ordering.
- Ran:
  - `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m ruff format c:/git/graphics/fractal-studio/ui/src c:/git/graphics/fractal-studio/ui/tests`
  - `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m ruff check --fix c:/git/graphics/fractal-studio/ui/src c:/git/graphics/fractal-studio/ui/tests`
- Adjusted code for lint correctness:
  - `ui/src/fractal_studio/main_window.py`
  - `ui/src/fractal_studio/ui/sections/state.py`

13. Sections naming polish completed:
- Renamed `ui/src/fractal_studio/ui/sections/main_window_sections*.py` modules to prefix-free names:
  - `sections.py`, `adapters.py`, `base.py`, `state.py`, `panel_state.py`, `ports.py`, `mediator.py`, `*_adapter.py`
- Updated canonical imports in source and tests to renamed section modules.
- Updated package layout smoke imports to use renamed modules.

14. Sections helper symbol naming polished:
- Renamed `build_main_window_sections_ports` to `build_sections_ports` across source exports/imports.

## Important caution before editing
- `ui/tests/test_ui_redesign.py` was modified after the previous pass. Re-read current file contents before any additional edit to avoid clobbering user/tool changes.

## Verification evidence
- Last full run succeeded:
  - `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest c:/git/graphics/fractal-studio/ui/tests`
  - Result: 131 passed

## Recommended next slice
1. Optional: rename workflow class names for semantic clarity (keep package split unchanged).
2. Optional: add Ruff invocation to CI (same commands used above) to keep style drift from returning.
3. Optional: tighten section type alias naming if desired (`MainWindowSections*` class names) in a separate compatibility-safe pass.

## Naming decision (2026-05-27)
- Keep `application/coordinators` and `application/workflows` package split as-is.
- Defer any class-name-only rename pass to a separate optional slice.

## Quick command set for Claude
1. Validate current baseline:
- `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest c:/git/graphics/fractal-studio/ui/tests`

2. Find any legacy shim imports still present:
- `rg "from fractal_studio\\.(appearance_settings_dialog|custom_resolution_dialog|favorite_hover_presenter|favorite_row_style_presenter|favorite_thumbnail_row|placeholder_panel|settings_service|export_service|palette_service|favorites_workflow_coordinator|startup_coordinator|theme_workflow_coordinator|export_panel_coordinator|favorites_panel_coordinator|palette_panel_coordinator|palette_preview_coordinator|settings_dialog_coordinator|sidebar_wiring_coordinator|favorites_controller|main_window_controller|theme_controller|editor_controller|viewport_controller|params_panel_controller) import" c:/git/graphics/fractal-studio/ui/src c:/git/graphics/fractal-studio/ui/tests`

3. Re-run full tests after each slice:
- `c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest c:/git/graphics/fractal-studio/ui/tests`

## Summary for Claude
- Reorganization and shim retirement are complete and tested.
- Canonical paths are enforced by `ui/tests/test_import_policy.py`.
- Canonical package imports are smoke-tested by `ui/tests/test_package_layout_smoke.py`.
- Main-window sections modules are now canonical under `ui/src/fractal_studio/ui/sections`.
- Current baseline is stable at 131 passing tests.
