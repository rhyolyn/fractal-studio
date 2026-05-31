# Fractal Studio - Codex Architectural Analysis

**Date:** 2026-05-30  
**Reviewer:** Codex  
**Scope:** Source code only. Existing architecture/design docs were intentionally excluded from this review so the findings would not be influenced by prior Copilot or Claude-generated analysis.

---

## Executive Summary

Fractal Studio has a promising architectural direction: a Python/PySide6 desktop shell, a Rust rendering core, immutable state objects, a composition root, and an attempted ports/adapters boundary around window sections.

The codebase is partway through a refactor. Several names and folders suggest a clean layered architecture, but key dependencies still flow through concrete Qt widgets, private `MainWindow` state, and synchronous backend calls. The highest-risk issues are settings persistence overwriting sibling fields, rendering/export work blocking the UI thread, and the section ports layer depending on a half-wired `MainWindow`.

**Overall assessment:** structurally promising, but currently over-coupled at the UI/application boundary. The next architectural work should focus less on adding more layers and more on making the existing boundaries real.

---

## Review Method

This review was based on source files under `ui/` and `core/` only. The generated docs in `docs/` were not used as inputs.

Verification performed:

```powershell
cd ui
python -m pytest -q
```

Result: `11 passed, 143 deselected`.

```powershell
cd core
cargo test -q
```

Result: failed. `23 passed`, `1 failed`. The failing test was `tests::legacy_palette_parser_reads_existing_repo_map`, which could not find a referenced path from `core/src/lib.rs`.

---

## Key Findings

### 1. Settings Writes Can Erase Each Other

**Severity:** High  
**Files:**

- `ui/src/fractal_studio/application/workflows/theme_workflow_coordinator.py`
- `ui/src/fractal_studio/main_window.py`
- `ui/src/fractal_studio/application/controllers/settings_controller.py`
- `ui/src/fractal_studio/state.py`

Theme persistence writes a fresh `UiSettings(theme=name)` object. That loses any existing `sidebar_collapsed` values. Sidebar collapse persistence writes from `MainWindow._current_ui_settings`, but that cached settings object is not updated when the theme changes.

Likely user-visible behavior:

- Changing the theme can erase sidebar collapse state.
- Toggling a sidebar section after a theme change can save the old theme back to disk.

**Recommendation:** centralize settings updates behind one aggregate update path. Each settings write should load or hold the current full `UiSettings`, replace exactly one field, and save the whole object.

Target shape:

```python
def update_settings(repo: SettingsRepository, transform: Callable[[UiSettings], UiSettings]) -> UiSettings:
    current = repo.load().settings
    updated = transform(current)
    repo.save(updated)
    return updated
```

Then theme and sidebar persistence become field replacements on the same aggregate instead of competing partial writes.

---

### 2. Rendering And Export Block The UI Thread

**Severity:** High  
**Files:**

- `ui/src/fractal_studio/ui/controllers/viewport_controller.py`
- `ui/src/fractal_studio/services/export_service.py`
- `core/src/lib.rs`

Viewport rendering calls the Rust backend synchronously from the Qt event path. Export does the same after calling `QApplication.processEvents()`, which is a symptom-level workaround rather than an architectural boundary.

The Rust `render_fractal` binding is exposed as a normal PyO3 function with no Python-side worker abstraction, no cancellation, no progress reporting, and no render generation token.

Impact:

- Deep zooms or high iteration counts can freeze the UI.
- Large exports can make the app appear hung.
- Rapid parameter changes can queue stale work conceptually, but there is no explicit stale-result rejection model.
- Future progress bars, cancellation, and tiled export will be harder to add cleanly.

**Recommendation:** introduce a render job boundary before expanding export/render features.

Suggested components:

- `RenderRequest`: formula, viewport bounds, dimensions, palette, coloring, iteration settings.
- `RenderResult`: request id, image bytes, dimensions, status/error.
- `RenderWorker`: runs Rust calls off the UI thread.
- `RenderScheduler`: coalesces/debounces viewport requests and drops stale results.
- `ExportJob`: separate long-running workflow with progress/cancellation.

The existing debounce timer can remain, but its timeout should dispatch work rather than render directly.

---

### 3. Section Ports Depend On A Half-Built MainWindow

**Severity:** High  
**Files:**

- `ui/src/fractal_studio/main_window_factory.py`
- `ui/src/fractal_studio/ui/sections/adapters/base.py`
- `ui/src/fractal_studio/ui/sections/state.py`

The factory builds section ports from `window` before the context is attached. The base adapter then reaches into `owner._sections_state`, a private object that is populated later.

This makes the ports/adapters boundary structurally nice but temporally fragile. The adapters are not truly independent implementations of narrow ports; they are views over mutable private `MainWindow` state.

Impact:

- Construction order matters more than the types reveal.
- Tests need to recreate private wiring details.
- A missing or late-bound collaborator tends to fail as a no-op rather than a clear construction error.
- The composition root is split between `main_window_factory.py`, `MainWindow.attach_context()`, and `MainWindowSectionsState.bind()`.

**Recommendation:** make the composition root own panel-state construction directly.

Target direction:

- Construct repositories, services, controllers, coordinators, backend, and panel states in `main_window_factory.py`.
- Construct section port adapters from explicit panel state objects, not from `MainWindow`.
- Let `MainWindowSectionsState` hold only already-built panel state instances.
- Keep `MainWindow` responsible for shell lifecycle and high-level layout initialization, not dependency construction.

---

### 4. Application And Service Layers Still Import Concrete Qt Widgets

**Severity:** Medium-high  
**Files:**

- `ui/src/fractal_studio/services/export_service.py`
- `ui/src/fractal_studio/services/palette_service.py`
- `ui/src/fractal_studio/application/controllers/favorites_controller.py`
- `ui/src/fractal_studio/application/workflows/favorites_workflow_coordinator.py`

The application/service layer frequently accepts or imports concrete Qt widgets such as `QWidget`, `QFileDialog`, `QApplication`, `FractalViewportWidget`, `FractalParamsPanel`, `ColorCubeEditor`, and `PalettePreviewWidget`.

Some of this is pragmatic for a desktop app, but the current level of widget coupling weakens the intended layering. It also limits unit testing because otherwise domain-ish workflows require Qt object graphs.

Examples:

- Export service reads viewport state and palette directly from `FractalViewportWidget`.
- Palette service owns file dialog calls.
- Favorites controller restores directly into viewport, params panel, editor, and preview widgets.

**Recommendation:** push widget reads/writes to the UI edge and pass data transfer objects inward.

Better boundaries:

- `ExportService.export_render(request: RenderRequest, destination: Path, status: Callable)`
- `PaletteWorkflowService.save_palette(path: Path, control_points: list[Color], palette_size: int)`
- `FavoritesController.restore_snapshot(snapshot) -> RestoreFavoriteResult`

The UI layer can translate those results into widget updates.

---

### 5. Backend Availability Is A Partial Facade, Not A Clear Null Object

**Severity:** Medium  
**Files:**

- `ui/src/fractal_studio/backend.py`
- `ui/src/fractal_studio/ui/controllers/editor_controller.py`
- `ui/src/fractal_studio/ui/controllers/viewport_controller.py`
- `ui/src/fractal_studio/services/palette_service.py`

`CoreBackend.profile()` returns default values when Rust is absent, but operational methods call `_require()` and raise. Other callers often check `backend.available` manually.

That mixed behavior makes the backend contract hard to reason about. Is the backend a null object with safe defaults, or is it a required dependency that must be guarded before use? The code uses both patterns.

Impact:

- New callers must infer whether to guard or trust the backend.
- `BackendProfile` can imply capabilities that are not actually available.
- UI-only mode has to be handled by scattered checks.

**Recommendation:** split capability description from execution.

Possible shape:

```python
@dataclass(frozen=True)
class BackendCapabilities:
    can_render: bool
    can_generate_palette: bool
    can_import_palette: bool
    can_export_palette: bool

class RenderBackend(Protocol):
    def render(request: RenderRequest) -> bytes: ...

class PaletteBackend(Protocol):
    def generate_palette(control_points: list[Color], size: int) -> list[Color]: ...
```

Then the UI can enable/disable features from capabilities, and execution code can depend on explicit backend protocols.

---

### 6. MainWindowSectionsState Is Both State Holder And Composition Sub-root

**Severity:** Medium  
**Files:**

- `ui/src/fractal_studio/ui/sections/state.py`
- `ui/src/fractal_studio/ui/sections/panel_state.py`

`MainWindowSectionsState` stores repositories, services, controllers, coordinators, backend state, section state, and widget references. Its `bind()` method constructs six panel state objects and wires lambdas between them.

The class is doing at least three jobs:

- dependency bag for collaborators,
- factory for panel state machines,
- runtime holder for mutable widget state.

Impact:

- Every feature touching sections has a gravitational pull toward one class.
- Dependencies become available through broad shared state rather than explicit constructor arguments.
- Panel states are harder to reason about in isolation because many receive the aggregate state object plus additional collaborators.

**Recommendation:** reduce it to a panel-state container or remove it entirely.

Target shape:

```python
@dataclass
class MainWindowSectionsState:
    viewport: MainWindowViewportState
    sidebar: MainWindowSidebarState
    palette: MainWindowPaletteState
    colormap: MainWindowColormapState
    favorites: MainWindowFavoritesState
    export: MainWindowExportState
```

Construction belongs in the composition root.

---

### 7. Rust Test Suite Has A Path Assumption

**Severity:** Medium  
**Files:**

- `core/src/lib.rs`

`cargo test -q` failed in `tests::legacy_palette_parser_reads_existing_repo_map` because a referenced path was not found. This is not necessarily an application architecture problem, but it is a build/reliability issue.

Impact:

- The Rust core cannot currently be verified with one standard command from `core/`.
- Contributors may distrust the test suite or skip it.

**Recommendation:** move the expected legacy fixture into `core/tests/fixtures`, or compute the path relative to `CARGO_MANIFEST_DIR` and skip only if the external sample is intentionally optional.

---

## Architectural Strengths

- The repository has a clear Python UI / Rust core split.
- `state.py` uses frozen dataclasses for important persisted state.
- The PyO3 bridge is compact and easy to locate.
- The UI has begun moving widget behavior into controllers and coordinators.
- `ui/pyproject.toml` has pytest markers configured so the default Python test run can stay lightweight.
- The Rust core has meaningful unit coverage around palette generation, rendering variants, and serialization.
- The `SectionPanel` / `ViewportWell` direction is good: focused widgets with narrow responsibilities.

---

## Recommended Priority Order

1. Fix settings persistence so theme and sidebar state cannot overwrite each other.
2. Introduce a render/export job abstraction with worker execution and stale-result handling.
3. Move panel-state construction into `main_window_factory.py`.
4. Rebuild section port adapters around explicit panel state dependencies instead of `MainWindow`.
5. Push concrete Qt widget dependencies out of application/services and into the UI edge.
6. Clarify backend capabilities versus backend execution.
7. Fix the failing Rust path-dependent test.

---

## Bottom Line

The app is not badly architected; it is mid-refactor. The main risk is that architectural names are currently cleaner than the actual dependency flow. The next step should be to make the existing boundaries honest: one settings aggregate owner, one render job boundary, one composition root, and application services that operate on data rather than widgets.
