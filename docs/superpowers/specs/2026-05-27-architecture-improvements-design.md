# Architecture Improvements — Design Spec

**Date:** 2026-05-27  
**Scope:** Immediate + medium-term recommendations from architecture-analysis-2026-05-27.md  
**Approach:** Dependency order — each step leaves the codebase shippable with a green test baseline

---

## Overview

Eight targeted improvements to the fractal-studio Python UI, sequenced so that each step depends only on work that has already been done. Longer-term items (async rendering, command bus, `.pyi` stubs) are out of scope.

---

## Step 1 — Fix Test Infrastructure

**Problem:** Six tests currently fail in environments without PySide6. There is no way to run a green subset of the test suite, so contributors cannot verify that non-UI changes are correct.

**Change:**
- Add `fractal-studio/ui/pytest.ini` with markers `unit` and `integration`.
- Default test run (`pytest`) executes `unit` only.
- Mark all tests that import PySide6 (directly or transitively) with `@pytest.mark.integration`.
- Mark pure-Python tests (`test_backend.py`, `test_import_policy.py`) with `@pytest.mark.unit`.
- `test_package_layout_smoke.py` and `test_main_window_section_panel_states.py` get `integration` (they import application code that imports PySide6).
- `test_ui_redesign.py` gets `integration`.

**Success criteria:**
- `pytest -m unit` passes with zero failures in this environment.
- `pytest -m integration` documents expected failures (PySide6 absent) clearly.
- No test file is left unmarked.

**Files touched:** `pytest.ini` (new), all 6 test files.

---

## Step 2 — Add `validate()` to `MainWindowSectionsState`

**Problem:** Panel state machines register collaborators via `bind_collaborators()`. If any collaborator is not bound, methods return `None` silently. This hides wiring errors until runtime behaviour breaks.

**Change:**
- Add `MainWindowSectionsState.validate()` called at the end of `bind()`.
- `validate()` asserts that every non-optional collaborator attribute on each panel state is not `None`.
- Raise `RuntimeError` with a descriptive message identifying the missing collaborator.
- The check runs once at startup; no cost in steady state.

**What counts as non-optional:** everything currently set in `bind_collaborators()` on each panel state. Optional attributes (e.g., `_hover_panel` on `MainWindowFavoritesState`) are excluded.

**Success criteria:**
- Intentionally omitting a collaborator binding in a test causes an immediate `RuntimeError` with the name of the missing attribute.
- No new failures in the unit test suite.

**Files touched:** `ui/sections/panel_state.py`, `ui/sections/state.py`.

---

## Step 3 — Move Adapters Into a Dedicated Subdirectory

**Problem:** Seven `*_adapter.py` files and the existing `adapters.py` base live directly in `ui/sections/` alongside unrelated files (`ports.py`, `mediator.py`, `panel_state.py`, `state.py`, `sections.py`). The adapters are not visually grouped; finding them requires scanning the whole directory.

**Change:**
- Create `ui/sections/adapters/` directory with an `__init__.py`.
- Move all 7 individual adapter files into the new directory:
  - `viewport_adapter.py`
  - `palette_adapter.py`
  - `colormap_adapter.py`
  - `backend_adapter.py`
  - `export_adapter.py`
  - `favorites_adapter.py`
  - `sidebar_adapter.py`
- Move `adapters.py` (base classes and `_BasePortsAdapter`, `_FavoriteActionsMixin`) into `ui/sections/adapters/base.py`.
- Export all adapter classes from `ui/sections/adapters/__init__.py` so `mediator.py` imports remain `from fractal_studio.ui.sections.adapters import ViewportPanelPortsAdapter, ...`.
- No logic changes to any adapter class.

**Success criteria:**
- `ui/sections/adapters/` contains `__init__.py`, `base.py`, and 7 adapter files.
- `ui/sections/` no longer contains any `*_adapter.py` files or a bare `adapters.py`.
- `mediator.py` imports resolve unchanged (via `__init__.py` re-exports).
- All imports resolve; unit tests pass.

**Files touched:** `ui/sections/adapters/` (new directory), `ui/sections/mediator.py` (import path update if needed), `ui/sections/adapters.py` (deleted, replaced by `adapters/base.py`), 7 moved files.

---

## Step 4 — Delete Thin Coordinators

**Problem:** `ExportPanelCoordinator` and `PalettePreviewCoordinator` contain only one-liner delegations to `MainWindowController` and `PalettePreviewCoordinator` respectively. They add an indirection layer with no orchestration value.

**Change:**
- Identify all call sites of `ExportPanelCoordinator` and `PalettePreviewCoordinator` in panel state machines and adapters.
- Replace each call with a direct call to the underlying collaborator.
- Delete `application/coordinators/export_panel_coordinator.py`.
- Delete `application/coordinators/palette_preview_coordinator.py`.
- Remove them from `MainWindowContext` in `main_window_factory.py` and from `MainWindowSectionsState`.

**What is NOT deleted:** `FavoritesPanelCoordinator`, `PalettePanelCoordinator`, `SettingsDialogCoordinator`, `SidebarWiringCoordinator` — all have genuine orchestration logic.

**Success criteria:**
- The two files are gone.
- All call sites resolve to the underlying collaborator directly.
- No new logic is introduced — this is a pure inlining.
- Unit tests pass.

**Files touched:** `application/coordinators/export_panel_coordinator.py` (deleted), `application/coordinators/palette_preview_coordinator.py` (deleted), `ui/sections/panel_state.py`, `main_window_factory.py`, `ui/sections/state.py`.

---

## Step 5 — Document the Controller/Coordinator/Workflow Contract

**Problem:** The boundary between controllers, coordinators, and workflows is enforced only by convention. New contributors (or future sessions) will recreate the ambiguity.

**Change:**
- Add a module docstring to `application/controllers/__init__.py`:
  > Controllers are stateless atoms of domain logic. They hold no mutable state after construction. They may reference repositories and services but must not reference Qt widgets directly.
- Add a module docstring to `application/coordinators/__init__.py`:
  > Coordinators orchestrate use cases by combining controllers and services. They may hold references to UI panels via port protocols, but must not subclass QWidget or hold direct widget references.
- Add a module docstring to `application/workflows/__init__.py`:
  > Workflows implement user-visible multi-step operations that cross panel boundaries and produce UI feedback (status messages, dialogs). Each workflow corresponds to one named user action.
- Add a one-line comment above each class in each layer referencing which contract it satisfies (e.g., `# Controller: stateless domain logic`).

**Success criteria:**
- Each `__init__.py` has a docstring that a new contributor can read in 30 seconds.
- No structural code changes.

**Files touched:** `application/controllers/__init__.py`, `application/coordinators/__init__.py`, `application/workflows/__init__.py`, and optionally the class files themselves.

---

## Step 6 — Split `MainWindowController`

**Problem:** `MainWindowController` handles export preset computation, aspect ratio logic, export delegation, settings dialog lifecycle, and theme coordination. It is the largest controller and growing.

**Change:**
Split into two controllers:

**`ExportController`** — owns:
- `build_export_presets_for_mode()`
- `apply_aspect_ratio_mode()`
- `refresh_export_presets()`
- `on_export_clicked()` / `export_render()`
- `build_export_presets()` helpers

**`SettingsController`** — owns:
- `open_settings_dialog()`
- `apply_aspect_ratio_mode()` (UI side — delegates to ExportController for presets)

`MainWindowController` is deleted once both replacements are complete.

**Injection:** Both new controllers are constructed in `main_window_factory.py` and added to `MainWindowContext`. Panel states that currently reference `MainWindowController` are updated to reference the appropriate split controller.

**Success criteria:**
- `MainWindowController` does not exist.
- Each new controller satisfies the "stateless domain logic" contract from Step 5.
- All existing test coverage for export and settings behaviour still passes.

**Files touched:** `application/controllers/main_window_controller.py` (deleted), new `application/controllers/export_controller.py`, new `application/controllers/settings_controller.py`, `main_window_factory.py`, `ui/sections/panel_state.py`.

---

## Step 7 — Decompose `ViewportState`

**Problem:** `ViewportState` has ~15 fields. Formula-specific parameters (Julia `cx/cy`, Phoenix `real/imag`, Newton trap point) are always present regardless of which formula is active. Invalid parameter combinations are representable.

**Change:**
Introduce formula-specific parameter sub-structs:

```python
@dataclass(frozen=True)
class MandelbrotParams:
    pass  # no extra params

@dataclass(frozen=True)
class JuliaParams:
    cx: float = 0.0
    cy: float = 0.0

@dataclass(frozen=True)
class PhoenixParams:
    real: float = 0.0
    imag: float = 0.0

@dataclass(frozen=True)
class NewtonParams:
    trap_x: float = 0.0
    trap_y: float = 0.0

FormulaParams = MandelbrotParams | JuliaParams | PhoenixParams | NewtonParams
```

`ViewportState` gains a `formula_params: FormulaParams` field; the individual flat fields (`cx`, `cy`, `real`, `imag`, `trap_x`, `trap_y`) are removed.

**Serialization:** `ViewportState.to_dict()` serializes `formula_params` as a nested dict with a `type` discriminator key. `from_dict()` dispatches on `type` to reconstruct the correct sub-struct. Legacy format (flat fields, no `type` key) is detected by absence of `formula_params` and converted on load.

**Affected callers:**
- `FractalParamsPanel.to_state()` / `apply_state()` — constructs/reads `FormulaParams`
- `ViewportController` — passes `formula_params` fields to backend
- `backend.py` — unpacks sub-struct before calling `fractal_core`
- `test_backend.py`, `test_ui_redesign.py` — update fixture construction

**Success criteria:**
- `ViewportState` has no flat `cx`, `cy`, `real`, `imag`, `trap_x`, `trap_y` fields.
- Round-trip serialization test passes for each formula type.
- Legacy flat-format JSON loads correctly and converts to the new structure.
- Unit tests pass; integration tests pass in environments with PySide6.

**Files touched:** `state.py`, `persistence.py`, `viewport.py`, `backend.py`, `ui/controllers/viewport_controller.py`, `ui/controllers/params_panel_controller.py` (if it reads formula-specific fields), test files.

---

## Step 8 — Shrink `MainWindowSectionsState.bind()`

**Problem:** `MainWindowSectionsState.bind()` is an 80-line method that wires all collaborators to all panel state machines via lambdas. It is the integration point for the entire application but provides no validation and is hard to read.

**Change:**
Refactor panel state machine constructors to accept their collaborators at construction time:

- Each panel state class (`MainWindowViewportState`, `MainWindowFavoritesState`, etc.) receives its specific collaborators as constructor arguments rather than via `bind_collaborators()`.
- `MainWindowSectionsState.__init__()` constructs each panel state with its collaborators directly.
- `bind()` is reduced to wiring cross-panel callbacks only (e.g., viewport → params panel signal connections) — the part that genuinely requires both panel states to exist.
- Lambda closures in `bind_collaborators()` are replaced by direct constructor injection.
- The `validate()` method from Step 2 is updated to check constructor arguments (simpler now).

**Panel state constructor signatures (illustrative):**

```python
class MainWindowViewportState:
    def __init__(self, controller: ExportController, coordinator: ..., ...):
        ...

class MainWindowFavoritesState:
    def __init__(self, controller: FavoritesController, workflow: ..., repo: ..., ...):
        ...
```

**Success criteria:**
- `bind()` is under 20 lines.
- Each panel state's constructor clearly documents its dependencies.
- No lambda closures remain in `bind()` for collaborator assignment.
- `validate()` checks constructor arguments rather than post-bind attributes.
- All unit tests pass.

**Files touched:** `ui/sections/panel_state.py`, `ui/sections/state.py`, `main_window_factory.py`.

---

## Sequence Summary

| Step | Item | Tier | Depends On |
|------|------|------|------------|
| 1 | Fix test infrastructure | Immediate | — |
| 2 | Add `validate()` | Immediate | Step 1 (green baseline) |
| 3 | Move adapters into `ui/sections/adapters/` | Immediate | Step 1 |
| 4 | Delete thin coordinators | Immediate | Steps 1–2 |
| 5 | Document layer contracts | Medium | Step 4 (docs reflect clean reality) |
| 6 | Split `MainWindowController` | Medium | Steps 2, 5 |
| 7 | Decompose `ViewportState` | Medium | Step 1 |
| 8 | Shrink `bind()` | Medium | Steps 2, 4, 6 |

Steps 3 and 7 have no inter-dependencies and can be done in parallel with adjacent steps if desired.

---

## Out of Scope

- Async rendering / QThread render pipeline
- Internal event/command bus
- `fractal_core.pyi` stub file
- Rust core implementation
