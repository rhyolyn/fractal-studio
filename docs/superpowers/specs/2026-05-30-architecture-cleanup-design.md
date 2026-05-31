# Architecture Cleanup Design Spec

**Date:** 2026-05-30
**Status:** Approved
**Scope:** Python UI layer (`ui/`) + Rust core test fix (`core/`)
**Out of scope:** Async rendering (F2) — deferred to a future spec

---

## Problem

The codebase has the right vocabulary — ports, adapters, controllers, repositories, a composition root — but four architectural boundaries exist in name only. The actual dependency lines don't honour the intended layering:

- Settings writes construct fresh `UiSettings` objects, silently erasing unrelated fields
- Services and application controllers accept Qt widget instances, making them untestable without PySide6
- The composition root is split across three phases, with construction order as a hidden invariant
- The backend is simultaneously a null object and a required dependency, with no consistent contract

This spec makes all four boundaries real and verifiable.

---

## Boundaries

### Boundary 1 — Settings write path

**Rule:** No caller constructs a `UiSettings` object. All mutations go through a single aggregate method on `SettingsRepository`.

```python
# persistence.py
def update(self, transform: Callable[[UiSettings], UiSettings]) -> UiSettings:
    current = self.load().settings
    updated = transform(current)
    self.save(updated)
    return updated

# call sites
repo.update(lambda s: dataclasses.replace(s, theme=name))
repo.update(lambda s: dataclasses.replace(s, sidebar_collapsed=collapsed))
```

`SettingsController` routes all writes through `repo.update()`. `ThemeWorkflowCoordinator` stops constructing fresh `UiSettings` objects. `MainWindow._current_ui_settings` is removed — callers receive the return value or read from the repo.

**Files:** `persistence.py`, `settings_controller.py`, `theme_workflow_coordinator.py`

---

### Boundary 2 — Service layer

**Rule:** Nothing in `application/` or `services/` imports from PySide6 or from `ui/widgets/`. An import policy test enforces this mechanically.

Services and application controllers accept plain Python values — frozen dataclasses from `state.py`, primitives, `Path` objects, and typed callbacks. All widget reads happen in the UI edge (panel states and adapters) before calling down. All widget writes happen in callbacks registered by the UI edge.

**Pattern:**
```
Before: service(widget)          — service reaches in for data, writes back to widget
After:  service(data, on_result) — panel state reads widget → passes data in, applies result out
```

**Specific changes:**

`ExportService` — remove `FractalViewportWidget` parameter; accept `ViewportState` and palette control points as data.

`PaletteService` — remove `QFileDialog` calls; file dialog moves to the panel state; service receives a `Path`.

`FavoritesController` — remove widget parameters (`FractalViewportWidget`, `FractalParamsPanel`, `ColorCubeEditor`, `PalettePreviewWidget`); replace with typed callbacks registered by the panel state.

`FavoritesWorkflowCoordinator` — same cleanup as controller.

Where a new result type is genuinely needed it goes in `state.py` as a frozen dataclass. In most cases `ViewportState`, `FavoriteSnapshot`, and `Path` are sufficient.

`test_import_policy.py` gains a new check: no file under `application/` or `services/` may import from `PySide6` or from `fractal_studio.ui.widgets`.

**Files:** `export_service.py`, `palette_service.py`, `favorites_controller.py`, `favorites_workflow_coordinator.py`, affected panel states and adapters, `test_import_policy.py`

---

### Boundary 3 — Construction

**Rule:** `main_window_factory.py` is the single construction pass. No deferred wiring phases.

**Target construction sequence:**

```
repos → services → controllers → coordinators → backend
→ MainWindow shell        (creates Qt window + status bar)
→ on_status callback      (window.statusBar().showMessage)
→ panel states            (built with explicit collaborators + on_status)
→ section adapters        (built from panel states, not from MainWindow)
→ MainWindowSectionsState (container only)
→ sections layout
→ window.initialize_sections(sections)
```

`MainWindow` is created early so the status bar exists to extract `on_status`. It receives nothing else until `initialize_sections()` at the end, which does Qt layout assembly only — no construction.

**`MainWindowSectionsState` becomes a plain container:**

```python
@dataclass
class MainWindowSectionsState:
    viewport: MainWindowViewportState
    sidebar:  MainWindowSidebarState
    palette:  MainWindowPaletteState
    colormap: MainWindowColormapState
    favorites: MainWindowFavoritesState
    export:   MainWindowExportState
```

`bind()` is deleted. Cross-panel callbacks (currently wired as lambdas in `bind()`) move into the factory where all collaborators are in scope.

Panel states stop accepting `owner: MainWindow`. Every `owner.statusBar().showMessage()` call is replaced by the injected `on_status: Callable[[str], None]`.

Section adapters are constructed from panel state objects, eliminating the `owner._sections_state` private reach-through.

`validate()` switches from a hardcoded string list to `dataclasses.fields()` filtered by type annotation — complete coverage by construction.

`attach_context()` is removed. `initialize_sections()` is its minimal replacement.

**Files:** `main_window_factory.py`, `main_window.py`, `ui/sections/state.py`, `ui/sections/panel_state.py`, `ui/sections/adapters/base.py`, all section adapter files

---

### Boundary 4 — Backend contract

**Rule:** `BackendCapabilities` describes what the backend can do. `CoreBackend` is a pure null object. No `backend.available` branching in the application or service layers.

**`BackendCapabilities`** is a new frozen dataclass:

```python
@dataclass(frozen=True)
class BackendCapabilities:
    can_render: bool
    can_generate_palette: bool
    can_import_palette: bool
    can_export_palette: bool
```

`CoreBackend.capabilities` returns a `BackendCapabilities` instance — all flags `False` when Rust is absent.

`CoreBackend` commits to pure null object: `_require()` is removed. Every operational method returns a safe default when Rust is absent (empty bytes, empty list, etc.) instead of raising.

**Caller split:**

- UI layer reads `backend.capabilities` once at startup to enable or disable controls.
- Application and service layers call backend methods unconditionally, trusting the null object.
- All `if not backend.available` guards are removed from `application/` and `services/`.
- `backend.available` survives as a display-only property for the status panel.

**Note:** `RenderBackend` and `PaletteBackend` protocol interfaces are intentionally deferred to the async rendering spec. Introducing them now would require shaping them around `RenderRequest`, which doesn't exist yet.

**Files:** `backend.py`, `editor_controller.py`, `viewport_controller.py`, `palette_service.py`

---

## Rust test fix

**Finding F7:** `cargo test -q` fails in `tests::legacy_palette_parser_reads_existing_repo_map` because the referenced path doesn't resolve when run from `core/`.

**Fix:** Compute the path relative to `env!("CARGO_MANIFEST_DIR")` and move the fixture file into `core/tests/fixtures/`. `cargo test` becomes reliably green from any working directory.

**Files:** `core/src/lib.rs`, new `core/tests/fixtures/<fixture-file>`

---

## Execution plan

Four numbered plans, each independently committable with its own test coverage. Each plan's tests must be green before moving to the next.

| Plan | Findings | Description | Risk |
|------|----------|-------------|------|
| arch-01 | F7 + F1 | Rust test fix + settings aggregate | Low |
| arch-02 | F4 | Service boundary — push Qt to the UI edge | Medium |
| arch-03 | F3 + F6 | Construction boundary — single composition root | High |
| arch-04 | F5 | Backend contract — capabilities + null object | Medium |

**Dependency order:** arch-01 and arch-02 are independent and can be done in either order. arch-03 assumes arch-02 is complete (cleaner call sites make the factory rewrite easier to read). arch-04 is independent of all others.

---

## Testing approach

Each plan must leave the test suite green at its commit boundary.

- **arch-01:** New unit tests for `SettingsRepository.update()` — two concurrent field writes don't erase each other; transform receives current loaded state; returned value matches saved state. Rust suite green with `cargo test` from `core/`.
- **arch-02:** New import policy check in `test_import_policy.py`. Unit tests for refactored services and controllers — no PySide6 required in the test module. All existing integration tests still pass.
- **arch-03:** Existing integration tests are the primary safety net. Factory construction must succeed without `attach_context()` or `bind()`. `validate()` coverage via `dataclasses.fields()` is verified by a unit test that adds a field and confirms it is caught.
- **arch-04:** Unit tests for `BackendCapabilities` — correct values when core absent; correct values when core present. Unit test that no file under `application/` or `services/` calls `backend.available`.

---

## What this does not cover

- **Async rendering (F2):** `RenderWorker`, `RenderScheduler`, `ExportJob` — future spec.
- **Backend execution protocols (`RenderBackend`, `PaletteBackend`):** deferred to the async rendering spec.
- **New UI features:** this spec is pure structural cleanup, no new user-visible behaviour.
