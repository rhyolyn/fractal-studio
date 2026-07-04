# Review-06: Wiring-Layer Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written.

**Goal:** Make misconfiguration of the panel-wiring layer fail loudly at startup instead of degrading into silent no-ops, and delete the pure parameter-forwarding coordinator layers. This is the structural change that prevents the next "Save JSON"-class bug.

**Architecture:** Three phases. **Phase A** collapses the two pass-through coordinators (`PalettePanelCoordinator` → callers use `PaletteWorkflowService` directly; `FavoritesWorkflowCoordinator` → callers use `FavoritesController` directly, with the six restore lambdas replaced by a `FavoriteRestoreTarget` protocol). **Phase B** makes all `panel_state.py` collaborators required constructor arguments and deletes every `if x is None: return` wiring guard. **Phase C** promotes the private scheduler slot to public API. The two setter-based getters that break the genuine viewport↔export construction cycle are kept but become documented and required-after-construction (validated).

**Tech Stack:** Python 3.12, PySide6 ≥ 6.8, pytest.

**Recommended model:** Claude Fable 5 (Opus 4.8 acceptable). *Reasoning:* this is the one plan requiring real judgment — it rewrites constructors and call chains across ~14 files, must hold the whole wiring graph in context, and will hit test fallout that needs case-by-case decisions (fakes vs. real collaborators). A weaker model will "fix" failing tests by re-adding Optional guards, which defeats the plan's purpose. The reviewing agent (if using subagent-driven development) should explicitly reject any reintroduced `| None = None` wiring parameter.

**Dependencies:** review-01, review-03, and review-04 must be merged first (review-01 touches files rewritten here; review-04 relocates the tests rewritten here; review-03's guards police these edits). review-05 recommended first but not required.

## Decisions made for you (owner may veto asynchronously)

1. **Coordinators collapsed:** only `PalettePanelCoordinator` and `FavoritesWorkflowCoordinator` — both are pure forwarding. `ThemeWorkflowCoordinator`, `SettingsDialogCoordinator`, `WindowStartupCoordinator`, `FavoritesPanelCoordinator`, `ExportPanelCoordinator`, `SidebarWiringCoordinator`, `PalettePreviewCoordinator` are **out of scope** — they hold real behavior (dialog lifecycle, nonlocal theme state, row construction/selection).
2. **Restore callbacks become a protocol:** `FavoritesController.restore_snapshot(snapshot, target)` where `target: FavoriteRestoreTarget` — replaces six positional lambdas. Save keeps explicit data arguments (it is already mostly data).
3. **The viewport↔export cycle stays setter-based** (`set_viewport_getter` / `set_aspect_ratio_mode_getter`): breaking it properly requires moving aspect-ratio ownership, a larger design change than this plan should carry. The setters become mandatory: `MainWindowSectionsState.validate()` now also checks they were called.
4. **AGENTS.md conflict noted per its own instructions:** AGENTS.md prefers ≤2 parameters per function. Several constructors here legitimately need 4-7 collaborators; injected-dependency constructors are the accepted exception. Do not invent parameter objects just to hit the count.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — especially "Architecture Principles" and "Error Handling" ("Keep the happy path simple… do not hide important failure modes"). The C++/Unreal sections do not apply.
2. `ui/src/fractal_studio/ui/sections/panel_state.py` — all six classes, in full.
3. `ui/src/fractal_studio/main_window_factory.py` — the whole composition root.
4. `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py`, `ui/src/fractal_studio/application/workflows/favorites_workflow_coordinator.py`, `ui/src/fractal_studio/application/controllers/favorites_controller.py`.

## Global Constraints

- **No wiring parameter may be `| None = None` after this plan** (widget slots that are genuinely populated later — `self.editor`, `self.viewport`, `self.export_combo`, etc. — stay `| None`; those are runtime state, not wiring).
- UI-only mode (backend absent) must keep working.
- Full suite green at every commit; run `..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q` from `ui/` before each commit.
- Startup smoke tests (`ui/tests/test_startup_smoke.py`) are the safety net for the factory — run them after every factory edit.
- Commit style: conventional commits.

---

## Phase A — collapse pass-through coordinators

### Task A1: Delete `PalettePanelCoordinator`; call `PaletteWorkflowService` directly

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (`MainWindowColormapState`)
- Modify: `ui/src/fractal_studio/main_window_factory.py`
- Delete: `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py`
- Modify: `ui/src/fractal_studio/application/coordinators/__init__.py` (remove export if listed)
- Modify tests: `ui/tests/test_palette_workflows.py` (`TestPalettePanelCoordinator` cases move to service-level or state-level equivalents)

**Interfaces:**
- Consumes: `PaletteWorkflowService.save_palette_json(path, backend, control_points, palette_size, set_status) -> bool`, `.load_palette_json(path, backend, set_control_points, set_status) -> bool`, `.export_legacy_map(path, backend, control_points, legacy_palette_size, set_status) -> bool` (all exist, unchanged).
- Produces: `MainWindowColormapState` constructor takes `palette_service: PaletteWorkflowService` instead of `palette_panel: PalettePanelCoordinator`.

- [ ] **Step 1: Write the failing test** — in `ui/tests/test_palette_workflows.py`, add a state-level delegation test (integration marker; mirror the RecordingPalettePanel pattern from `ui/tests/test_colormap_panel_state.py` introduced by review-01, but recording `PaletteWorkflowService`-shaped calls):

```python
class RecordingPaletteService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def save_palette_json(self, **kwargs) -> bool:
        self.calls.append(("save_palette_json", kwargs))
        return True

    def load_palette_json(self, **kwargs) -> bool:
        self.calls.append(("load_palette_json", kwargs))
        return True

    def export_legacy_map(self, **kwargs) -> bool:
        self.calls.append(("export_legacy_map", kwargs))
        return True
```

Test that `MainWindowColormapState(palette_service=RecordingPaletteService(), ...)` with a fake editor forwards `control_points` extracted from the editor (the None-editor early return moves into `panel_state`, which already checks `self.editor`).

- [ ] **Step 2: Implement** — in `MainWindowColormapState` (post-review-01 shape, post-Phase-B this constructor gets stricter; here just swap the collaborator):
  - Rename `_palette_panel` → `_palette_service`; type `PaletteWorkflowService`.
  - `save_palette_json` / `load_palette_json` / `export_legacy_map` bodies: add `if self.editor is None: return` at the top, then call the service with `control_points=self.editor.control_points` (save/export) or `set_control_points=self.editor.set_control_points` (load); all other arguments as before. The service's keyword names differ from the coordinator's (`editor=` disappears) — match the service signatures in Required Reading item 4.
  - Factory: delete `palette_panel = PalettePanelCoordinator(palette_service)`; pass `palette_service=palette_service` to `MainWindowColormapState`. Remove the import.
- [ ] **Step 3: Delete** `palette_panel_coordinator.py`; port `TestPalettePanelCoordinator`'s meaningful cases (None-editor early return) to the state-level test; delete the rest.
- [ ] **Step 4: Run full suite; commit** `refactor: drop PalettePanelCoordinator pass-through; colormap state calls PaletteWorkflowService directly`.

### Task A2: Delete `FavoritesWorkflowCoordinator`; introduce `FavoriteRestoreTarget`

**Files:**
- Modify: `ui/src/fractal_studio/application/controllers/favorites_controller.py`
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (`MainWindowFavoritesState`)
- Modify: `ui/src/fractal_studio/main_window_factory.py`
- Delete: `ui/src/fractal_studio/application/workflows/favorites_workflow_coordinator.py`
- Modify tests: `ui/tests/test_favorites_controllers.py`

**Interfaces:**
- Produces (in `favorites_controller.py`):

```python
class FavoriteRestoreTarget(Protocol):
    def apply_viewport_state(self, state: ViewportState, rerender: bool) -> None: ...
    def apply_control_points(self, points: list[tuple[int, int, int]]) -> None: ...
    def apply_palette(self, palette: list[tuple[int, int, int]]) -> None: ...
    def apply_params(self, params: ParamsState) -> None: ...
    def set_cycle_active(self, active: bool) -> None: ...
    def apply_aspect_ratio_mode(self, mode: str) -> None: ...
```

and `FavoritesController.restore_snapshot(self, snapshot: FavoriteSnapshot, target: FavoriteRestoreTarget) -> None` with the same ordering semantics as today:

```python
    def restore_snapshot(self, snapshot: FavoriteSnapshot, target: FavoriteRestoreTarget) -> None:
        target.apply_viewport_state(snapshot.viewport, False)
        target.apply_aspect_ratio_mode(snapshot.aspect_ratio_mode)
        if snapshot.control_points:
            target.apply_control_points(snapshot.control_points)
        if snapshot.palette and len(snapshot.control_points) < 4:
            target.apply_palette(snapshot.palette)
        target.apply_params(ParamsState.from_viewport_state(snapshot.viewport, cycle_active=False))
        target.set_cycle_active(False)
        target.apply_viewport_state(snapshot.viewport, True)
```

- Deletes: `FavoritesController.save_favorite` (the 11-callable variant — orchestration moves to `MainWindowFavoritesState`, which owns all the pieces anyway). Keep `build_favorite_name`, `build_snapshot`, `persist_favorites`, `load_favorites`, `load_favorite_row`, `update_palette_previews`.

- [ ] **Step 1: Write the failing tests** — add to `ui/tests/test_favorites_controllers.py`:

```python
def _viewport_state() -> ViewportState:
    return ViewportState(
        formula="standard", center_x=-0.5, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )


class RecordingRestoreTarget:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def apply_viewport_state(self, state, rerender: bool) -> None:
        self.calls.append(f"apply_viewport_state(rerender={rerender})")

    def apply_control_points(self, points) -> None:
        self.calls.append("apply_control_points")

    def apply_palette(self, palette) -> None:
        self.calls.append("apply_palette")

    def apply_params(self, params) -> None:
        self.calls.append("apply_params")

    def set_cycle_active(self, active: bool) -> None:
        self.calls.append(f"set_cycle_active({active})")

    def apply_aspect_ratio_mode(self, mode: str) -> None:
        self.calls.append("apply_aspect_ratio_mode")


@pytest.mark.unit
def test_restore_snapshot_order_with_control_points() -> None:
    controller = FavoritesController()
    snapshot = FavoriteSnapshot(
        favorite_id="id", saved_at="", aspect_ratio_mode="square", name="n",
        viewport=_viewport_state(), control_points=[(0, 0, 0)] * 4,
        palette=[(1, 2, 3)], thumbnail="",
    )
    target = RecordingRestoreTarget()
    controller.restore_snapshot(snapshot, target)
    assert target.calls == [
        "apply_viewport_state(rerender=False)",
        "apply_aspect_ratio_mode",
        "apply_control_points",
        "apply_params",
        "set_cycle_active(False)",
        "apply_viewport_state(rerender=True)",
    ]


@pytest.mark.unit
def test_restore_snapshot_applies_palette_only_when_under_four_points() -> None:
    controller = FavoritesController()
    snapshot = FavoriteSnapshot(
        favorite_id="id", saved_at="", aspect_ratio_mode="square", name="n",
        viewport=_viewport_state(), control_points=[(0, 0, 0)],
        palette=[(1, 2, 3)], thumbnail="",
    )
    target = RecordingRestoreTarget()
    controller.restore_snapshot(snapshot, target)
    assert "apply_palette" in target.calls
```

Run — expected FAIL: `restore_snapshot` today takes six callables, not a target object. Then port the remaining `TestFavoritesWorkflowCoordinator` behavioral cases (name uniqueness, delete-persists) to controller-level tests and delete the cases that only asserted parameter forwarding.
- [ ] **Step 2: Implement the controller change** (code above).
- [ ] **Step 3: Rewrite `MainWindowFavoritesState.save_favorite`, `delete_selected_favorite`, `activate_favorite_row`** to call the controller/panel-coordinator directly:

```python
    def save_favorite(self) -> None:
        viewport = self._viewport_getter()
        if viewport is None:
            return
        editor = self._editor_getter()
        state = viewport.to_state()
        name = self._favorites_controller.build_favorite_name(
            state, {f.name for f in self.favorites}, datetime.datetime.now
        )
        snapshot = self._favorites_controller.build_snapshot(
            viewport_state=state,
            palette=list(viewport.palette()),
            control_points=list(editor.control_points) if editor is not None else [],
            aspect_ratio_mode=self._aspect_ratio_mode_getter(),
            name=name,
            thumbnail=encode_pixmap(viewport.grab()),
        )
        self.favorites.append(snapshot)
        self.add_favorite_row(snapshot)
        self._favorites_controller.persist_favorites(self.favorites, self._favorites_repo.save)
        self._on_status(f"Saved favorite: {snapshot.name}")
```

```python
    def delete_selected_favorite(self) -> None:
        self.selected_row = self._favorites_panel.delete_selected(
            selected_row=self.selected_row,
            rows=self.fav_rows,
            favorites=self.favorites,
            scroll_layout=self.fav_scroll_layout,
        )
        if self.selected_row is None:
            self._favorites_controller.persist_favorites(self.favorites, self._favorites_repo.save)
```

For `activate_favorite_row`, define a small adapter in `panel_state.py` implementing `FavoriteRestoreTarget` over the getters (viewport/editor/preview/params panel), then:

```python
class _FavoriteRestoreAdapter:
    def __init__(self, *, viewport, params_panel, editor, preview_palette, apply_aspect_ratio_mode) -> None:
        self._viewport = viewport
        self._params_panel = params_panel
        self._editor = editor
        self._preview_palette = preview_palette
        self._apply_aspect_ratio_mode = apply_aspect_ratio_mode

    def apply_viewport_state(self, state, rerender: bool) -> None:
        if self._viewport is not None:
            self._viewport.apply_state(state, rerender=rerender)

    def apply_control_points(self, points) -> None:
        if self._editor is not None:
            self._editor.set_control_points(points)

    def apply_palette(self, palette) -> None:
        if self._viewport is not None:
            self._viewport.set_palette(palette)
        if self._preview_palette is not None:
            self._preview_palette.set_palette(palette)

    def apply_params(self, params) -> None:
        if self._params_panel is not None:
            self._params_panel.apply_state(params)

    def set_cycle_active(self, active: bool) -> None:
        if self._viewport is not None:
            self._viewport.set_cycle_active(active)

    def apply_aspect_ratio_mode(self, mode: str) -> None:
        self._apply_aspect_ratio_mode(mode)
```

(The None checks here are legitimate — widgets are runtime state, not wiring.) `activate_favorite_row` builds the adapter from its getters and calls `self._favorites_controller.load_favorite_row(row=row, favorites=self.favorites, rows=self.fav_rows, restore_snapshot=lambda snap: self._favorites_controller.restore_snapshot(snap, adapter), select_row=self.select_favorite_row, show_status=self._on_status)`.

- [ ] **Step 4:** Factory: remove `FavoritesWorkflowCoordinator` construction/import; `MainWindowFavoritesState` loses its `favorites_workflow` parameter. Delete `favorites_workflow_coordinator.py` and its `__init__.py` export; `MainWindow.initialize_sections` loses the `favorites_workflow` parameter (update `main_window.py` and the factory call).
- [ ] **Step 5:** Full suite + startup smoke tests; commit `refactor: fold FavoritesWorkflowCoordinator into controller + panel state; restore via FavoriteRestoreTarget protocol`.

---

## Phase B — required collaborators, no silent no-ops

### Task B1: Harden all six panel-state constructors

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (all six classes)
- Modify: `ui/src/fractal_studio/main_window_factory.py` (only if any call site omitted an argument — it shouldn't)
- Modify tests: every test constructing a panel-state class with partial arguments
- Test: `ui/tests/test_panel_state_wiring.py` (new)

**The transformation, applied uniformly** (shown for `MainWindowSidebarState`; repeat for all six):

```python
class MainWindowSidebarState:
    def __init__(
        self,
        *,
        sidebar_wiring: SidebarWiringCoordinator,
        viewport_getter: Callable[[], FractalViewportWidget | None],
        settings_service: SettingsWorkflowService,
        backend_loaded_getter: Callable[[], bool],
        backend_available_getter: Callable[[], bool],
    ) -> None:
        self._sidebar_wiring = sidebar_wiring
        self._viewport_getter = viewport_getter
        self._settings_service = settings_service
        self._backend_loaded_getter = backend_loaded_getter
        self._backend_available_getter = backend_available_getter
        self.params_panel: FractalParamsPanel | None = None
        self.backend_state_label: QLabel | None = None
```

and every method guard of the form

```python
        if self._sidebar_wiring is None or self._viewport_getter is None:
            return
```

is deleted. **Keep** guards on runtime widget state (`self.params_panel is None`, `self.editor is None`, `viewport is None` after calling a getter, `self.fav_scroll_layout is None`) — those are legitimately not-yet-built or absent. The distinction: *constructor-injected collaborator → required, no guard; widget slot populated during `build_*` → stays optional with guard.*

Per-class notes:
- `MainWindowViewportState`: `controller`, `export_panel`, `refresh_export_presets` required.
- `MainWindowColormapState`: `palette_service`, `backend`, `on_status`, `legacy_palette_size_getter`, `palette_size_getter` required. `self._on_status if self._on_status is not None else lambda _: None` expressions collapse to `self._on_status`.
- `MainWindowPaletteState`: `palette_preview`, `backend`, `legacy_palette_size_getter`, `editor_getter` required.
- `MainWindowFavoritesState`: all constructor collaborators required (post-A2 list: `favorites_controller`, `favorites_panel`, `favorites_repo`, `on_status`, `hover_panel_getter`, `viewport_getter`, `params_panel_getter`, `editor_getter`, `preview_palette_getter`, `apply_aspect_ratio_mode`, `aspect_ratio_mode_getter`).
- `MainWindowExportState`: `export_panel`, `controller`, `on_status` required; `viewport_getter`/`aspect_ratio_mode_getter` remain setter-injected (the documented cycle) — see Task B2.

- [ ] **Step 1: Write the failing fail-fast test** — `ui/tests/test_panel_state_wiring.py`:

```python
from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.integration

from fractal_studio.ui.sections.panel_state import MainWindowSidebarState  # noqa: E402


class TestPanelStateWiringIsRequired(unittest.TestCase):
    def test_sidebar_state_rejects_missing_collaborators(self) -> None:
        with self.assertRaises(TypeError):
            MainWindowSidebarState()  # type: ignore[call-arg]
```

Add one such test per hardened class (six total, same shape).

- [ ] **Step 2:** Run — currently these FAIL (construction succeeds today). Implement the transformation class by class; after each class, run the full suite and fix test constructions by supplying fakes (reuse the recording fakes from `tests/support.py` and the plan-01/A1 test files; add tiny fakes to `support.py` when missing). **Do not** satisfy a failing test by re-adding a default.
- [ ] **Step 3:** Run startup smoke tests (`tests/test_startup_smoke.py`) — the factory must still construct everything.
- [ ] **Step 4:** Commit per class or per pair: `refactor: require <X> collaborators at construction; remove silent no-op guards`.

### Task B2: Validate the two setter-injected getters

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (`MainWindowExportState`)
- Modify: `ui/src/fractal_studio/ui/sections/state.py` (`MainWindowSectionsState.validate`)
- Test: extend `ui/tests/test_panel_state_wiring.py`

- [ ] **Step 1: Failing test** — add to `ui/tests/test_panel_state_wiring.py` (the `validate()` loop only checks fields for `None`, so `SimpleNamespace()` stands in for the other five states):

```python
import types

from fractal_studio.ui.sections.panel_state import MainWindowExportState  # noqa: E402
from fractal_studio.ui.sections.state import MainWindowSectionsState  # noqa: E402


def _export_state_without_cycle_getters() -> MainWindowExportState:
    return MainWindowExportState(
        export_panel=object(), controller=object(), on_status=lambda _m: None
    )


class TestExportCycleGettersAreValidated(unittest.TestCase):
    def test_validate_rejects_unbound_export_getters(self) -> None:
        dummy = types.SimpleNamespace()
        sections_state = MainWindowSectionsState(
            viewport=dummy, sidebar=dummy, palette=dummy,
            colormap=dummy, favorites=dummy,
            export=_export_state_without_cycle_getters(),
        )
        with self.assertRaises(RuntimeError):
            sections_state.validate()

    def test_validate_passes_once_getters_are_bound(self) -> None:
        dummy = types.SimpleNamespace()
        export_state = _export_state_without_cycle_getters()
        export_state.set_viewport_getter(lambda: None)
        export_state.set_aspect_ratio_mode_getter(lambda: "square")
        sections_state = MainWindowSectionsState(
            viewport=dummy, sidebar=dummy, palette=dummy,
            colormap=dummy, favorites=dummy, export=export_state,
        )
        sections_state.validate()  # must not raise
```

- [ ] **Step 2: Implement** — in `MainWindowExportState`, initialize `self._viewport_getter: Callable[[], FractalViewportWidget | None] | None = None` (setter-injected), and add:

```python
    def assert_wired(self) -> None:
        if self._viewport_getter is None or self._aspect_ratio_mode_getter is None:
            raise RuntimeError(
                "MainWindowExportState: set_viewport_getter/set_aspect_ratio_mode_getter "
                "must be called before use (viewport<->export construction cycle)."
            )
```

In `MainWindowSectionsState.validate()` add `self.export.assert_wired()` after the existing None-field loop. Remove the `if ... is None: return` guards inside `MainWindowExportState` methods that referenced these two getters (validate() now guarantees them; a genuine `viewport is None` runtime check stays where the getter can return None).

- [ ] **Step 3:** Full suite; commit `feat: validate() now fails fast when export state's cycle getters are unbound`.

---

## Phase C — public scheduler slot

### Task C1: Promote `_on_render_ready`

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (`MainWindowViewportState._on_render_ready` → `on_render_ready`)
- Modify: `ui/src/fractal_studio/main_window_factory.py` (line ~178: `render_scheduler.render_ready.connect(viewport_state.on_render_ready)`)
- Modify tests: grep `_on_render_ready` and update references.

- [ ] **Step 1:** Rename method (keep body identical), update the factory connect call and any tests (`grep -rn "_on_render_ready" ui/`).
- [ ] **Step 2:** Full suite; commit `refactor: make viewport render-ready handler public API`.

---

## Final verification

- [ ] `..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q` — green, count matches the review-04 baseline plus tests added by this plan.
- [ ] `grep -rn "is None or self\._" ui/src/fractal_studio/ui/sections/panel_state.py` — every remaining match must be a *widget-slot* guard, not a wiring guard. List the survivors in the PR description with one-line justifications.
- [ ] Launch the app in UI-only mode (`fractal-studio` without the Rust core) — all panels build, favorites save/load/delete work, no traceback.

## Done criteria

- Constructing any panel-state class without its collaborators raises `TypeError` at startup; `validate()` catches unbound cycle getters.
- `PalettePanelCoordinator` and `FavoritesWorkflowCoordinator` no longer exist; no behavior lost (restore ordering and name-uniqueness tests prove it at controller level).
- No new `| None = None` wiring parameters anywhere in `panel_state.py`.
