# Fractal Studio UI: Current Architectural Deficiencies (2026-05-27)

Scope reviewed:
- `ui/src/fractal_studio/**/*.py`
- Current post-refactor state only (no historical/resolved items)

This document lists only active architectural deficiencies, prioritized by impact on change safety, correctness risk, and maintainability.

Current status:
- No active architectural deficiencies remain in the reviewed `ui/src/fractal_studio/**/*.py` scope.

Residual monitoring notes:
- Keep the import policy guard test (`ui/tests/test_import_policy.py`) active to prevent regressions in import paths.

Recently resolved in this cleanup pass:
- Retired the final shim-removal batches by deleting all remaining root coordinator/controller/ui-controller shim modules.
- Retired the second shim-removal batch by deleting root service/workflow shim modules after canonical import migration and policy enforcement.
- Retired the first shim-removal batch by deleting root dialog/widget/presenter shim modules after canonical import migration and test guard enforcement.
- Added a dedicated import policy guard test that fails if `ui/src` or `ui/tests` imports legacy root-shim modules (`ui/tests/test_import_policy.py`).
- Introduced a dedicated `ui/controllers` package for widget-facing controller concerns and moved in-repo imports to canonical UI controller paths.
- Introduced a dedicated `application/controllers` package for main application controller concerns and moved in-repo imports to canonical controller paths.
- Introduced a dedicated `application/coordinators` package for panel/dialog/sidebar coordination concerns and moved in-repo imports to canonical coordinator paths.
- Completed canonicalization of remaining in-repo imports (including tests) to organized package paths under `ui/`, `services/`, and `application/workflows/`.
- Introduced logical package boundaries for UI dialogs/widgets/presenters with runtime imports moved to canonical package paths.
- Introduced logical package boundaries for workflow and service layers under `application/workflows` and `services` with core composition imports moved to canonical package paths.
- Introduced a dedicated `ui/sections` package and moved the full `main_window_sections*` module family to canonical section package paths.
- Favorites workflow/controller contracts were tightened around typed `FavoriteSnapshot` boundaries.
- `MainWindowSectionsState` orchestration coupling was reduced by moving viewport, export, palette, colormap, sidebar, and favorites panel helpers to explicit bind-time collaborator injection.
- Compatibility-style helper imports through `fractal_studio.main_window` were removed from in-repo callers.
- Direct regression tests now verify the bind-time collaborator contract on the section helper states, and this coverage is isolated in `ui/tests/test_main_window_section_panel_states.py`.
- Startup/theme settings dialog flow now uses explicit dialog-factory protocols and typed startup state handoff instead of `Any`-based contracts.
- Viewport drag rendering now coalesces per-event-loop tick to avoid full synchronous render storms during high-frequency mouse move input.
- Viewport resize rendering now coalesces per-event-loop tick to avoid redundant back-to-back full renders during rapid resize events.
