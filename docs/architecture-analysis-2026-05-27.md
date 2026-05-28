# Fractal Studio — Architectural Analysis

**Date:** 2026-05-27  
**Scope:** Full Python UI layer (`fractal-studio/ui/`) + Rust bridge interface  
**Analyst:** Claude Sonnet 4.6

---

## 1. Executive Summary

Fractal Studio is a PySide6/Qt desktop application for interactive fractal rendering and palette authoring. It wraps a Rust rendering engine (`fractal_core`) via a lazy-loading Python bridge and presents a multi-panel workspace: fractal viewport, palette/colormap editor, parameter controls, export controls, and a favorites system.

The codebase has undergone substantial layering work and now shows a clearly intentional architecture — immutable data models, layered business logic, and a mediator/ports pattern for UI wiring. The main risks are in the UI layer: the sections/ports machinery is approaching critical mass, some layer boundaries are unclear, and the absence of the compiled Rust backend from the test environment creates gaps in functional coverage.

**Overall grade:** B+ — structurally sound, some complexity debt accumulating in the middle layers.

---

## 2. Package Structure

```
fractal_studio/
├── app.py                          Entry point (QApplication + factory)
├── main_window.py                  QMainWindow shell
├── main_window_factory.py          Dependency injection root
├── state.py                        Immutable domain objects
├── persistence.py                  JSON repositories
├── backend.py                      Rust bridge (lazy-load)
├── theme.py                        Theme specs + QSS generation
├── editor.py                       ColorCubeEditor widget
├── viewport.py                     FractalViewportWidget + FractalParamsPanel
├── thumbnail_utils.py              Base64 image encode/decode
│
├── application/
│   ├── controllers/                Stateless domain logic atoms
│   ├── coordinators/               Use-case orchestration
│   └── workflows/                  Multi-step user operations
│
├── services/                       Cross-cutting services
│
└── ui/
    ├── sections/                   Mediator/ports UI wiring layer
    ├── controllers/                Widget-level event logic
    ├── dialogs/                    Modal dialogs
    ├── presenters/                 CSS/tooltip formatting
    └── widgets/                    Custom QWidget subclasses
```

### Dependency Hierarchy (top-down)

```
app.py
  └── main_window_factory.py         ← DI root
        └── MainWindow
              └── MainWindowSectionsState  ← aggregates all collaborators
                    ├── Panel state machines  (6)
                    ├── Adapters / ports
                    │     └── MainWindowSections  ← layout builder
                    ├── application/{controllers,coordinators,workflows}
                    ├── services/
                    ├── persistence.py
                    ├── backend.py
                    └── state.py  (shared by all)
```

Nothing in `state.py` or `persistence.py` imports from application or UI layers. `backend.py` is pure bridge. The dependency arrows are unidirectional — that's the intended invariant and it's largely respected.

---

## 3. Layer-by-Layer Analysis

### 3.1 Data Model (`state.py`)

**Approach:** Frozen dataclasses — immutable, hashable, explicit serialization.

**Types:**
| Type | Purpose |
|------|---------|
| `UiSettings` | Theme preference |
| `ViewportState` | Full render parameter set (formula, center, scale, iterations, Julia/Phoenix params, palette offset, coloring mode) |
| `ParamsState` | ViewportState + cycle animation settings |
| `FavoriteSnapshot` | Saved fractal: viewport state + control points + rendered palette + base64 thumbnail |

**Strengths:**
- Immutability prevents accidental mutation across layers.
- `from_dict` methods defensively validate and coerce types; schema version tracked.
- Legacy format fallback keeps backward compatibility without polluting the model.

**Weaknesses:**
- `ViewportState` has grown large (~15 fields). No attempt to decompose into sub-structs (e.g., `JuliaParams`, `ColoringParams`). As new formula types are added this will worsen.
- No `__post_init__` validation beyond clamps — invalid combinations (e.g., `formula="newton"` + `mode="julia"`) are silently allowed at the model level and caught later in the UI.

### 3.2 Persistence Layer (`persistence.py`)

Two repositories: `SettingsRepository`, `FavoritesRepository`. Both operate on `~/.fractal_studio/`.

**Strengths:**
- Load results carry a `source` tag (`current` / `legacy` / `default`) enabling accurate status messages.
- Diagnostic strings from failed parses propagate to the UI status bar rather than being swallowed.
- Graceful fallback to defaults on any parse error.

**Weaknesses:**
- No transaction safety — save writes the entire file atomically (good) but doesn't use temp-file-then-rename (risky on crash mid-write).
- `last_load_diagnostic` is an attribute mutated on load. Since repositories are injected once at startup and reused, this is fine; but it's a hidden state mutation in an otherwise functional style.

### 3.3 Rust Backend Bridge (`backend.py`)

**Design:** `load_backend()` attempts `import fractal_core`; if absent, `CoreBackend` wraps `None`. All methods are no-ops or return defaults when unavailable. A `BackendProfile` dataclass describes capabilities.

**Strengths:**
- Graceful degradation allows the full UI to launch and be tested without compiling Rust.
- `BackendProfile` provides a clean contract so callers don't introspect the raw module.
- Single import site keeps the blast radius of backend changes minimal.

**Weaknesses:**
- Callers still check `backend.available` at multiple points (coordinators, services). A null-object pattern is partially applied but not consistently — some paths silently no-op, others guard with early returns. This inconsistency makes it hard to know what "works" without the Rust module.
- `render_mandelbrot` / `render_julia` are distinct method variants alongside the generic `render_fractal`. The reason for the split isn't documented; callers may be confused about which to use.

### 3.4 Application Layer — Controllers

Single-responsibility atoms. Stateless (no instance fields that change after construction). Each takes injected dependencies in `__init__`.

**`FavoritesController`** — snapshot creation, name uniqueness, restore, palette preview refresh.  
**`MainWindowController`** — export preset computation, aspect ratio application, settings dialog lifecycle.  
**`ThemeController`** — QSS application, dynamic widget repolish.

**Strengths:**
- Genuinely stateless; easy to unit-test with stubs.
- Clear scope: each controller owns exactly one domain.

**Weaknesses:**
- `MainWindowController` is stretched: it handles export preset math, aspect ratio logic, settings dialog, and export delegation. It's the largest controller and growing. Consider splitting into `ExportController` and `SettingsController`.
- `FavoritesController.restore_snapshot()` calls methods on viewport, params panel, and editor directly. This couples the controller to three concrete widgets. If the port abstractions in `ui/sections/ports.py` were used here instead, the coupling would be softer.

### 3.5 Application Layer — Coordinators

Orchestrators that combine a controller + service (or multiple controllers) to implement a use case.

**`FavoritesPanelCoordinator`** — row construction, selection, deletion, scroll layout management.  
**`ExportPanelCoordinator`** — thin delegator to `MainWindowController`.  
**`PalettePanelCoordinator`** — palette save/load/export guards.  
**`PalettePreviewCoordinator`** — palette preview label updates.  
**`SettingsDialogCoordinator`** — settings dialog + theme preview lifecycle.  
**`SidebarWiringCoordinator`** — wires 12 param panel signals to viewport slots.

**Strengths:**
- Separating wiring (coordinators) from logic (controllers) keeps controllers clean.

**Weaknesses:**
- `ExportPanelCoordinator` adds zero logic — it's a one-liner forwarding hub. Either it needs real orchestration responsibilities, or it should be eliminated and callers should call `MainWindowController` directly.
- `PalettePreviewCoordinator` is similarly thin.
- The boundary between coordinator and workflow isn't enforced by any naming convention, type, or base class. A developer adding a new feature must make a judgment call about which layer is appropriate, with no guidance in the code.

### 3.6 Application Layer — Workflows

User-facing multi-step operations that involve UI feedback:

**`StartupCoordinator`** — settings load → theme apply → status message composition.  
**`FavoritesWorkflowCoordinator`** — save, load, and delete favorites (full round-trip with persistence).  
**`ThemeWorkflowCoordinator`** — theme apply, optional persist, dialog open/close.

**Strengths:**
- Correctly treats startup, favorites, and theme change as distinct workflows with their own state.

**Weaknesses:**
- `ThemeWorkflowCoordinator.apply_theme_name()` captures `self._settings_repo` in a lambda to persist settings. This is a hidden side effect; the method name gives no indication persistence is conditional. A `persist: bool = False` parameter with an explicit conditional would be clearer.

### 3.7 Services

Stateless, cross-cutting operations dealing with file I/O or system-level actions:

**`ExportService`** — file dialog → render → save PNG → status.  
**`PaletteWorkflowService`** — file dialog → backend palette operations → status / callback.  
**`SettingsWorkflowService`** — diagnostic message composition + theme persistence helpers.

**Strengths:**
- Clean separation of file I/O from business logic.
- Services have no dependencies on UI widgets (except the `QWidget` parent for dialogs — acceptable).

**Weaknesses:**
- `SettingsWorkflowService` is more of a message-formatter utility than a service. Its methods (`backend_state_message`, `startup_message`, `append_diagnostics`) are pure functions with no state. They could reasonably live as module-level functions or in a `messages.py` module.

### 3.8 UI Sections — Mediator/Ports Layer

This is the most architecturally ambitious part of the codebase. It solves a real problem: wiring a multi-panel Qt window without spaghetti dependencies.

**Components:**

| Component | Role |
|-----------|------|
| `ports.py` | Protocol definitions (7 panel port interfaces) |
| `panel_state.py` | State machine per panel (6 classes) |
| `state.py` | `MainWindowSectionsState` aggregate |
| `adapters.py` + `*_adapter.py` | Protocol implementations bridging to state machines |
| `mediator.py` | Factory: builds `MainWindowSectionsPorts` from adapters |
| `sections.py` | Layout builder consuming port objects |
| `base.py` | Shared adapter base + favorites mixin |

**Data flow for a user action (e.g., save favorite):**
```
Button click
  → FavoritesPanelPortsAdapter.save_favorite()
    → MainWindowFavoritesState.save_favorite()
      → FavoritesWorkflowCoordinator.save_favorite()
        → FavoritesController.save_favorite()
          → FavoritesRepository.save()
          → add_row callback → panel state → scroll layout
          → status bar message
```

**Strengths:**
- Protocols in `ports.py` are the cleanest contracts in the codebase. Layout code in `sections.py` has no knowledge of business logic; it only knows port methods.
- Panel state machines encapsulate per-panel widget references, preventing them from leaking into `MainWindow`.
- The adapter layer means protocols can be reimplemented (e.g., for testing) without touching business logic.

**Weaknesses:**
- **Complexity budget exceeded.** There are now 7 ports, 6 panel states, 7+ adapter files, 1 mediator, and 1 aggregate state. Each new panel requires changes in 4–5 places. The indirection buys decoupling but costs navigability — tracing a single action requires jumping through 4–5 files.
- **`MainWindowSectionsState`** has 25+ constructor parameters and a `bind()` method that's already 80+ lines. It's a god object in disguise. The bind step is critical but has no validation — if a collaborator isn't bound, methods silently return `None`.
- **`bind_collaborators()`** in each panel state registers lambdas over `self`. These lambdas capture state objects, which can create closure-related memory/lifecycle issues if panel states are ever replaced.
- **Adapter files** (`viewport_adapter.py`, `backend_adapter.py`, etc.) are mostly 10–20 line files that delegate one level. The file count is not justified by the complexity; consolidating all adapters into `adapters.py` would eliminate 6 files with no loss of clarity.

### 3.9 UI Layer — Widget Controllers

**`ViewportController`** — render scheduling, pan/zoom event math, state bridge.  
**`ParamsPanelController`** — dynamic widget visibility based on formula selection.  
**`EditorController`** — color cube face mouse interaction, control point drag logic.

**Strengths:**
- Separating event logic from the QWidget classes keeps widgets (in `viewport.py`, `editor.py`) as thin view objects.
- `ViewportController.schedule_render()` uses a QTimer for debouncing — correct and important for performance.

**Weaknesses:**
- `ViewportController` and `FractalViewportWidget` are tightly coupled (the controller stores a reference to the widget and calls widget methods directly). The boundary between controller and widget is enforced only by convention.

---

## 4. Key Design Decisions — Assessment

| Decision | Assessment |
|----------|-----------|
| Immutable frozen dataclasses for state | **Correct.** Makes snapshots trivial, prevents mutation bugs. |
| Dependency injection via factory | **Correct.** Enables testability; context is explicit. |
| Mediator/ports for UI wiring | **Correct intent, over-engineered execution.** The abstraction is right; the file proliferation is not. |
| Lazy Rust backend with graceful degradation | **Correct.** Allows UI work without compilation. |
| Workflows as a distinct layer | **Correct.** Distinguishes user-visible operations from internal logic. |
| Weak references in favorites rows | **Correct, but inconsistent.** Should be applied wherever owner references are captured. |
| QTimer debouncing for render | **Correct.** Without this, mouse-move events would flood the renderer. |
| Signal coalescing in params panel | **Fragile.** `blockSignals` patterns are subtle and can be violated by future changes. |

---

## 5. Architectural Problems

### P1 — God Object: `MainWindowSectionsState`

`MainWindowSectionsState` accumulates all repositories, services, controllers, coordinators, workflows, and panel state references. Its `bind()` method is the integration point for the entire application. This is appropriate in a DI root, but it's not a DI root — it's a stateful object passed around.

**Recommendation:** Promote `main_window_factory.py` to be the true DI root. `MainWindowSectionsState` should hold only panel state machines, not all collaborators. Pass collaborators directly to the state machines that need them at construction time.

### P2 — Unclear Controller/Coordinator Boundary

`ExportPanelCoordinator` and `PalettePreviewCoordinator` are one-liner delegators. `FavoritesController` and `FavoritesWorkflowCoordinator` have overlapping responsibilities.

**Recommendation:** Define the boundary explicitly in a comment or ADR:  
- **Controller:** owns business logic, no UI widget references.  
- **Coordinator:** owns use-case orchestration, may reference widgets via port protocols.  
- **Workflow:** owns user-visible multi-step operations with feedback.  

Then delete or merge the thin coordinators that add no value.

### P3 — Silent Failures on Unbound Collaborators

Panel state methods return `None` silently if a collaborator hasn't been bound. This is a runtime trap that's invisible at call sites.

**Recommendation:** Add a `validate()` method to `MainWindowSectionsState` called at the end of `bind()`, asserting all non-optional collaborators are non-None. Fail loudly at startup rather than silently at runtime.

### P4 — ViewportState Flat Structure

`ViewportState` has ~15 fields. Formula-specific parameters (Julia `cx/cy`, Phoenix `real/imag`, Newton trap point) are always present regardless of which formula is active.

**Recommendation:** Introduce a discriminated union or sub-struct:
```python
@dataclass(frozen=True)
class JuliaParams:
    cx: float
    cy: float

@dataclass(frozen=True)
class ViewportState:
    formula: str
    center: complex
    scale: float
    max_iterations: int
    formula_params: JuliaParams | PhoenixParams | NewtonParams | MandelbrotParams
    ...
```
This eliminates invalid states and makes serialization code simpler.

### P5 — Test Coverage Gap: No Rust Backend

The test suite correctly stubs the backend, but this means render correctness, palette generation, and export are never tested. Six tests currently fail due to missing PySide6 in the CI environment.

**Recommendation:**
1. Add `pytest.ini` markers to separate `unit` (no Qt), `integration` (Qt required), and `backend` (Rust required) tests. Run only `unit` tests in the standard CI job.
2. Add a separate CI job that installs PySide6 and runs `integration` tests.
3. Consider property-based tests (Hypothesis) for state serialization round-trips — they're pure Python and require no dependencies.

### P6 — Adapter File Proliferation

Seven adapter files in `ui/sections/` each contain 15–30 lines. The ratio of boilerplate to logic is unfavorable.

**Recommendation:** Consolidate all adapter classes into `adapters.py`. The individual files add file-system overhead with no navigational benefit.

### P7 — Render Scheduling Fragility

`FractalViewportWidget` uses a `QTimer` to coalesce render calls. The timer is created once and reused. There's no guard against scheduling renders after the widget is destroyed (e.g., during test teardown).

**Recommendation:** Connect `timer.stop()` to the widget's `destroyed` signal, or check `self.isVisible()` before scheduling.

---

## 6. Recommendations — Prioritized

### Immediate (low risk, high value)

1. **Consolidate adapter files.** Move the 7 `*_adapter.py` files into `adapters.py`. Delete the individual files. No logic changes required.

2. **Add `validate()` to `MainWindowSectionsState`.** Assert all required collaborators are bound at startup. One method, prevents silent runtime failures.

3. **Add pytest markers** (`unit`, `integration`) and configure `pytest.ini` to run only `unit` by default. This fixes the 6 currently-failing tests in environments without PySide6.

4. **Delete thin coordinators.** `ExportPanelCoordinator` and `PalettePreviewCoordinator` add no logic. Inline their one-line delegations and remove the files.

### Medium-term (moderate effort, structural improvement)

5. **Decompose `ViewportState`.** Introduce formula-specific param sub-structs. Update serialization. This is a contained change with high payoff — eliminates invalid states and clarifies formulas.

6. **Shrink `MainWindowSectionsState.bind()`.** Each panel state machine should receive its own collaborators at construction, not via a 80-line bind method. The bind step should become a thin wiring call.

7. **Document the Controller/Coordinator/Workflow contract** (inline docstring or ADR). Without this, the next contributor will recreate the current confusion.

8. **Split `MainWindowController`** into `ExportController` (preset math, aspect ratio, export delegation) and `SettingsController` (dialog lifecycle, theme coordination). This is a mechanical rename/split.

### Longer-term (architectural)

9. **Introduce a command bus or event bus** for cross-panel communication. Currently, cross-panel actions flow through chains of coordinators and callbacks. A lightweight internal event system (not a full pub/sub) would flatten this and make the data flow explicit.

10. **Typed render parameter structs.** Pass a `RenderRequest` dataclass to `backend.render_fractal()` instead of kwargs. This gives callers a typed contract and makes it easy to add parameters without breaking call sites.

11. **Rust core: define the Python API contract explicitly.** The expected module interface (20+ functions) is inferred from `backend.py`. A `fractal_core.pyi` stub file should be committed alongside the Python package, generated by `pyo3-stub-gen` or hand-written, so the Python side gets type checking against the Rust exports.

---

## 7. What's Working Well

The codebase has several practices that are genuinely good and worth preserving:

- **Immutable state objects** — correctly applied throughout, not just in the data layer.
- **Dependency injection root** — `main_window_factory.py` is the right place for construction; wiring is explicit.
- **Protocol-based port interfaces** — `ports.py` is the cleanest boundary in the codebase. Layout code is truly decoupled from business logic.
- **Graceful backend degradation** — the UI is testable and usable without the compiled Rust module.
- **Diagnostic propagation** — load errors surface in the status bar rather than being swallowed.
- **Import policy test** — `test_import_policy.py` enforces architectural constraints automatically.
- **Debounced rendering** — QTimer coalescing is the correct pattern for mouse-driven render scheduling.

---

## 8. Missing Capabilities (Not Bugs)

These are gaps in the current design that will matter as the application grows:

| Gap | Impact |
|-----|--------|
| No undo/redo | User cannot step back through viewport changes; frustrating for exploration |
| No async rendering | Long renders block the Qt event loop; UI freezes during export |
| No keyboard navigation | Accessibility and power-user usability |
| No settings migration path | `version: 1` schema is tracked but no migration logic exists |
| No palette undo | Dragging control points to a bad position is irreversible |

The most impactful missing feature is **async rendering**. As the Rust renderer is extended to support higher iteration counts and larger exports, blocking the event loop will become noticeably painful. The standard Qt pattern is to move render calls to a `QThread` and emit results back to the main thread via signals.

---

## 9. Summary

Fractal Studio has a well-considered architecture that has been actively refactored toward clean layering. The immutable data model, DI factory, and protocol-based UI ports are correct design choices. The primary risk is the `ui/sections/` layer: it has achieved its decoupling goals but the implementation complexity (7 adapters, 6 panel states, 1 mediator, 1 80-line bind method) is approaching the point where it costs more to navigate than it saves in coupling. The recommendations above are sequenced to reduce that cost incrementally without requiring a rewrite.

The Rust core is not yet implemented (per the CLAUDE.md "Next Task" note). When it arrives, the backend bridge design is sound enough to accommodate it with minimal changes to the Python side.
