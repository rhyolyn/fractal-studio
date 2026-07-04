# Review-05: Unify Render Invocation Behind RenderRequest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written.

**Goal:** Collapse the three hand-plumbed 17-argument `render_fractal` call sites (`ViewportController.render` sync fallback, `RenderWorker.do_render`, `ExportService.export_render`) into one `CoreBackend.render(request: RenderRequest) -> bytes`, extract the duplicated status-string formatter, and remove the redundant widget-level render debounce.

**Architecture:** `RenderRequest` (frozen dataclass in `state.py`) already exists and carries everything a render needs. We add `CoreBackend.render(request)` as the single unpacking point, `format_render_status(state)` in `state.py` as the single formatter, and route all three call sites through them. The viewport widget's zero-delay `_render_timer` coalescing is removed — `RenderScheduler` already debounces (50 ms); the sync fallback path (scheduler=None, tests only) does not need coalescing.

**Tech Stack:** Python 3.12, PySide6 ≥ 6.8, pytest.

**Recommended model:** Claude Sonnet 4.6. *Reasoning:* the design is fully pinned here and the change is mostly mechanical consolidation; the threading-adjacent parts (worker, scheduler) are not restructured, only re-routed. Escalate to Opus 4.8 only if the executor must diverge from the code below (e.g., unforeseen test coupling).

**Dependencies:** Do review-03 (import guards) and review-04 (test split) first — **do not start until the review-04 PR is merged into `main`** (master-plan ground rule 6: execute against current `main`, never a stale branch). The tests touched here (`TestViewportController`, `TestViewportRenderScheduling`) live in `ui/tests/test_viewport_widget.py` after the split.

> **Amended 2026-07-03 after Codex plan review:** Task 3's test-home pointer corrected (`ExportService`/`ExportRunner` tests live in the pre-existing `ui/tests/test_render_workers.py`, not the split's `test_export_panel.py`), and Task 4 now specifies the exact rewrite of the widget-coalescing tests and the render-bridge fake instead of a generic "grep and fix".

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — engineering standards apply ("Refactor duplication early"). The C++/Unreal sections do not apply.
2. `ui/src/fractal_studio/state.py` (`RenderRequest`, `ViewportState.to_render_kwargs`).
3. `ui/src/fractal_studio/backend.py` (`CoreBackend.render_fractal`).
4. The three call sites: `ui/src/fractal_studio/ui/controllers/viewport_controller.py` (`render`, lines ~256-308), `ui/src/fractal_studio/ui/workers/render_worker.py` (`do_render`), `ui/src/fractal_studio/services/export_service.py` (`export_render`).

## Global Constraints

- `state.py` must stay Qt-free (the review-03 guard enforces this — `format_render_status` is pure string formatting, which is fine).
- `backend.py` may import `RenderRequest` from `state.py` (downward dependency; allowed).
- UI-only mode must keep working: `CoreBackend(None).render(request)` returns `b""`.
- Public behavior unchanged: same images, same status strings, same scheduling semantics via `RenderScheduler`.
- Commit style: conventional commits.

---

### Task 1: `CoreBackend.render(request)` — the single unpacking point

**Files:**
- Modify: `ui/src/fractal_studio/backend.py`
- Test: `ui/tests/test_backend.py` (append)

**Interfaces:**
- Consumes: `RenderRequest(generation, viewport_state, palette, width, height)` from `fractal_studio.state`.
- Produces: `CoreBackend.render(self, request: RenderRequest) -> bytes` — Tasks 2-4 call exactly this.

- [ ] **Step 1: Write the failing test**

Append to `ui/tests/test_backend.py` (match the file's existing marker style — check its imports/marks first and replicate):

```python
class RecordingRenderModule:
    """Stands in for the fractal_core module; records render_fractal kwargs."""

    def __init__(self) -> None:
        self.args: tuple | None = None
        self.kwargs: dict | None = None

    def render_fractal(self, *args, **kwargs) -> bytes:
        self.args = args
        self.kwargs = kwargs
        return b"\x01\x02\x03\x04"


@pytest.mark.unit
def test_backend_render_unpacks_request_fields() -> None:
    from fractal_studio.backend import CoreBackend
    from fractal_studio.state import JuliaParams, RenderRequest, ViewportState

    module = RecordingRenderModule()
    backend = CoreBackend(module)
    state = ViewportState(
        formula="standard",
        center_x=-0.5,
        center_y=0.25,
        scale=1.5,
        max_iterations=333,
        is_julia=True,
        formula_params=JuliaParams(cx=-0.7, cy=0.2),
        coloring_mode="orbit_trap_circle",
        palette_offset=0.125,
        power=4,
    )
    request = RenderRequest(
        generation=7,
        viewport_state=state,
        palette=((1, 2, 3), (4, 5, 6)),
        width=64,
        height=48,
    )

    raw = backend.render(request)

    assert raw == b"\x01\x02\x03\x04"
    assert module.args == ("standard", 64, 48)
    assert module.kwargs is not None
    assert module.kwargs["is_julia"] is True
    assert module.kwargs["julia_real"] == -0.7
    assert module.kwargs["julia_imag"] == 0.2
    assert module.kwargs["power"] == 4
    assert module.kwargs["center_x"] == -0.5
    assert module.kwargs["center_y"] == 0.25
    assert module.kwargs["scale"] == 1.5
    assert module.kwargs["max_iterations"] == 333
    assert module.kwargs["palette"] == [(1, 2, 3), (4, 5, 6)]
    assert module.kwargs["coloring_mode"] == "orbit_trap_circle"
    assert module.kwargs["palette_offset"] == 0.125


@pytest.mark.unit
def test_backend_render_returns_empty_without_module() -> None:
    from fractal_studio.backend import CoreBackend
    from fractal_studio.state import RenderRequest, StandardParams, ViewportState

    state = ViewportState(
        formula="standard", center_x=-0.5, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    request = RenderRequest(generation=1, viewport_state=state, palette=(), width=8, height=8)
    assert CoreBackend(None).render(request) == b""
```

- [ ] **Step 2: Run to verify failure**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest tests/test_backend.py -v -k "render_unpacks or render_returns_empty"
```

Expected: FAIL with `AttributeError: 'CoreBackend' object has no attribute 'render'`.

- [ ] **Step 3: Implement**

In `ui/src/fractal_studio/backend.py`, add the import at the top:

```python
from fractal_studio.state import RenderRequest
```

Add this method to `CoreBackend`, directly above `render_fractal`:

```python
    def render(self, request: RenderRequest) -> bytes:
        state = request.viewport_state
        kwargs = state.to_render_kwargs()
        return self.render_fractal(
            state.formula,
            request.width,
            request.height,
            is_julia=state.is_julia,
            julia_real=kwargs["julia_real"],
            julia_imag=kwargs["julia_imag"],
            power=state.power,
            phoenix_real=kwargs["phoenix_real"],
            phoenix_imag=kwargs["phoenix_imag"],
            center_x=state.center_x,
            center_y=state.center_y,
            scale=state.scale,
            max_iterations=state.max_iterations,
            palette=list(request.palette),
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=state.palette_offset,
        )
```

- [ ] **Step 4: Run to verify pass, then commit**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_backend.py -v
git add ui/src/fractal_studio/backend.py ui/tests/test_backend.py
git commit -m "feat: add CoreBackend.render(RenderRequest) as the single render unpacking point"
```

---

### Task 2: `format_render_status` — the single status formatter

**Files:**
- Modify: `ui/src/fractal_studio/state.py` (append function at module bottom)
- Test: `ui/tests/test_settings_repository.py` is the wrong home; create `ui/tests/test_render_status.py`

**Interfaces:**
- Produces: `format_render_status(state: ViewportState) -> str` in `fractal_studio.state` — Tasks 3-4 import it.

- [ ] **Step 1: Write the failing test**

Create `ui/tests/test_render_status.py`:

```python
from __future__ import annotations

import pytest

from fractal_studio.state import StandardParams, ViewportState, format_render_status


@pytest.mark.unit
def test_format_render_status_matches_legacy_shape() -> None:
    state = ViewportState(
        formula="burning_ship", center_x=-0.5, center_y=-0.5, scale=3.0,
        max_iterations=256, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    assert format_render_status(state) == (
        "Burning Ship · Mandelbrot | center (-0.5000, -0.5000) | scale 3 | 256 iters"
    )


@pytest.mark.unit
def test_format_render_status_shows_multibrot_power() -> None:
    state = ViewportState(
        formula="multibrot", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=128, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0, power=5,
    )
    assert "(n=5)" in format_render_status(state)
```

- [ ] **Step 2: Run to verify failure** (`ImportError: cannot import name 'format_render_status'`), then implement in `ui/src/fractal_studio/state.py` (bottom of file):

```python
def format_render_status(state: ViewportState) -> str:
    label = state.formula.replace("_", " ").title()
    mode = "Julia" if state.is_julia else "Mandelbrot"
    extra = f" (n={state.power})" if state.formula == "multibrot" else ""
    return (
        f"{label}{extra} · {mode} | "
        f"center ({state.center_x:.4f}, {state.center_y:.4f}) | "
        f"scale {state.scale:.4g} | "
        f"{state.max_iterations} iters"
    )
```

- [ ] **Step 3: Run to verify pass, then commit**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_render_status.py -v
git add ui/src/fractal_studio/state.py ui/tests/test_render_status.py
git commit -m "feat: extract format_render_status as single render status formatter"
```

---

### Task 3: Route `RenderWorker` and `ExportService` through the new API

**Files:**
- Modify: `ui/src/fractal_studio/ui/workers/render_worker.py` (`do_render`)
- Modify: `ui/src/fractal_studio/services/export_service.py` (`export_render`)
- Modify tests: `ui/tests/test_render_workers.py` only — this pre-existing file holds both the `RenderWorker`/`RenderScheduler` tests **and** the `ExportService`/`ExportRunner` tests (~lines 170-217); update its fakes only if they stub `render_fractal` directly (behavior is unchanged). The split's `ui/tests/test_export_panel.py` holds panel/coordinator-level tests that do not stub the service render path — confirm with `grep -n "render_fractal\|ExportService" ui/tests/test_export_panel.py` and expect no changes there.

- [ ] **Step 1: Rewrite `RenderWorker.do_render`**

```python
    @Slot(object)  # RenderRequest — object type matches the Signal(object) on RenderScheduler
    def do_render(self, request: RenderRequest) -> None:
        raw = self._backend.render(request)
        if not raw:
            self.render_complete.emit(RenderResult(
                generation=request.generation,
                image=None,
                status=None,
            ))
            return

        image = QImage(
            raw, request.width, request.height,
            request.width * 4, QImage.Format.Format_RGBA8888,
        ).copy()
        self.render_complete.emit(RenderResult(
            generation=request.generation,
            image=image,
            status=format_render_status(request.viewport_state),
        ))
```

Update the module's imports: `from fractal_studio.state import RenderRequest, format_render_status`.

- [ ] **Step 2: Rewrite `ExportService.export_render`**

```python
from fractal_studio.state import RenderRequest, ViewportState


class ExportService:
    def __init__(self, backend: CoreBackend) -> None:
        self._backend = backend

    def export_render(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bytes | None:
        set_status(f"Rendering {width}×{height}...")
        request = RenderRequest(
            generation=0,
            viewport_state=viewport_state,
            palette=tuple(palette),
            width=width,
            height=height,
        )
        raw = self._backend.render(request)
        if not raw:
            set_status("Backend not available — no render produced.")
            return None
        return raw
```

- [ ] **Step 3: Run the worker and export tests, fix stubs if they faked `render_fractal`**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_render_workers.py -m "unit or integration" -v
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q -k "export"
```

If a test's fake backend implements `render_fractal(...)` and the code now calls `render(request)`, prefer keeping the fake at the `render_fractal` level and letting the real `CoreBackend.render` logic run through it (i.e., wrap fakes in `CoreBackend(RecordingRenderModule())` where practical) — that keeps the unpacking logic under test. Only add a `render(request)` method to a fake when it stubs `CoreBackend` itself rather than the module.

- [ ] **Step 4: Commit**

```powershell
git add ui/src/fractal_studio/ui/workers/render_worker.py ui/src/fractal_studio/services/export_service.py ui/tests
git commit -m "refactor: route RenderWorker and ExportService through CoreBackend.render"
```

---

### Task 4: Route the sync fallback and remove the widget-level debounce

**Files:**
- Modify: `ui/src/fractal_studio/ui/controllers/viewport_controller.py` (`render`)
- Modify: `ui/src/fractal_studio/viewport.py` (`FractalViewportWidget.__init__`, `request_render`, `_flush_scheduled_render`)
- Modify tests: viewport tests (post-split: `ui/tests/test_viewport_widget.py`)

- [ ] **Step 1: Rewrite `ViewportController.render`**

Replace the whole method with:

```python
    def render(self, widget: _ViewportAdapter) -> ViewportRenderResult:
        palette = widget.palette()
        if not self._backend.capabilities.can_render or not palette:
            return ViewportRenderResult(image=None, status=None)

        width = max(1, widget.width())
        height = max(1, widget.height())
        state = widget.to_state()

        if self._scheduler is not None:
            self._scheduler.schedule(
                viewport_state=state,
                palette=tuple(palette),
                width=width,
                height=height,
            )
            return ViewportRenderResult(image=None, status=None)

        # Fallback: synchronous render when no scheduler is wired (used in tests)
        request = RenderRequest(
            generation=0, viewport_state=state, palette=tuple(palette),
            width=width, height=height,
        )
        raw = self._backend.render(request)
        image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        status = format_render_status(state)
        widget.store_rendered_image(image)
        widget.update()
        widget.status_changed.emit(status)
        return ViewportRenderResult(image=image, status=status)
```

Update imports in the module: `from fractal_studio.state import (JuliaParams, NewtonParams, PhoenixParams, RenderRequest, ViewportState, format_render_status)`.

Behavioral note (intended, verify tests agree): previously the scheduler path scheduled even when… no — it also required `can_render and palette`; the consolidated guard preserves that. The only intentional change is DRY.

- [ ] **Step 2: Remove the widget-level debounce**

In `ui/src/fractal_studio/viewport.py`, `FractalViewportWidget.__init__`, delete:

```python
        self._render_pending = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._flush_scheduled_render)
```

Delete `_flush_scheduled_render` and replace `request_render` with:

```python
    def request_render(self) -> None:
        self._controller.render(self)
```

Rationale (leave this reasoning in the commit message): `RenderScheduler` already debounces at 50 ms with generation-based staleness; a second zero-delay coalescing layer in the widget adds state and no protection. In the scheduler-less sync fallback (tests only), per-event rendering is acceptable.

- [ ] **Step 3: Rewrite the widget-coalescing tests to assert delegation, not coalescing**

`TestViewportRenderScheduling` in `ui/tests/test_viewport_widget.py` currently pins the *old* widget-level debounce: `test_mouse_move_coalesces_render_requests` sends 5 mouse-move events, asserts `render_calls == 0`, then `processEvents()`, then `render_calls == 1`. After this task the widget delegates synchronously, so that test must change — do not "fix" it by reintroducing the timer. Replace its tail (keep the setup and the `ControllerStub` unchanged) with:

```python
        self.assertEqual(stub.move_calls, 5)
        # request_render delegates synchronously now; coalescing is owned by
        # RenderScheduler (50 ms debounce + generation counter — covered in
        # test_render_workers.py), not by the widget.
        self.assertEqual(stub.render_calls, 5)
```

and rename it to `test_mouse_move_delegates_each_render_request` (delete the `processEvents()` call — no event-loop dependency remains). `test_mouse_move_without_pan_does_not_schedule_render` needs no change: `handle_mouse_move` returning `False` still means `request_render` is never called. Apply the same delegation treatment to any resize-based coalescing test in the class.

**The render-bridge test with a `render_fractal`-only fake:** `TestViewportController`'s sync-render test stubs a backend that implements only `render_fractal`. After this task `ViewportController.render` calls `self._backend.render(request)`, so that fake breaks. Replace it with `CoreBackend(RecordingRenderModule())` (the recording module from Task 1's `test_backend.py` — move `RecordingRenderModule` into `ui/tests/support.py`, the shared helper module created by review-04, if importing across test modules is awkward; the import form is `from tests.support import RecordingRenderModule`), so the real `CoreBackend.render` unpacking stays under test rather than being stubbed away.

Then sweep for any remaining coupling:

```powershell
grep -rn "_render_timer\|_render_pending\|_flush_scheduled_render" ui/
```

Expected: zero matches in `ui/src`; any test match must be rewritten per the above patterns.

- [ ] **Step 4: Full suite, then commit**

```powershell
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q
git add ui/src/fractal_studio/ui/controllers/viewport_controller.py ui/src/fractal_studio/viewport.py ui/tests
git commit -m "refactor: unify sync render fallback on CoreBackend.render; drop redundant widget debounce"
```

Expected: green, same count as the review-04 baseline.

## Done criteria

- Exactly one place unpacks `ViewportState` into `render_fractal` kwargs (`CoreBackend.render`); exactly one status formatter.
- `grep -rn "to_render_kwargs" ui/src` shows only `state.py` (definition) and `backend.py` (single consumer).
- Full suite green; scheduling semantics unchanged (50 ms debounce + generation staleness in `RenderScheduler` only).
