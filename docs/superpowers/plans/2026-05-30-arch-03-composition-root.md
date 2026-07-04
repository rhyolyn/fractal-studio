> **Status: COMPLETED — historical record (executed 2026-05/06, verified in-tree 2026-07-03). Do not execute.** Live work is tracked in [2026-07-03-review-00-master.md](2026-07-03-review-00-master.md).

# Architecture Cleanup 03 — Composition Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `main_window_factory.py` the single construction pass, eliminating `MainWindowSectionsState.bind()` and `MainWindow.attach_context()` as deferred wiring phases.

**Architecture:** Currently construction is split: `build_main_window_context()` builds repos/services/controllers, then `attach_context()` calls `bind()` which builds all six panel states with `owner: MainWindow` and `sections_state` as a shared dependency bag. After this plan: the factory builds everything in one pass. Panel states receive explicit collaborators and an `on_status: Callable[[str], None]` callback instead of `owner`. `MainWindowSectionsState` becomes a plain `@dataclass` container. `bind()` is deleted. `attach_context()` is replaced by `initialize_sections()` which does Qt layout assembly only. Run `arch-01` and `arch-02` before this plan.

**Tech Stack:** Python 3.12, PySide6, pytest

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `ui/src/fractal_studio/ui/sections/panel_state.py` | Remove `sections_state` and `owner` constructor params; add `on_status` |
| Modify | `ui/src/fractal_studio/ui/sections/state.py` | Replace god-object with plain `@dataclass` container; delete `bind()`; update `validate()` |
| Modify | `ui/src/fractal_studio/main_window_factory.py` | Build panel states explicitly; remove `build_main_window_context(window)` window dependency; use two-phase construction |
| Modify | `ui/src/fractal_studio/main_window.py` | Replace `attach_context()` with `initialize_sections()`; remove `_sections_state` god-object usage |
| Modify | `ui/src/fractal_studio/ui/sections/adapters/base.py` | Remove `owner._sections_state` reach-through |

---

## Task 1: Remove `sections_state` and `owner` from panel state constructors

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py`

Each of the six panel state classes currently takes `sections_state: MainWindowSectionsState` as its first positional argument. Some also take `owner: MainWindow`. These are replaced with explicit collaborator parameters and `on_status: Callable[[str], None]`.

Read `ui/src/fractal_studio/ui/sections/panel_state.py` in full before making any edits. Then apply the following changes:

- [ ] **Step 1: Update `MainWindowViewportState.__init__`**

Remove `sections_state: MainWindowSectionsState` as first positional parameter. Remove the `self._sections_state = sections_state` assignment. The remaining keyword parameters (`controller`, `export_panel`, `refresh_export_presets`) stay unchanged. The class no longer needs the TYPE_CHECKING import for `MainWindowSectionsState` if that was its only use.

New signature:
```python
class MainWindowViewportState:
    def __init__(
        self,
        *,
        controller: ExportController | None = None,
        export_panel: ExportPanelCoordinator | None = None,
        refresh_export_presets: Callable[[], None] | None = None,
    ) -> None:
        self._controller = controller
        self._export_panel = export_panel
        self._refresh_export_presets = refresh_export_presets
        self.viewport: FractalViewportWidget | None = None
        self.viewport_hint_label: QLabel | None = None
        self.aspect_ratio_combo: QComboBox | None = None
        self.aspect_ratio_mode: str = "square"
```

- [ ] **Step 2: Update `MainWindowSidebarState.__init__`**

Remove `sections_state` positional param and its assignment. Remaining params unchanged.

New signature:
```python
class MainWindowSidebarState:
    def __init__(
        self,
        *,
        sidebar_wiring: SidebarWiringCoordinator | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        settings_service: SettingsWorkflowService | None = None,
        backend_loaded_getter: Callable[[], bool] | None = None,
        backend_available_getter: Callable[[], bool] | None = None,
    ) -> None:
        self._sidebar_wiring = sidebar_wiring
        self._viewport_getter = viewport_getter
        self._settings_service = settings_service
        self._backend_loaded_getter = backend_loaded_getter
        self._backend_available_getter = backend_available_getter
        self.params_panel: FractalParamsPanel | None = None
        self.backend_state_label: QLabel | None = None
```

- [ ] **Step 3: Update `MainWindowPaletteState.__init__`**

Remove `sections_state` positional param and its assignment.

New signature:
```python
class MainWindowPaletteState:
    def __init__(
        self,
        *,
        palette_preview: PalettePreviewCoordinator | None = None,
        backend: CoreBackend | None = None,
        legacy_palette_size_getter: Callable[[], int | None] | None = None,
        editor_getter: Callable[[], ColorCubeEditor | None] | None = None,
    ) -> None:
        self._palette_preview = palette_preview
        self._backend = backend
        self._legacy_palette_size_getter = legacy_palette_size_getter
        self._editor_getter = editor_getter
        self.preview_palette: PalettePreviewWidget | None = None
        self.preview_legacy: PalettePreviewWidget | None = None
        self.point_summary: QLabel | None = None
        self.palette_summary: QLabel | None = None
```

- [ ] **Step 4: Update `MainWindowColormapState.__init__`**

Remove `sections_state` positional param. Replace `owner: MainWindow | None` with `on_status: Callable[[str], None] | None`. Replace `parent: self._owner` calls with `on_status` calls.

Read the full `MainWindowColormapState` body to find every `self._owner.statusBar().showMessage(...)` call and replace it with `if self._on_status: self._on_status(message)`.

New signature:
```python
class MainWindowColormapState:
    def __init__(
        self,
        *,
        palette_panel: PalettePanelCoordinator | None = None,
        backend: CoreBackend | None = None,
        on_status: Callable[[str], None] | None = None,
        legacy_palette_size_getter: Callable[[], int | None] | None = None,
    ) -> None:
        self._palette_panel = palette_panel
        self._backend = backend
        self._on_status = on_status
        self._legacy_palette_size_getter = legacy_palette_size_getter
        self.editor: ColorCubeEditor | None = None
```

In `load_palette_json()` and `export_legacy_map()`, replace `parent=self._owner` with `parent=None` for now (dialog parent will be revisited in a later cleanup), and replace `set_status=self._owner.statusBar().showMessage` with `set_status=self._on_status or (lambda _: None)`.

- [ ] **Step 5: Update `MainWindowExportState.__init__`**

Remove `sections_state` positional param. Replace `owner: MainWindow | None` with `on_status: Callable[[str], None] | None`.

Read the full `MainWindowExportState` body to find every `self._owner` usage and replace status calls with `self._on_status`.

New signature:
```python
class MainWindowExportState:
    def __init__(
        self,
        *,
        export_panel: ExportPanelCoordinator | None = None,
        controller: ExportController | None = None,
        on_status: Callable[[str], None] | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        aspect_ratio_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self._export_panel = export_panel
        self._controller = controller
        self._on_status = on_status
        self._viewport_getter = viewport_getter
        self._aspect_ratio_mode_getter = aspect_ratio_mode_getter
```

- [ ] **Step 6: Update `MainWindowFavoritesState.__init__`**

Remove `sections_state` positional param. Replace `owner: MainWindow | None` with `on_status: Callable[[str], None] | None`.

New signature:
```python
class MainWindowFavoritesState:
    def __init__(
        self,
        *,
        favorites_controller: FavoritesController | None = None,
        favorites_panel: FavoritesPanelCoordinator | None = None,
        favorites_workflow: FavoritesWorkflowCoordinator | None = None,
        favorites_repo: FavoritesRepository | None = None,
        on_status: Callable[[str], None] | None = None,
        hover_panel_getter: Callable[[], QLabel | None] | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        params_panel_getter: Callable[[], FractalParamsPanel | None] | None = None,
        editor_getter: Callable[[], ColorCubeEditor | None] | None = None,
        preview_palette_getter: Callable[[], PalettePreviewWidget | None] | None = None,
        apply_aspect_ratio_mode: Callable[[str], str] | None = None,
        aspect_ratio_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        ...
```

Replace all `self._owner.statusBar().showMessage(...)` calls with `if self._on_status: self._on_status(message)`.

- [ ] **Step 7: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass. (Integration tests may fail at this point — that's expected until Task 2.)

---

## Task 2: Replace `MainWindowSectionsState` god-object with a plain container

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/state.py`

- [ ] **Step 1: Rewrite `state.py`**

The new `MainWindowSectionsState` is a plain `@dataclass` holding the six built panel states. `bind()` is deleted. `validate()` uses `dataclasses.fields()`.

Replace the entire file with:

```python
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from fractal_studio.ui.sections.panel_state import (
    MainWindowColormapState,
    MainWindowExportState,
    MainWindowFavoritesState,
    MainWindowPaletteState,
    MainWindowSidebarState,
    MainWindowViewportState,
)


@dataclass
class MainWindowSectionsState:
    viewport: MainWindowViewportState
    sidebar: MainWindowSidebarState
    palette: MainWindowPaletteState
    colormap: MainWindowColormapState
    favorites: MainWindowFavoritesState
    export: MainWindowExportState

    def validate(self) -> None:
        for f in dataclasses.fields(self):
            if getattr(self, f.name) is None:
                raise RuntimeError(
                    f"MainWindowSectionsState.validate(): '{f.name}' is None."
                )
```

- [ ] **Step 2: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

---

## Task 3: Rebuild `main_window_factory.py` with a single construction pass

**Files:**
- Modify: `ui/src/fractal_studio/main_window_factory.py`

The factory currently takes `window: MainWindow` as a parameter to pass to `build_sections_ports(window)`. After this task the factory creates the window internally (or receives it only for status bar extraction), builds everything, and returns a fully-wired window.

Read `ui/src/fractal_studio/main_window_factory.py` and `ui/src/fractal_studio/ui/sections/adapters/base.py` in full before editing.

- [ ] **Step 1: Update `create_main_window()` to own the full construction sequence**

Replace the `build_main_window_context()` and `create_main_window()` functions with a new single `create_main_window()` that follows this order:

```python
def create_main_window() -> MainWindow:
    from fractal_studio.main_window import MainWindow

    # 1. Build repos, services, controllers, coordinators, backend
    favorites_repo = FavoritesRepository(Path.home() / ".fractal_studio" / "favorites.json")
    settings_repo = SettingsRepository(Path.home() / ".fractal_studio" / "settings.json")
    settings_service = SettingsWorkflowService()
    theme_controller = ThemeController()
    startup = WindowStartupCoordinator(settings_repo, settings_service, theme_controller)
    favorites_controller = FavoritesController()
    favorites_panel = FavoritesPanelCoordinator(FavoriteHoverPresenter())
    favorites_workflow = FavoritesWorkflowCoordinator(favorites_controller, favorites_panel)
    backend = load_backend()
    export_service = ExportService(backend)
    palette_service = PaletteWorkflowService()
    palette_panel = PalettePanelCoordinator(palette_service)
    palette_preview = PalettePreviewCoordinator(favorites_controller)
    sidebar_wiring = SidebarWiringCoordinator()
    export_controller = ExportController(export_service)
    settings_controller = SettingsController()
    export_panel = ExportPanelCoordinator(export_controller)
    settings_dialog = SettingsDialogCoordinator(settings_controller, settings_service)
    theme_workflow = ThemeWorkflowCoordinator(settings_dialog, theme_controller, settings_repo)
    backend_loaded = backend.available
    backend_profile = backend.profile()

    # 2. Create MainWindow shell so status bar exists
    window = MainWindow()
    on_status: Callable[[str], None] = window.statusBar().showMessage

    # 3. Build panel states with explicit collaborators
    legacy_size: Callable[[], int | None] = lambda: backend_profile.legacy_palette_size

    export_state = MainWindowExportState(
        export_panel=export_panel,
        controller=export_controller,
        on_status=on_status,
    )
    viewport_state = MainWindowViewportState(
        controller=export_controller,
        export_panel=export_panel,
        refresh_export_presets=export_state.refresh_export_presets,
    )
    export_state_viewport_getter: Callable[[], FractalViewportWidget | None] = (
        lambda: viewport_state.viewport
    )
    export_state_aspect_getter: Callable[[], str] = lambda: viewport_state.aspect_ratio_mode
    export_state.set_viewport_getter(export_state_viewport_getter)
    export_state.set_aspect_ratio_mode_getter(export_state_aspect_getter)

    colormap_state = MainWindowColormapState(
        palette_panel=palette_panel,
        backend=backend,
        on_status=on_status,
        legacy_palette_size_getter=legacy_size,
    )
    palette_state = MainWindowPaletteState(
        palette_preview=palette_preview,
        backend=backend,
        legacy_palette_size_getter=legacy_size,
        editor_getter=lambda: colormap_state.editor,
    )
    sidebar_state = MainWindowSidebarState(
        sidebar_wiring=sidebar_wiring,
        viewport_getter=lambda: viewport_state.viewport,
        settings_service=settings_service,
        backend_loaded_getter=lambda: backend_loaded,
        backend_available_getter=lambda: backend.available,
    )
    favorites_state = MainWindowFavoritesState(
        favorites_controller=favorites_controller,
        favorites_panel=favorites_panel,
        favorites_workflow=favorites_workflow,
        favorites_repo=favorites_repo,
        on_status=on_status,
        hover_panel_getter=lambda: window.hover_panel,
        viewport_getter=lambda: viewport_state.viewport,
        params_panel_getter=lambda: sidebar_state.params_panel,
        editor_getter=lambda: colormap_state.editor,
        preview_palette_getter=lambda: palette_state.preview_palette,
        apply_aspect_ratio_mode=viewport_state.apply_aspect_ratio_mode,
        aspect_ratio_mode_getter=lambda: viewport_state.aspect_ratio_mode,
    )

    # 4. Build sections state container
    sections_state = MainWindowSectionsState(
        viewport=viewport_state,
        sidebar=sidebar_state,
        palette=palette_state,
        colormap=colormap_state,
        favorites=favorites_state,
        export=export_state,
    )
    sections_state.validate()

    # 5. Build section adapters from panel states (not from window)
    sections_ports = build_sections_ports(sections_state)
    sections = MainWindowSections(sections_ports)

    # 6. Initialize window with fully-built sections
    window.initialize_sections(
        sections=sections,
        sections_state=sections_state,
        favorites_repo=favorites_repo,
        settings_repo=settings_repo,
        settings_controller=settings_controller,
        settings_service=settings_service,
        startup=startup,
        favorites_controller=favorites_controller,
        favorites_panel=favorites_panel,
        favorites_workflow=favorites_workflow,
        theme_controller=theme_controller,
        backend=backend,
        backend_loaded=backend_loaded,
        backend_profile=backend_profile,
        theme_workflow=theme_workflow,
    )

    return window
```

Note: `build_sections_ports()` must be updated to accept `MainWindowSectionsState` instead of `MainWindow` (see Task 4). `export_state.set_viewport_getter()` and `export_state.set_aspect_ratio_mode_getter()` are setter methods you add to `MainWindowExportState` in Task 1 to handle the circular dependency between viewport_state and export_state.

- [ ] **Step 2: Add `set_viewport_getter` and `set_aspect_ratio_mode_getter` to `MainWindowExportState`**

In `panel_state.py`, add to `MainWindowExportState`:

```python
    def set_viewport_getter(
        self, getter: Callable[[], FractalViewportWidget | None]
    ) -> None:
        self._viewport_getter = getter

    def set_aspect_ratio_mode_getter(self, getter: Callable[[], str]) -> None:
        self._aspect_ratio_mode_getter = getter
```

- [ ] **Step 3: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

---

## Task 4: Update `build_sections_ports()` to use `MainWindowSectionsState`

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/adapters/base.py`
- Modify: `ui/src/fractal_studio/ui/sections/mediator.py`

The current `build_sections_ports(window: MainWindow)` reaches into `window._sections_state` (private). After this task it accepts the already-built `sections_state` directly.

Read `ui/src/fractal_studio/ui/sections/mediator.py` and `ui/src/fractal_studio/ui/sections/adapters/base.py` before editing.

- [ ] **Step 1: Update `build_sections_ports()` in `mediator.py`**

Change the function signature from:
```python
def build_sections_ports(window: MainWindow) -> MainWindowSectionsPorts:
```
to:
```python
def build_sections_ports(sections_state: MainWindowSectionsState) -> MainWindowSectionsPorts:
```

Update all usages inside the function body to use `sections_state` directly instead of `window._sections_state`.

- [ ] **Step 2: Update adapter base if it references `owner._sections_state`**

In `base.py`, remove any reach-through to `owner._sections_state`. Adapters should accept the panel state they need as a constructor argument, or access it through the `sections_state` container passed at construction time.

Read `base.py` in full and update accordingly.

- [ ] **Step 3: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

---

## Task 5: Replace `attach_context()` with `initialize_sections()` in `MainWindow`

**Files:**
- Modify: `ui/src/fractal_studio/main_window.py`

Read `ui/src/fractal_studio/main_window.py` in full before editing.

- [ ] **Step 1: Remove `attach_context()` and add `initialize_sections()`**

Delete the `attach_context()` method entirely.

Add `initialize_sections()` which accepts the fully-built objects and does only Qt layout assembly:

```python
    def initialize_sections(
        self,
        *,
        sections: MainWindowSections,
        sections_state: MainWindowSectionsState,
        favorites_repo: FavoritesRepository,
        settings_repo: SettingsRepository,
        settings_controller: SettingsController,
        settings_service: SettingsWorkflowService,
        startup: WindowStartupCoordinator,
        favorites_controller: FavoritesController,
        favorites_panel: FavoritesPanelCoordinator,
        favorites_workflow: FavoritesWorkflowCoordinator,
        theme_controller: ThemeController,
        backend: CoreBackend,
        backend_loaded: bool,
        backend_profile: BackendProfile,
        theme_workflow: ThemeWorkflowCoordinator,
    ) -> None:
        self._sections = sections
        self._sections_state = sections_state
        self._favorites_repo = favorites_repo
        self._settings_repo = settings_repo
        self._settings_controller = settings_controller
        self._settings_service = settings_service
        self._startup = startup
        self._favorites_controller = favorites_controller
        self._favorites_panel = favorites_panel
        self._favorites_workflow = favorites_workflow
        self._theme_controller = theme_controller
        self.backend = backend
        self.backend_loaded = backend_loaded
        self.backend_profile = backend_profile
        self._theme_workflow = theme_workflow
        self.initialize()
```

- [ ] **Step 2: Update `_sections_state` accesses in `MainWindow`**

The `_sections_state` is now a `MainWindowSectionsState` container with named panel states. Any code that accessed panel states through the old bag (e.g., `self._sections_state._favorites_state`) must now use `self._sections_state.favorites`.

Search for old-style accesses:
```powershell
rg -n "_sections_state\." ui/src/fractal_studio/main_window.py
```

Update each to use the new named attributes (`viewport`, `sidebar`, `palette`, `colormap`, `favorites`, `export`).

- [ ] **Step 3: Add `hover_panel` as a public attribute on `MainWindow`**

The factory references `window.hover_panel` (used in the `hover_panel_getter` lambda). Make it public in `_init_window_state()`:

```python
    def _init_window_state(self) -> None:
        self.hover_panel: QLabel | None = None
        self._theme_name = "light"
        self._theme_spec: ThemeSpec = get_theme(self._theme_name)
        self._startup_sidebar_collapsed: dict[str, bool] = {}
```

Update `_init_hover_panel()` to assign to `self.hover_panel` instead of `self._hover_panel`.

- [ ] **Step 4: Run integration tests**

```powershell
cd ui && pytest -m "unit or integration" -q
```
Expected: all tests pass. The application should launch without errors.

- [ ] **Step 5: Commit all changes from Tasks 1–5**

```powershell
git add ui/src/fractal_studio/ui/sections/panel_state.py
git add ui/src/fractal_studio/ui/sections/state.py
git add ui/src/fractal_studio/main_window_factory.py
git add ui/src/fractal_studio/main_window.py
git add ui/src/fractal_studio/ui/sections/adapters/base.py
git add ui/src/fractal_studio/ui/sections/mediator.py
git commit -m "refactor: single-pass construction root; MainWindowSectionsState becomes plain container"
```

---

## Self-Review

**Spec coverage:**
- `bind()` deleted: Task 2 ✓
- `attach_context()` replaced by `initialize_sections()` (layout only): Task 5 ✓
- Panel states receive `on_status` instead of `owner: MainWindow`: Task 1 ✓
- Panel states lose `sections_state` bag dependency: Task 1 ✓
- Factory builds everything in one pass: Task 3 ✓
- `MainWindowSectionsState` is a plain container: Task 2 ✓
- `validate()` uses `dataclasses.fields()`: Task 2 ✓
- Adapters built from panel states not from MainWindow: Task 4 ✓

**Placeholder scan:** Tasks 1 and 5 instruct the implementer to read the full file before editing because the body of panel state methods (especially those using `self._owner`) cannot be shown in full without reproducing hundreds of lines. The new constructor signatures are fully specified; the internal method body changes follow a clear mechanical rule (replace `self._owner.statusBar().showMessage(x)` with `if self._on_status: self._on_status(x)`).

**Type consistency:** `on_status: Callable[[str], None]` used consistently across all panel state constructors and the factory.
