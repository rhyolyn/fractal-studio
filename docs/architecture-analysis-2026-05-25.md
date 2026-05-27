# Fractal Studio UI Architecture Analysis (2026-05-25)

## Scope

Reviewed code:
- `ui/src/fractal_studio/main_window.py`
- `ui/src/fractal_studio/viewport.py`
- `ui/src/fractal_studio/editor.py`
- `ui/src/fractal_studio/backend.py`
- `ui/src/fractal_studio/theme.py`
- `ui/src/fractal_studio/app.py`

Reference standards applied:
- Repository guidance in `AGENT.md` at repo root (`c:/git/graphics/AGENT.md`): SOLID, single responsibility, readability, decomposition over duplication.
- Project-level guidance in `CLAUDE.md` (architecture-first, direct risk assessment).

Note:
- The requested path `c:/users/rhyol/agent.md` was not present in this environment.

## Executive Summary

The current UI implementation is functional and recently improved, but architecture cleanliness is limited by concentration of responsibilities and cross-component state reach-through.

Top issues:
1. `MainWindow` is a god object with UI composition, orchestration, persistence, serialization, export, and settings concerns.
2. Multiple modules mutate private fields of other modules directly, creating fragile coupling and bypassing contracts.
3. Favorites/settings persistence is now versioned and service-backed, but migration policy/diagnostics are still incomplete.
4. View/logic boundaries are blurred in viewport/editor widgets.

Overall cleanliness rating:
- Readability: Medium
- SRP adherence: Low-Medium
- Duplication control: Medium
- Change safety: Medium-Low

## Findings

### 1) MainWindow Is a God Object
Severity: Critical

Current status: In progress (partially mitigated, not resolved)

Why this is bad:
- One class owns too many responsibilities: layout construction, event wiring, rendering export, favorites CRUD, settings dialog orchestration, persistence I/O, theme transitions, and state synchronization.
- This amplifies regression risk and makes targeted changes expensive.

What improved already:
- Settings/favorites file I/O has been extracted into dedicated repository services.
- State transfer logic now uses typed contracts (`ViewportState`, `ParamsState`, `FavoriteSnapshot`).

What still keeps this as a god object:
- `MainWindow` still combines large UI assembly (`_build_*` family), export orchestration, favorites row orchestration/load flow, palette import/export actions, and settings dialog flow.

Evidence:
- `MainWindow` starts at `ui/src/fractal_studio/main_window.py:341`.
- UI construction methods spread across `_build_*` methods: `:386`, `:401`, `:425`, `:439`, `:467`, `:498`, `:516`, `:554`, `:578`, `:729`.
- Persistence now delegates to repositories but orchestration is still in class: `_persist_favorites` `:903`, `_load_favorites_from_disk` `:914`, `_persist_settings` `:1024`, `_load_settings_from_disk` `:1027`.
- Export logic is still embedded in `_export_render` `:697`.
- Favorites load/sync orchestration is still embedded: `_load_favorite_row` `:856`, `_sync_params_panel_from_favorite` `:897`.

Recommendation:
- Split into focused collaborators:
  - `WorkspaceViewBuilder`
  - `FavoritesService`
  - `SettingsService`
  - `ExportService`
  - `MainWindowController` (wiring only)

---

### 2) Private State Reach-Through Across Components
Severity: Critical

Why this is bad:
- `MainWindow` reads/writes internal fields of `FractalViewportWidget` and `FractalParamsPanel` directly.
- This bypasses invariants and creates hidden temporal coupling.

Evidence:
- `_export_render` accesses viewport internals directly (`vp._formula`, `vp._center_x`, etc.) at `ui/src/fractal_studio/main_window.py:705-719`.
- `_load_favorite_row` directly mutates viewport internals (`vp._*`) at `:865-877`.
- `_sync_params_panel_from_favorite` writes private widget internals (`p._formula_combo`, `p._set_*`) at `:924-973`.

Recommendation:
- Introduce typed state transfer objects and explicit APIs:
  - `ViewportState` (`to_state`, `apply_state`)
  - `ParamsState` (`to_state`, `apply_state`)
- Remove all direct `_private` field access outside owning class.

---

### 3) Dict-Based Schema Without Strong Contract for Favorites/Settings
Severity: High

Why this is bad:
- Serialization uses ad-hoc dict keys and manual conversion/parsing.
- Increases typo risk, migration friction, and inconsistent defaults.

Evidence:
- Typed models now exist in `ui/src/fractal_studio/state.py`: `UiSettings` `:8`, `ViewportState` `:25`, `FavoriteSnapshot` `:83`.
- `MainWindow` now uses those models in save/load paths: `_save_favorite` `ui/src/fractal_studio/main_window.py:804`, `_load_favorite_row` `:863`, `_load_favorites_from_disk` `:981`, `_persist_settings` `:1095`, `_load_settings_from_disk` `:1100`.
- Remaining gap: persistence still physically owned by `MainWindow` and has no explicit schema version/migration plan.

Recommendation:
- Keep the new dataclass model layer, then finish the persistence contract:
  - add schema version tags for favorites/settings payloads
  - add migration adapters for backward compatibility
  - move file I/O ownership into a dedicated persistence service

---

### 4) UI and Domain Logic Mixed in Rendering Widgets
Severity: High

Why this is bad:
- `FractalViewportWidget` mixes rendering orchestration, interaction logic, default formula behavior, and status text formatting.
- `ColorCubeEditor` similarly combines rendering caches, input handling, palette generation triggers, and status text.

Evidence:
- `FractalViewportWidget` starts at `ui/src/fractal_studio/viewport.py:23`; `_rerender` at `:231` is large and stateful.
- Formula/mode behavior is embedded in `set_formula` `:109`, `set_mode` `:119`, `set_power` `:127`.
- `ColorCubeEditor` starts at `ui/src/fractal_studio/editor.py:78`; event + palette refresh coupling in `mousePressEvent` `:127`, `mouseMoveEvent` `:146`, `_refresh_palette` `:190`.

Recommendation:
- Move domain behavior into services:
  - `FractalViewStateController`
  - `PaletteEditController`
- Keep widgets as view/input surfaces with thin command calls.

---

### 5) Theme Application Uses Large Global Stylesheet and Runtime Re-Polish
Severity: Medium

Why this is bad:
- Global stylesheet in one large string is brittle and hard to evolve.
- Dynamic updates rely on manual unpolish/polish for some widgets only.

Evidence:
- `build_stylesheet` in `ui/src/fractal_studio/theme.py:126`.
- Runtime dynamic re-style in `_apply_theme_to_dynamic_widgets` at `ui/src/fractal_studio/main_window.py:1093`.

Recommendation:
- Introduce style sections or tokenized style templates per feature area.
- Add a central `ThemeController` to manage re-application strategy and widget registration.

---

### 6) Backend Facade Is Broad and Low-Cohesion
Severity: Medium

Why this is bad:
- `CoreBackend` exposes many pass-through methods with broad API surface.
- Harder to reason about ownership and test narrower concerns.

Evidence:
- `CoreBackend` at `ui/src/fractal_studio/backend.py:35` with multiple rendering and export methods.

Recommendation:
- Split facade interfaces:
  - `RenderBackend`
  - `PaletteBackend`
  - `ProfileBackend`
- Keep composition in one adapter factory.

---

### 7) Error Handling Is Mostly Silent on Persistence Paths
Severity: Medium

Why this is bad:
- Some failures become silent fallback behavior, reducing diagnosability.
- Acceptable for UX fallback in some paths, but currently too broad in places.

Evidence:
- Favorites load silently returns empty list on parse failure at `ui/src/fractal_studio/main_window.py:981-989`.
- Settings load similarly falls back without reporting at `ui/src/fractal_studio/main_window.py:1100-1106`.

Recommendation:
- Keep fallback, but add structured diagnostics (status message/log hook).

---

### 8) Test Suite Still Has White-Box Coupling Hotspots
Severity: Medium-Low

Why this is bad:
- Many tests assert private UI fields and internals, making refactors noisier.
- Good for fast regression coverage, but expensive for architectural cleanup.

Evidence:
- `ui/tests/test_ui_redesign.py` uses several private fields (`_...`) and internal methods.

Recommendation:
- Gradually migrate critical tests to behavior-level assertions and public API/state effects.

## Recommended Remediation Order

## Progress Update (2026-05-25)

### Live Verification Status (while testing)

Automated checks:
- UI regression suite: passing (`55 passed`).

Manual validation checklist:
- [ ] Settings theme preview/apply/revert behavior
- [ ] Favorites save/load/delete and thumbnail hover details
- [ ] Export preset/custom resolution path and saved image output
- [ ] Aspect ratio switching and viewport sizing behavior
- [ ] Startup with existing legacy settings/favorites files

Testing notes:
- Record any regressions against these areas before starting decomposition slice 7.
- If manual testing stays clean, proceed with trimming remaining widget helper wrappers.

Completed since this analysis was written:
- Phase 1 step 1 is done: typed state objects were introduced and wired into favorites/settings paths.
- Implemented in `ui/src/fractal_studio/state.py` and integrated in `ui/src/fractal_studio/main_window.py`.
- Phase 1 step 2 is done: explicit `to_state()` / `apply_state()` APIs were added to viewport and params panel.
- `MainWindow` export/favorite restore paths were switched to those APIs, reducing direct private-field mutation.
- Phase 1 step 3 is done: versioned persistence wrappers + migration-safe adapters were added for settings/favorites.
- Read-old/write-new compatibility tests were added and passing.
- Phase 2 decomposition slice 1 is done: settings/favorites persistence I/O moved out of `MainWindow` into dedicated repository services.
- `MainWindow` now delegates persistence to services and remains focused on orchestration/view wiring.
- Phase 2 decomposition slice 2 is done: export orchestration moved to `ExportService`, and favorite restore/sync orchestration moved to `FavoritesController`.
- `MainWindow` now delegates high-churn export/favorites workflows to dedicated collaborators.
- Phase 2 decomposition slice 3 is done: `_build_*` section assembly moved behind a dedicated `MainWindowSections` builder collaborator.
- `MainWindow` now delegates section construction and is further reduced toward composition/wiring responsibility.
- Phase 2 decomposition slice 4 is done: workflow orchestration moved behind a dedicated `MainWindowController` boundary.
- `MainWindow` now delegates export/favorites workflow methods through controller-level orchestration.
- Phase 2 decomposition slice 5 is done: aspect ratio/export preset transitions and settings dialog apply/revert flow moved behind `MainWindowController` orchestration.
- UI regression suite remains green after slice 5 (`55 passed`).
- Phase 2 decomposition slice 6 is done: palette import/export and legacy-map workflow moved behind `PaletteWorkflowService`.
- UI regression suite remains green after slice 6 (`58 passed`).
- Phase 3 slice 1 is done: viewport and editor domain behavior now delegates through dedicated controller helpers.
- UI regression suite remains green after slice 1 (`55 passed`).
- Phase 3 slice 2 is done: remaining thin widget helper wrappers were trimmed and the tests now target the controller boundary directly.
- UI regression suite remains green after slice 2 (`55 passed`).
- Phase 1 step 2 is done: startup diagnostics now surface legacy settings migrations in the status bar.
- Phase 2 decomposition slice 7 is done: remaining startup/theme/settings branching moved behind `SettingsWorkflowService`.
- UI regression suite remains green after slice 7 (`61 passed`).
- Phase 2 decomposition slice 8 is done: remaining `MainWindow` pass-through wrappers were removed.
- UI regression suite remains green after slice 8 (`61 passed`).
- Phase 2 decomposition slice 9 is done: favorite-name generation moved behind `FavoritesController`.
- UI regression suite remains green after slice 9 (`63 passed`).
- Phase 2 decomposition slice 10 is done: remaining favorite save/load orchestration and palette preview updates moved behind `FavoritesController`.
- UI regression suite remains green after slice 10 (`66 passed`).
- Phase 2 decomposition slice 11 is done: favorites persistence bridging moved behind `FavoritesController` and repository helpers.
- UI regression suite remains green after slice 11 (`71 passed`).
- Phase 2 decomposition slice 12 is done: residual `MainWindow` helper wrappers were trimmed where direct delegation provided the same behavior.
- UI regression suite remains green after slice 12 (`71 passed`).
- Diagnostics hardening slice 1 is done: settings/favorites fallback loads now emit narrow startup diagnostics instead of failing silently.
- UI regression suite remains green after diagnostics hardening slice 1 (`74 passed`).
- Behavior tests hardening slice 1 is done: export dimension selection tests now target `MainWindowController` behavior instead of private `MainWindow` method patching.
- UI regression suite remains green after behavior tests hardening slice 1 (`74 passed`).
- Behavior tests hardening slice 2 is done: params-panel interaction tests now use public widget interactions and behavior assertions instead of private slot invocation.
- UI regression suite remains green after behavior tests hardening slice 2 (`74 passed`).
- Behavior tests hardening slice 3 is done: favorites/thumbnail interaction tests now lean on row click/double-click behavior and style outcomes instead of private selection/load helpers.
- UI regression suite remains green after behavior tests hardening slice 3 (`74 passed`).
- Phase 1 policy slice 1 is done: legacy migration compatibility window and sunset criteria are now explicitly documented.
- Phase 1 gate slice 2 is done: a targeted manual smoke-test checklist gate is now required for persistence-adjacent refactors.
- Phase 3 cleanup slice 3 is done: params-panel formula/mode/coloring/reset decision logic moved behind a dedicated `ParamsPanelController` boundary.
- UI regression suite remains green after phase 3 cleanup slice 3 (`74 passed`).
- Phase 3 cleanup slice 4 is done: theme application now delegates through a dedicated `ThemeController`, and stylesheet assembly is split into smaller section builders.
- UI regression suite remains green after phase 3 cleanup slice 4 (`76 passed`).
- Behavior tests hardening slice 4 is done: editor interaction tests now assert click/drag outcomes and emitted status behavior instead of private controller/drag-state internals.
- UI regression suite remains green after behavior tests hardening slice 4 (`76 passed`).
- Behavior tests hardening slice 5 is done: appearance dialog and favorite-row tests now validate theme/hover behavior through public widget signals/events instead of private test hooks.
- UI regression suite remains green after behavior tests hardening slice 5 (`76 passed`).
- Phase 3 cleanup slice 6 is done: favorite-row hover metadata rendering and hover-panel positioning now delegate through a dedicated `FavoriteHoverPresenter`.
- UI regression suite remains green after phase 3 cleanup slice 6 (`78 passed`).
- Phase 3 cleanup slice 7 is done: favorite-row visual-state styling now delegates through a dedicated `FavoriteRowStylePresenter`.
- UI regression suite remains green after phase 3 cleanup slice 7 (`81 passed`).
- Behavior tests hardening slice 6 is done: favorite persistence interaction tests now use viewport public state/palette APIs instead of private viewport fields.
- UI regression suite remains green after behavior tests hardening slice 6 (`81 passed`).
- Phase 2 decomposition slice 13 is done: favorite-row panel lifecycle orchestration moved behind a dedicated `FavoritesPanelCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 13 (`84 passed`).
- Behavior tests hardening slice 7 is done: favorite-row panel lifecycle behavior now has focused coordinator-level tests.
- UI regression suite remains green after behavior tests hardening slice 7 (`84 passed`).
- Phase 2 decomposition slice 14 is done: startup status/diagnostics assembly moved behind `SettingsWorkflowService.startup_status`.
- UI regression suite remains green after phase 2 decomposition slice 14 (`85 passed`).
- Behavior tests hardening slice 8 is done: startup status composition behavior now has focused `SettingsWorkflowService` coverage.
- UI regression suite remains green after behavior tests hardening slice 8 (`85 passed`).
- Phase 2 decomposition slice 15 is done: export/aspect panel event orchestration moved behind a dedicated `ExportPanelCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 15 (`88 passed`).
- Behavior tests hardening slice 9 is done: export/aspect panel coordinator behavior now has focused unit coverage.
- UI regression suite remains green after behavior tests hardening slice 9 (`88 passed`).
- Phase 2 decomposition slice 16 is done: settings dialog open/apply flow now delegates through a dedicated `SettingsDialogCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 16 (`90 passed`).
- Behavior tests hardening slice 10 is done: settings dialog coordinator behavior now has focused unit coverage.
- UI regression suite remains green after behavior tests hardening slice 10 (`90 passed`).
- Phase 2 decomposition slice 17 is done: palette import/export panel workflow now delegates through a dedicated `PalettePanelCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 17 (`93 passed`).
- Behavior tests hardening slice 11 is done: palette panel coordinator behavior now has focused unit coverage.
- UI regression suite remains green after behavior tests hardening slice 11 (`93 passed`).
- Phase 2 decomposition slice 18 is done: sidebar params-panel ↔ viewport signal wiring now delegates through a dedicated `SidebarWiringCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 18 (`95 passed`).
- Behavior tests hardening slice 12 is done: sidebar wiring coordinator behavior now has focused unit coverage.
- UI regression suite remains green after behavior tests hardening slice 12 (`95 passed`).
- Phase 2 decomposition slice 19 is done: thumbnail encode/decode/placeholder helpers were extracted from `MainWindow` into a dedicated `thumbnail_utils` module.
- UI regression suite remains green after phase 2 decomposition slice 19 (`95 passed`).
- Behavior tests hardening slice 13 is done: thumbnail helper tests now target `thumbnail_utils` behavior instead of `MainWindow` private static methods.
- UI regression suite remains green after behavior tests hardening slice 13 (`95 passed`).
- Phase 2 decomposition slice 20 is done: unused residual `MainWindow` helper `_backend_state_text` was removed after backend status assembly delegation.
- UI regression suite remains green after phase 2 decomposition slice 20 (`95 passed`).
- Behavior tests hardening slice 14 is done: export/aspect panel tests now discover and validate UI behavior via widget contracts instead of `MainWindow` private field access.
- UI regression suite remains green after behavior tests hardening slice 14 (`95 passed`).
- Behavior tests hardening slice 15 is done: favorite persistence tests now save/load through UI interactions and widget discovery instead of direct `MainWindow` private favorites/combo fields.
- UI regression suite remains green after behavior tests hardening slice 15 (`95 passed`).
- Behavior tests hardening slice 16 is done: legacy/versioned favorites format tests now assert through repository/file payload boundaries instead of `MainWindow` private favorites storage.
- UI regression suite remains green after behavior tests hardening slice 16 (`95 passed`).
- Behavior tests hardening slice 17 is done: settings/theme persistence and no-persist assertions now target repository and coordinator boundaries instead of `MainWindow` private theme helper calls.
- UI regression suite remains green after behavior tests hardening slice 17 (`95 passed`).
- Behavior tests hardening slice 18 is done: the remaining editor cache-reuse white-box assertion was removed, keeping editor interaction coverage at the behavior boundary.
- UI regression suite remains green after behavior tests hardening slice 18 (`94 passed`).
- Phase 2 decomposition slice 21 is done: the redundant pre-assignment in `MainWindow._apply_aspect_ratio_mode` was removed.
- UI regression suite remains green after phase 2 decomposition slice 21 (`94 passed`).
- Phase 2 decomposition slice 22 is done: startup settings load, theme application, and startup-status composition were extracted behind `WindowStartupCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 22 (`96 passed`).
- Behavior tests hardening slice 19 is done: startup coordinator behavior now has focused coverage for versioned and legacy settings bootstrapping.
- UI regression suite remains green after behavior tests hardening slice 19 (`96 passed`).
- Phase 2 decomposition slice 23 is done: favorites save/load/delete guard orchestration and favorite-name bridging were extracted behind `FavoritesWorkflowCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 23 (`100 passed`).
- Behavior tests hardening slice 20 is done: favorites workflow coordinator behavior now has focused guard/orchestration coverage.
- UI regression suite remains green after behavior tests hardening slice 20 (`100 passed`).
- Phase 2 decomposition slice 24 is done: theme apply/persist bridging moved out of `MainWindow` into `ThemeWorkflowCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 24 (`102 passed`).
- Behavior tests hardening slice 21 is done: theme workflow coordinator behavior now has focused coverage for apply/persist and unchanged-theme paths.
- UI regression suite remains green after behavior tests hardening slice 21 (`102 passed`).
- Phase 2 decomposition slice 25 is done: favorite-row weakref callback wiring moved out of `MainWindow` into `FavoritesPanelCoordinator.build_row_with_callbacks`.
- UI regression suite remains green after phase 2 decomposition slice 25 (`104 passed`).
- Behavior tests hardening slice 22 is done: favorites panel coordinator now has focused callback-wiring coverage for live-owner and collected-owner paths.
- UI regression suite remains green after behavior tests hardening slice 22 (`104 passed`).
- Phase 2 decomposition slice 26 is done: colormap preview/control-summary callback ownership moved out of `MainWindow` into `PalettePreviewCoordinator`.
- UI regression suite remains green after phase 2 decomposition slice 26 (`106 passed`).
- Behavior tests hardening slice 23 is done: palette preview coordinator now has focused summary/delegation coverage.
- UI regression suite remains green after behavior tests hardening slice 23 (`106 passed`).
- Phase 2 decomposition slice 27 is done: favorite-row restore orchestration moved out of `MainWindow` into `FavoritesWorkflowCoordinator.load_favorite_row`.
- UI regression suite remains green after phase 2 decomposition slice 27 (`107 passed`).
- Behavior tests hardening slice 24 is done: favorites workflow coordinator now has focused load-row delegation coverage.
- UI regression suite remains green after behavior tests hardening slice 24 (`107 passed`).
- Phase 2 decomposition slice 28 is done: `MainWindow` export click flow now delegates directly to controller export rendering without the redundant `_export_render` pass-through helper.
- UI regression suite remains green after phase 2 decomposition slice 28 (`107 passed`).
- Phase 2 decomposition slice 29 is done: colormap button actions now invoke `PalettePanelCoordinator` directly from section wiring, removing redundant `MainWindow` palette pass-through helpers.
- UI regression suite remains green after phase 2 decomposition slice 29 (`107 passed`).
- Phase 2 decomposition slice 30 is done: `MainWindow` theme-apply pass-through wrapper was removed, with settings dialog theme callbacks now delegating directly through `ThemeWorkflowCoordinator` from `_open_settings`.
- UI regression suite remains green after phase 2 decomposition slice 30 (`107 passed`).

Removed from active queue:
- "Introduce typed state objects" (already completed).
- "State API enforcement" and the associated `_private` mutation removal in export/favorite load paths (already completed).
- "Versioned persistence contract" and compatibility test hardening (already completed).
- "MainWindow decomposition slice 1" for persistence extraction (already completed).
- "MainWindow decomposition slice 2" for export/favorites orchestration extraction (already completed).
- "MainWindow decomposition slice 3" for UI section builder extraction (already completed).
- "MainWindow decomposition slice 4" for controller orchestration extraction (already completed).
- "MainWindow decomposition slice 5" for remaining stateful helper extraction (already completed).
- "Palette workflow extraction" for palette JSON and legacy map operations (already completed).
- "Rendering/domain extraction slice 1" for viewport/editor controller extraction (already completed).
- "Rendering/domain extraction slice 2" for trimming remaining viewport/editor helper wrappers (already completed).
- "Add lightweight startup diagnostics when legacy payloads are auto-migrated in memory" (already completed).
- "MainWindow decomposition slice 7" for the remaining theme application and settings persistence helpers (already completed).
- "MainWindow decomposition slice 8" for the remaining `MainWindow` pass-through wrappers (already completed).
- "MainWindow decomposition slice 9" for the favorite-name generation helper (already completed).
- "MainWindow decomposition slice 10" for the remaining favorite save/load orchestration and palette preview update logic (already completed).
- "MainWindow decomposition slice 11" for the favorites persistence bridge (already completed).
- "MainWindow decomposition slice 12" for trimming residual helper wrappers in `MainWindow` (already completed).
- "Diagnostics hardening slice 1" for settings/favorites fallback observability (already completed).
- "Behavior tests hardening slice 1" for reducing private-method coupling in high-churn export tests (already completed).
- "Behavior tests hardening slice 2" for reducing private-slot coupling in params-panel interaction tests (already completed).
- "Behavior tests hardening slice 3" for reducing private-field coupling in favorites/thumbnail interaction tests (already completed).
- "Phase 1 policy slice 1" for documenting migration policy duration and sunset criteria (already completed).
- "Phase 1 gate slice 2" for adding a required manual smoke-test checklist gate after persistence-adjacent refactors (already completed).
- "Phase 3 cleanup slice 3" for trimming remaining widget-local params-panel logic into a controller boundary (already completed).
- "Phase 3 cleanup slice 4" for refactoring theme application into a dedicated controller boundary and smaller stylesheet sections (already completed).
- "Behavior tests hardening slice 4" for reducing editor interaction white-box coupling to private controller/drag-state internals (already completed).
- "Behavior tests hardening slice 5" for reducing appearance dialog/favorite-row white-box coupling in tests (already completed).
- "Phase 3 cleanup slice 6" for extracting favorite-row hover metadata/positioning into a dedicated presenter (already completed).
- "Phase 3 cleanup slice 7" for extracting favorite-row visual-state styling into a dedicated presenter (already completed).
- "Behavior tests hardening slice 6" for reducing favorite persistence test coupling to private viewport fields (already completed).
- "Phase 2 decomposition slice 13" for extracting favorite-row panel lifecycle orchestration into `FavoritesPanelCoordinator` (already completed).
- "Behavior tests hardening slice 7" for adding focused favorite-panel coordinator behavior coverage (already completed).
- "Phase 2 decomposition slice 14" for extracting startup status/diagnostics assembly into `SettingsWorkflowService.startup_status` (already completed).
- "Behavior tests hardening slice 8" for adding focused startup status composition coverage (already completed).
- "Phase 2 decomposition slice 15" for extracting export/aspect panel event orchestration into `ExportPanelCoordinator` (already completed).
- "Behavior tests hardening slice 9" for adding focused export/aspect coordinator behavior coverage (already completed).
- "Phase 2 decomposition slice 16" for extracting settings dialog open/apply flow into `SettingsDialogCoordinator` (already completed).
- "Behavior tests hardening slice 10" for adding focused settings dialog coordinator behavior coverage (already completed).
- "Phase 2 decomposition slice 17" for extracting palette import/export panel workflow into `PalettePanelCoordinator` (already completed).
- "Behavior tests hardening slice 11" for adding focused palette panel coordinator behavior coverage (already completed).
- "Phase 2 decomposition slice 18" for extracting sidebar params-panel ↔ viewport signal wiring into `SidebarWiringCoordinator` (already completed).
- "Behavior tests hardening slice 12" for adding focused sidebar wiring coordinator behavior coverage (already completed).
- "Phase 2 decomposition slice 19" for extracting thumbnail encode/decode/placeholder helpers into `thumbnail_utils` (already completed).
- "Behavior tests hardening slice 13" for shifting thumbnail helper tests to the `thumbnail_utils` behavior boundary (already completed).
- "Phase 2 decomposition slice 20" for trimming the unused `MainWindow._backend_state_text` helper after backend-status delegation (already completed).
- "Behavior tests hardening slice 14" for reducing export/aspect test coupling to `MainWindow` private fields via behavior-level widget discovery (already completed).
- "Behavior tests hardening slice 15" for reducing favorite persistence test coupling to `MainWindow` private favorites/combo fields via behavior-level UI interactions (already completed).
- "Behavior tests hardening slice 16" for reducing legacy/versioned favorites format test coupling to `MainWindow` private favorites storage (already completed).
- "Behavior tests hardening slice 17" for reducing settings/theme test coupling to `MainWindow` private theme helper calls (already completed).
- "Behavior tests hardening slice 18" for removing the remaining editor cache-reuse white-box assertion (already completed).
- "Phase 2 decomposition slice 21" for removing the redundant pre-assignment in `MainWindow._apply_aspect_ratio_mode` (already completed).
- "Phase 2 decomposition slice 22" for extracting startup settings load, theme application, and startup-status composition into `WindowStartupCoordinator` (already completed).
- "Behavior tests hardening slice 19" for adding focused `WindowStartupCoordinator` coverage (already completed).
- "Phase 2 decomposition slice 23" for extracting favorites action orchestration and naming bridge into `FavoritesWorkflowCoordinator` (already completed).
- "Behavior tests hardening slice 20" for adding focused `FavoritesWorkflowCoordinator` coverage (already completed).
- "Phase 2 decomposition slice 24" for extracting theme apply/persist bridging into `ThemeWorkflowCoordinator` (already completed).
- "Behavior tests hardening slice 21" for adding focused `ThemeWorkflowCoordinator` coverage (already completed).
- "Phase 2 decomposition slice 25" for extracting favorite-row weakref callback wiring into `FavoritesPanelCoordinator.build_row_with_callbacks` (already completed).
- "Behavior tests hardening slice 22" for adding focused callback-wiring coverage in `FavoritesPanelCoordinator` (already completed).
- "Phase 2 decomposition slice 26" for extracting colormap preview/control-summary callback ownership into `PalettePreviewCoordinator` (already completed).
- "Behavior tests hardening slice 23" for adding focused `PalettePreviewCoordinator` coverage (already completed).
- "Phase 2 decomposition slice 27" for extracting favorite-row restore orchestration into `FavoritesWorkflowCoordinator.load_favorite_row` (already completed).
- "Behavior tests hardening slice 24" for adding focused `FavoritesWorkflowCoordinator.load_favorite_row` coverage (already completed).
- "Phase 2 decomposition slice 28" for removing the redundant `MainWindow._export_render` pass-through helper (already completed).
- "Phase 2 decomposition slice 29" for removing redundant `MainWindow` palette action pass-through helpers (already completed).
- "Phase 2 decomposition slice 30" for removing redundant `MainWindow._apply_theme_name` pass-through wrapper (already completed).

### Phase 3 (Remaining cleanup)
1. Tighten behavior-level tests around the remaining high-churn widget interactions.

### Phase 1 (Highest ROI, Lowest Regret)
1. Enforce one targeted manual smoke-test checklist run after each persistence-adjacent refactor.

Expected impact:
- Biggest improvement in readability and change safety with manageable scope.

Phase 1 policy decision (2026-05-25):
- Compatibility mode: read old unversioned settings/favorites payloads and continue writing versioned payloads only.
- Compatibility window: keep read compatibility through 2026-12-31.
- User signaling: keep startup diagnostics for legacy/invalid payload fallback paths during the compatibility window.
- Compatibility test gate: legacy-read tests remain required in CI until the sunset date.
- Sunset criteria:
  1. The project reaches or passes 2026-12-31.
  2. Release notes include the deprecation policy before removal.
  3. A removal PR explicitly drops legacy adapters and updates tests/docs in the same change.

Execution order inside Phase 1:
1. Keep diagnostics hook for legacy payload loads (status/log signal).
2. Keep compatibility tests as a release gate.
3. Keep manual smoke checklist as a release gate for UI-affecting persistence changes.

Phase 1 manual smoke-test gate (required for persistence-adjacent refactors):
- Trigger condition: any change touching settings/favorites schema, repository load/save, migration adapters, or startup fallback behavior.
- Evidence requirement: record checklist results in the PR/task notes before merge.
- Checklist:
  1. Launch app with missing settings/favorites files; verify normal startup and no crash.
  2. Launch app with legacy unversioned settings/favorites files; verify load succeeds and status message indicates legacy handling.
  3. Launch app with invalid/corrupt settings/favorites files; verify fallback loads and diagnostics appear in startup status.
  4. Save new settings/favorites; verify persisted payloads are versioned.
  5. Reload app and verify saved settings/favorites round-trip correctly.
- Release gate rule: if any checklist item fails, do not merge persistence-adjacent changes.

### Phase 2 (Structural Decomposition)
1. Split `MainWindow` orchestration into services/controllers.
2. Keep UI composition methods but remove remaining domain logic from window class.
3. Add focused unit tests around `MainWindowController` state transitions and decision branches.
4. Trim residual helper wrappers in `MainWindow` where direct delegation can replace method indirection.

Expected impact:
- Major SRP improvement and lower regression surface.

### Phase 3 (Rendering/Theme Cleanliness)
1. Extract viewport/editor domain behavior into controllers.
2. Refactor theme system into smaller style sections and a dedicated controller.
3. Introduce diagnostics policy for persistence fallback paths.
4. Shift tests from white-box private-field assertions toward behavior-level contracts.

Expected impact:
- Better long-term maintainability and cleaner boundaries.

## Suggested Next Work Package

If only one package is started next, start with:
- "Phase 3 follow-up": tighten behavior-level tests around the remaining high-churn widget interactions.

Reason:
- Favorite-row hover metadata/positioning and visual-state styling are now extracted; the best ROI is hardening behavior-level coverage for remaining high-churn interaction paths.

## Resume Marker

Resume from here next session:
- Current checkpoint: Phase 1 policy slice 1, Phase 1 gate slice 2, Phase 2 decomposition slices 13-30, Phase 3 cleanup slices 3-4 and 6-7, plus behavior tests hardening slices 4-24 are complete.
- Next action: continue Phase 3 follow-up by tightening behavior-level tests for remaining high-churn widget interactions.
- Quick resume command: `cd c:/git/graphics/fractal-studio/ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py`
