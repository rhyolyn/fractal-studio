# Async Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move fractal rendering and export off the Qt UI thread so the app remains responsive during pan, zoom, and large PNG exports.

**Architecture:** A `RenderWorker(QObject)` lives permanently in a `QThread`; a `RenderScheduler` on the main thread debounces requests (50 ms), assigns generation numbers, and drops stale results. Export uses a per-job `ExportRunner(QObject)` in a short-lived `QThread`. `ViewportController.render()` becomes non-blocking by delegating to the scheduler. The scheduler is threaded through `_BasePortsAdapter` (alongside `backend`) so `sections.py` can pass it to `FractalViewportWidget` at construction time.

**Tech Stack:** PySide6 `QThread`, `QObject`, `Signal`, `Slot` — standard Qt threading model. Python 3.12+. pytest (unit tests run without Qt; integration tests require PySide6).

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `ui/src/fractal_studio/state.py` | Add `RenderRequest` frozen dataclass |
| Create | `ui/src/fractal_studio/ui/workers/__init__.py` | Empty package marker |
| Create | `ui/src/fractal_studio/ui/workers/render_worker.py` | `RenderResult` dataclass + `RenderWorker(QObject)` |
| Create | `ui/src/fractal_studio/ui/workers/render_scheduler.py` | `RenderScheduler(QObject)` — generation counter + 50 ms debounce |
| Create | `ui/src/fractal_studio/ui/workers/export_runner.py` | `ExportRunner(QObject)` — single-shot background export |
| Modify | `ui/src/fractal_studio/ui/controllers/viewport_controller.py` | `render()` delegates to scheduler; accepts `scheduler` kwarg |
| Modify | `ui/src/fractal_studio/ui/sections/panel_state.py` | `MainWindowViewportState._on_render_ready()` slot; `MainWindowExportState._do_export()` becomes async |
| Modify | `ui/src/fractal_studio/application/controllers/export_controller.py` | Async export with `ExportRunner`; guard against double-export |
| Modify | `ui/src/fractal_studio/ui/sections/adapters/base.py` | Add `render_scheduler` property (alongside `backend`) |
| Modify | `ui/src/fractal_studio/ui/sections/adapters/__init__.py` | `build_sections_ports()` accepts `render_scheduler` |
| Modify | `ui/src/fractal_studio/main_window_factory.py` | Create thread/worker/scheduler; wire signals; teardown on quit |
| Modify | `ui/src/fractal_studio/ui/sections/sections.py` | Pass `ports.render_scheduler` to `FractalViewportWidget` |
| Modify | `ui/src/fractal_studio/viewport.py` | `FractalViewportWidget.__init__` accepts `scheduler` kwarg |
| Create | `ui/tests/test_render_workers.py` | Unit + integration tests for workers and scheduler |

---

## Task 1: Add `RenderRequest` to `state.py`

**Files:**
- Modify: `ui/src/fractal_studio/state.py`
- Test: `ui/tests/test_render_workers.py`

`RenderRequest` is a frozen dataclass that carries everything a worker needs for one render. It belongs in `state.py` because it contains only pure-Python types (no Qt). `RenderResult` is in `render_worker.py` because it holds a `QImage`.

- [ ] **Step 1: Write the failing test**

Create `ui/tests/test_render_workers.py`:

```python
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
import sys
sys.path.insert(0, str(SOURCE_ROOT))


@pytest.mark.unit
def test_render_request_is_frozen() -> None:
    from fractal_studio.state import RenderRequest, ViewportState, StandardParams

    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=256, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    req = RenderRequest(generation=1, viewport_state=state, palette=[], width=4, height=4)
    assert dataclasses.is_dataclass(req)
    with pytest.raises(Exception):
        req.generation = 2  # type: ignore[misc]


@pytest.mark.unit
def test_render_request_carries_all_fields() -> None:
    from fractal_studio.state import RenderRequest, ViewportState, StandardParams

    state = ViewportState(
        formula="standard", center_x=-0.5, center_y=0.0, scale=3.0,
        max_iterations=128, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    palette = [(255, 0, 0), (0, 255, 0)]
    req = RenderRequest(generation=7, viewport_state=state, palette=palette, width=100, height=80)
    assert req.generation == 7
    assert req.viewport_state is state
    assert req.palette == palette
    assert req.width == 100
    assert req.height == 80
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
cd ui && python -m pytest tests/test_render_workers.py -v -m unit 2>&1 | tail -10
```
Expected: `ImportError` or `cannot import name 'RenderRequest'`

- [ ] **Step 3: Add `RenderRequest` to `state.py`**

Read `ui/src/fractal_studio/state.py`. Add after the `ViewportState` class definition (before `ParamsState`):

```python
@dataclass(frozen=True)
class RenderRequest:
    generation: int
    viewport_state: ViewportState
    palette: list[tuple[int, int, int]]
    width: int
    height: int
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
cd ui && python -m pytest tests/test_render_workers.py -v -m unit 2>&1 | tail -10
```
Expected: 2 PASS.

- [ ] **Step 5: Run full unit suite to confirm no regressions**

```powershell
cd ui && python -m pytest -m unit -q 2>&1 | tail -5
```
Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add ui/src/fractal_studio/state.py ui/tests/test_render_workers.py
git commit -m "feat: add RenderRequest frozen dataclass to state.py"
```

---

## Task 2: Create `RenderWorker`

**Files:**
- Create: `ui/src/fractal_studio/ui/workers/__init__.py`
- Create: `ui/src/fractal_studio/ui/workers/render_worker.py`
- Test: `ui/tests/test_render_workers.py`

`RenderWorker` is a `QObject` that lives in a background `QThread`. Its `do_render` slot calls `backend.render_fractal()` and emits `render_complete`. `RenderResult` is defined here because it holds a `QImage` (a Qt type not appropriate for `state.py`).

- [ ] **Step 1: Write the failing tests**

Append to `ui/tests/test_render_workers.py`:

```python
@pytest.mark.unit
def test_render_result_is_frozen() -> None:
    import dataclasses
    from PySide6.QtGui import QImage
    from fractal_studio.ui.workers.render_worker import RenderResult

    result = RenderResult(generation=3, image=None, status=None)
    assert dataclasses.is_dataclass(result)
    with pytest.raises(Exception):
        result.generation = 4  # type: ignore[misc]


@pytest.mark.integration
def test_render_worker_emits_result_on_do_render() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    from fractal_studio.backend import CoreBackend
    from fractal_studio.state import RenderRequest, ViewportState, StandardParams
    from fractal_studio.ui.workers.render_worker import RenderWorker

    _app = QApplication.instance() or QApplication([])

    backend = CoreBackend(None)  # null backend — returns b""
    worker = RenderWorker(backend)
    thread = QThread()
    worker.moveToThread(thread)
    thread.start()

    results = []
    worker.render_complete.connect(results.append)

    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    req = RenderRequest(generation=1, viewport_state=state, palette=[(0,0,0)], width=4, height=4)
    worker.do_render(req)

    import time
    deadline = time.time() + 2.0
    while not results and time.time() < deadline:
        _app.processEvents()

    thread.quit()
    thread.wait()

    assert len(results) == 1
    assert results[0].generation == 1
    # Null backend returns b"" so image is None
    assert results[0].image is None
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_render_result_is_frozen tests/test_render_workers.py::test_render_worker_emits_result_on_do_render -v 2>&1 | tail -10
```
Expected: FAIL — `ModuleNotFoundError: fractal_studio.ui.workers.render_worker`

- [ ] **Step 3: Create the workers package**

```powershell
New-Item -ItemType Directory -Force ui/src/fractal_studio/ui/workers
"" | Set-Content ui/src/fractal_studio/ui/workers/__init__.py
```

- [ ] **Step 4: Create `render_worker.py`**

Create `ui/src/fractal_studio/ui/workers/render_worker.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from fractal_studio.state import RenderRequest

if TYPE_CHECKING:
    from fractal_studio.backend import CoreBackend


@dataclass(frozen=True)
class RenderResult:
    generation: int
    image: QImage | None
    status: str | None


class RenderWorker(QObject):
    render_complete = Signal(RenderResult)

    def __init__(self, backend: CoreBackend) -> None:
        super().__init__()
        self._backend = backend

    @Slot(RenderRequest)
    def do_render(self, request: RenderRequest) -> None:
        state = request.viewport_state
        kwargs = state.to_render_kwargs()
        raw = self._backend.render_fractal(
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
            palette=request.palette,
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=state.palette_offset,
        )
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
        label = state.formula.replace("_", " ").title()
        mode = "Julia" if state.is_julia else "Mandelbrot"
        extra = f" (n={state.power})" if state.formula == "multibrot" else ""
        status = (
            f"{label}{extra} · {mode} | "
            f"center ({state.center_x:.4f}, {state.center_y:.4f}) | "
            f"scale {state.scale:.4g} | "
            f"{state.max_iterations} iters"
        )
        self.render_complete.emit(RenderResult(
            generation=request.generation,
            image=image,
            status=status,
        ))
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_render_result_is_frozen tests/test_render_workers.py::test_render_worker_emits_result_on_do_render -v -m "unit or integration" 2>&1 | tail -10
```
Expected: 2 PASS.

- [ ] **Step 6: Commit**

```powershell
git add ui/src/fractal_studio/ui/workers/__init__.py ui/src/fractal_studio/ui/workers/render_worker.py ui/tests/test_render_workers.py
git commit -m "feat: add RenderWorker and RenderResult"
```

---

## Task 3: Create `RenderScheduler`

**Files:**
- Create: `ui/src/fractal_studio/ui/workers/render_scheduler.py`
- Test: `ui/tests/test_render_workers.py`

`RenderScheduler` lives on the main thread. It debounces incoming render requests with a 50 ms `QTimer`, assigns monotonically increasing generation numbers, and drops stale results from the worker.

- [ ] **Step 1: Write the failing tests**

Append to `ui/tests/test_render_workers.py`:

```python
@pytest.mark.integration
def test_scheduler_drops_stale_results() -> None:
    from PySide6.QtWidgets import QApplication
    from fractal_studio.state import ViewportState, StandardParams
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
    from fractal_studio.ui.workers.render_worker import RenderResult
    from PySide6.QtGui import QImage

    _app = QApplication.instance() or QApplication([])
    scheduler = RenderScheduler()
    ready: list[RenderResult] = []
    scheduler.render_ready.connect(ready.append)

    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )

    # Schedule twice — generation increments to 2
    scheduler.schedule(state, [], 4, 4)
    scheduler.schedule(state, [], 4, 4)
    current_gen = scheduler.current_generation

    # Deliver a stale result (generation = current_gen - 1)
    stale = RenderResult(generation=current_gen - 1, image=None, status=None)
    scheduler._on_result(stale)
    assert ready == []

    # Deliver the current result
    current = RenderResult(generation=current_gen, image=None, status=None)
    scheduler._on_result(current)
    assert len(ready) == 1
    assert ready[0].generation == current_gen


@pytest.mark.integration
def test_scheduler_emits_render_requested_after_debounce() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from fractal_studio.state import ViewportState, StandardParams
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
    from fractal_studio.state import RenderRequest

    _app = QApplication.instance() or QApplication([])
    scheduler = RenderScheduler()
    requests: list[RenderRequest] = []
    scheduler.render_requested.connect(requests.append)

    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )

    # Three rapid schedule calls
    scheduler.schedule(state, [], 4, 4)
    scheduler.schedule(state, [], 4, 4)
    scheduler.schedule(state, [], 4, 4)

    # Wait for debounce to fire (> 50 ms)
    QTest.qWait(100)

    # Only one request should have been emitted (the last one)
    assert len(requests) == 1
    assert requests[0].generation == scheduler.current_generation
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_scheduler_drops_stale_results tests/test_render_workers.py::test_scheduler_emits_render_requested_after_debounce -v -m "unit or integration" 2>&1 | tail -10
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `render_scheduler.py`**

Create `ui/src/fractal_studio/ui/workers/render_scheduler.py`:

```python
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from fractal_studio.state import RenderRequest, ViewportState

from fractal_studio.ui.workers.render_worker import RenderResult

_DEBOUNCE_MS = 50


class RenderScheduler(QObject):
    render_requested = Signal(RenderRequest)
    render_ready = Signal(RenderResult)

    def __init__(self) -> None:
        super().__init__()
        self._generation: int = 0
        self._pending: RenderRequest | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_DEBOUNCE_MS)
        self._timer.timeout.connect(self._fire)

    @property
    def current_generation(self) -> int:
        return self._generation

    def schedule(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None:
        self._generation += 1
        self._pending = RenderRequest(
            generation=self._generation,
            viewport_state=viewport_state,
            palette=list(palette),
            width=width,
            height=height,
        )
        self._timer.start()

    def _fire(self) -> None:
        if self._pending is not None:
            self.render_requested.emit(self._pending)
            self._pending = None

    @Slot(RenderResult)
    def _on_result(self, result: RenderResult) -> None:
        if result.generation == self._generation:
            self.render_ready.emit(result)
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_scheduler_drops_stale_results tests/test_render_workers.py::test_scheduler_emits_render_requested_after_debounce -v -m "unit or integration" 2>&1 | tail -10
```
Expected: 2 PASS.

- [ ] **Step 5: Run full test suite**

```powershell
cd ui && python -m pytest -m "unit or integration" --deselect tests/test_ui_redesign.py::TestColorCubeEditor::test_mouse_press_adds_point_and_hover_status -q 2>&1 | tail -5
```
Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add ui/src/fractal_studio/ui/workers/render_scheduler.py ui/tests/test_render_workers.py
git commit -m "feat: add RenderScheduler with generation counter and 50ms debounce"
```

---

## Task 4: Wire viewport to scheduler

**Files:**
- Modify: `ui/src/fractal_studio/ui/controllers/viewport_controller.py`
- Modify: `ui/src/fractal_studio/viewport.py`
- Modify: `ui/src/fractal_studio/ui/sections/adapters/base.py`
- Modify: `ui/src/fractal_studio/ui/sections/adapters/__init__.py`
- Modify: `ui/src/fractal_studio/ui/sections/sections.py`
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py`
- Modify: `ui/src/fractal_studio/main_window_factory.py`

This is the largest task. Read every file before editing.

### 4a: Update `ViewportController.render()`

`render()` currently calls `backend.render_fractal()` and blocks. After this step it delegates to `self._scheduler.schedule()` when a scheduler is available, or falls back to synchronous rendering when `_scheduler` is `None` (for tests that don't wire a scheduler).

- [ ] **Step 1: Read `viewport_controller.py` in full**

- [ ] **Step 2: Update `ViewportController.__init__` and `render()`**

In `ui/src/fractal_studio/ui/controllers/viewport_controller.py`, add the import and update the class:

Add to imports:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
```

Update `__init__`:
```python
class ViewportController:
    def __init__(self, backend: CoreBackend, scheduler: RenderScheduler | None = None) -> None:
        self._backend = backend
        self._scheduler = scheduler
```

Replace the `render()` method entirely:
```python
    def render(self, widget: _ViewportAdapter) -> ViewportRenderResult:
        if self._scheduler is not None:
            palette = widget.palette()
            if self._backend.capabilities.can_render and palette:
                self._scheduler.schedule(
                    viewport_state=widget.to_state(),
                    palette=palette,
                    width=max(1, widget.width()),
                    height=max(1, widget.height()),
                )
            return ViewportRenderResult(image=None, status=None)

        # Fallback: synchronous render (used when no scheduler is wired, e.g. tests)
        palette = widget.palette()
        if not self._backend.capabilities.can_render or not palette:
            return ViewportRenderResult(image=None, status=None)

        width = max(1, widget.width())
        height = max(1, widget.height())
        state = widget.to_state()
        kwargs = state.to_render_kwargs()
        raw = self._backend.render_fractal(
            state.formula, width, height,
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
            palette=palette,
            coloring_mode=state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=state.palette_offset,
        )
        image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        label = state.formula.replace("_", " ").title()
        mode = "Julia" if state.is_julia else "Mandelbrot"
        extra = f" (n={state.power})" if state.formula == "multibrot" else ""
        status = (
            f"{label}{extra} · {mode} | "
            f"center ({state.center_x:.4f}, {state.center_y:.4f}) | "
            f"scale {state.scale:.4g} | "
            f"{state.max_iterations} iters"
        )
        widget.store_rendered_image(image)
        widget.update()
        widget.status_changed.emit(status)
        return ViewportRenderResult(image=image, status=status)
```

- [ ] **Step 3: Run unit tests to verify nothing broken**

```powershell
cd ui && python -m pytest -m unit -q 2>&1 | tail -5
```
Expected: all pass (existing tests use a DummyBackend with no scheduler — the fallback path).

### 4b: Add `_on_render_ready` to `MainWindowViewportState`

When a scheduler result arrives on the main thread, the panel state applies it to the viewport widget.

- [ ] **Step 4: Read `panel_state.py` — `MainWindowViewportState` class**

- [ ] **Step 5: Add `_on_render_ready` to `MainWindowViewportState`**

Add this method to `MainWindowViewportState` in `panel_state.py`. Import `Slot` from `PySide6.QtCore` at the top of the file if not already present.

```python
    @Slot(object)
    def _on_render_ready(self, result: object) -> None:
        from fractal_studio.ui.workers.render_worker import RenderResult
        if not isinstance(result, RenderResult):
            return
        viewport = self.viewport
        if viewport is None or result.image is None:
            return
        viewport.store_rendered_image(result.image)
        viewport.update()
        if result.status:
            viewport.status_changed.emit(result.status)
```

### 4c: Add `render_scheduler` to adapter base and `build_sections_ports`

- [ ] **Step 6: Read `ui/src/fractal_studio/ui/sections/adapters/base.py`**

- [ ] **Step 7: Add `render_scheduler` to `_BasePortsAdapter`**

Update `_BasePortsAdapter.__init__` to accept a `render_scheduler` argument and expose it as a property:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile, CoreBackend
    from fractal_studio.ui.sections.state import MainWindowSectionsState
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
    from fractal_studio.viewport import FractalViewportWidget


class _BasePortsAdapter:
    def __init__(
        self,
        sections_state: MainWindowSectionsState,
        on_status: Callable[[str], None],
        backend: CoreBackend,
        backend_profile: BackendProfile,
        render_scheduler: RenderScheduler | None = None,
    ) -> None:
        self._state = sections_state
        self._on_status = on_status
        self._backend = backend
        self._backend_profile = backend_profile
        self._render_scheduler = render_scheduler

    @property
    def backend(self) -> CoreBackend:
        return self._backend

    @property
    def backend_profile(self) -> BackendProfile:
        return self._backend_profile

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._state.viewport.viewport

    @property
    def render_scheduler(self) -> RenderScheduler | None:
        return self._render_scheduler

    def show_status(self, message: str) -> None:
        self._on_status(message)
```

- [ ] **Step 8: Update `build_sections_ports` in `adapters/__init__.py`**

Read `ui/src/fractal_studio/ui/sections/adapters/__init__.py`. Add `render_scheduler` parameter and pass it through:

```python
def build_sections_ports(
    sections_state: MainWindowSectionsState,
    on_status: Callable[[str], None],
    backend: CoreBackend,
    backend_profile: BackendProfile,
    render_scheduler: RenderScheduler | None = None,
) -> MainWindowSectionsPorts:
    args = (sections_state, on_status, backend, backend_profile, render_scheduler)
    return MainWindowSectionsPorts(
        viewport=ViewportPanelPortsAdapter(*args),
        palette=PalettePanelPortsAdapter(*args),
        colormap=ColormapPanelPortsAdapter(*args),
        backend=BackendPanelPortsAdapter(*args),
        export=ExportPanelPortsAdapter(*args),
        favorites=FavoritesPanelPortsAdapter(*args),
        sidebar=SidebarPanelPortsAdapter(*args),
    )
```

Also add to the `TYPE_CHECKING` block:
```python
if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile, CoreBackend
    from fractal_studio.ui.sections.state import MainWindowSectionsState
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
```

### 4d: Pass scheduler to `FractalViewportWidget` via `sections.py`

- [ ] **Step 9: Read `ui/src/fractal_studio/viewport.py` `__init__` signature**

- [ ] **Step 10: Update `FractalViewportWidget.__init__`**

Change the signature to accept an optional scheduler and pass it to the controller:

```python
def __init__(
    self,
    backend: CoreBackend,
    scheduler: RenderScheduler | None = None,
    parent: QWidget | None = None,
) -> None:
    super().__init__(parent)
    self._backend = backend
    self._controller = ViewportController(backend, scheduler=scheduler)
    # ... rest unchanged
```

Add import at the top of `viewport.py` (inside `TYPE_CHECKING` to avoid circular import):
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
```

- [ ] **Step 11: Update `sections.py` to pass scheduler when building the viewport**

Read `ui/src/fractal_studio/ui/sections/sections.py`. Find where `FractalViewportWidget(ports.backend)` is constructed. Change to:

```python
viewport = FractalViewportWidget(ports.backend, scheduler=ports.render_scheduler)
```

### 4e: Wire everything in the factory

- [ ] **Step 12: Read `ui/src/fractal_studio/main_window_factory.py` in full**

- [ ] **Step 13: Update `create_main_window()` to create and wire the scheduler**

Add imports at the top of `main_window_factory.py`:
```python
from PySide6.QtCore import QThread
from fractal_studio.ui.workers.render_worker import RenderWorker
from fractal_studio.ui.workers.render_scheduler import RenderScheduler
```

In `create_main_window()`, after `backend_profile = backend.profile()` and before `window = MainWindow()`, add:

```python
    # ── Async render worker ──
    render_scheduler = RenderScheduler()
    render_worker = RenderWorker(backend)
    render_thread = QThread()
    render_worker.moveToThread(render_thread)
    render_scheduler.render_requested.connect(render_worker.do_render)
    render_worker.render_complete.connect(render_scheduler._on_result)
    render_thread.start()
```

Update the `build_sections_ports` call to pass the scheduler:
```python
    sections_ports = build_sections_ports(sections_state, on_status, backend, backend_profile, render_scheduler)
```

After building `viewport_state` and `sections_state`, connect the scheduler's result signal to the viewport panel state:
```python
    render_scheduler.render_ready.connect(viewport_state._on_render_ready)
```

At the end of `create_main_window()`, before `return window`, add teardown wiring. You need a reference to the app — get it from `QApplication.instance()`:
```python
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(render_thread.quit)
        app.aboutToQuit.connect(render_thread.wait)
```

- [ ] **Step 14: Run the startup smoke test**

```powershell
cd ui && python -m pytest tests/test_startup_smoke.py -v -m "unit or integration" 2>&1 | tail -10
```
Expected: all 3 tests PASS.

- [ ] **Step 15: Run the full test suite**

```powershell
cd ui && python -m pytest -m "unit or integration" --deselect tests/test_ui_redesign.py::TestColorCubeEditor::test_mouse_press_adds_point_and_hover_status -q 2>&1 | tail -5
```
Expected: all pass.

- [ ] **Step 16: Smoke test the app**

```powershell
timeout 8 python -c "from fractal_studio.app import main; main()" 2>&1; echo "exit:$?"
```
Expected: `exit:124` (killed by timeout — meaning it ran cleanly for 8 seconds).

- [ ] **Step 17: Commit**

```powershell
git add ui/src/fractal_studio/ui/controllers/viewport_controller.py ui/src/fractal_studio/viewport.py ui/src/fractal_studio/ui/sections/adapters/base.py ui/src/fractal_studio/ui/sections/adapters/__init__.py ui/src/fractal_studio/ui/sections/sections.py ui/src/fractal_studio/ui/sections/panel_state.py ui/src/fractal_studio/main_window_factory.py
git commit -m "feat: wire RenderScheduler and RenderWorker into viewport rendering path"
```

---

## Task 5: Create `ExportRunner`

**Files:**
- Create: `ui/src/fractal_studio/ui/workers/export_runner.py`
- Test: `ui/tests/test_render_workers.py`

`ExportRunner` is a `QObject` that runs a single export job on a background thread.

- [ ] **Step 1: Write the failing test**

Append to `ui/tests/test_render_workers.py`:

```python
@pytest.mark.integration
def test_export_runner_emits_bytes_on_success() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    from fractal_studio.backend import CoreBackend
    from fractal_studio.services.export_service import ExportService
    from fractal_studio.state import ViewportState, StandardParams
    from fractal_studio.ui.workers.export_runner import ExportRunner

    _app = QApplication.instance() or QApplication([])

    backend = CoreBackend(None)  # null — returns b""
    service = ExportService(backend)
    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    runner = ExportRunner(service, state, palette=[(0, 0, 0)], width=4, height=4)
    thread = QThread()
    runner.moveToThread(thread)
    thread.started.connect(runner.run)

    results = []
    runner.export_done.connect(results.append)
    runner.export_done.connect(thread.quit)
    thread.start()
    thread.wait(2000)

    assert len(results) == 1
    # Null backend returns b"" which ExportService maps to None
    assert results[0] is None


@pytest.mark.integration
def test_export_runner_emits_status_signal() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    from fractal_studio.backend import CoreBackend
    from fractal_studio.services.export_service import ExportService
    from fractal_studio.state import ViewportState, StandardParams
    from fractal_studio.ui.workers.export_runner import ExportRunner

    _app = QApplication.instance() or QApplication([])

    backend = CoreBackend(None)
    service = ExportService(backend)
    state = ViewportState(
        formula="standard", center_x=0.0, center_y=0.0, scale=3.0,
        max_iterations=64, is_julia=False, formula_params=StandardParams(),
        coloring_mode="smooth_escape", palette_offset=0.0,
    )
    runner = ExportRunner(service, state, palette=[(0, 0, 0)], width=4, height=4)
    thread = QThread()
    runner.moveToThread(thread)
    thread.started.connect(runner.run)

    statuses = []
    runner.status_changed.connect(statuses.append)
    runner.export_done.connect(thread.quit)
    thread.start()
    thread.wait(2000)

    # Null backend triggers "Backend not available" status message
    assert any("not available" in s.lower() for s in statuses)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_export_runner_emits_bytes_on_success tests/test_render_workers.py::test_export_runner_emits_status_signal -v -m "unit or integration" 2>&1 | tail -10
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `export_runner.py`**

Create `ui/src/fractal_studio/ui/workers/export_runner.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from fractal_studio.state import ViewportState

if TYPE_CHECKING:
    from fractal_studio.services.export_service import ExportService


class ExportRunner(QObject):
    export_done = Signal(object)   # bytes | None
    status_changed = Signal(str)

    def __init__(
        self,
        export_service: ExportService,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None:
        super().__init__()
        self._service = export_service
        self._viewport_state = viewport_state
        self._palette = list(palette)
        self._width = width
        self._height = height

    @Slot()
    def run(self) -> None:
        raw = self._service.export_render(
            viewport_state=self._viewport_state,
            palette=self._palette,
            width=self._width,
            height=self._height,
            set_status=self._emit_status,
        )
        self.export_done.emit(raw)

    def _emit_status(self, message: str) -> None:
        self.status_changed.emit(message)
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
cd ui && python -m pytest tests/test_render_workers.py::test_export_runner_emits_bytes_on_success tests/test_render_workers.py::test_export_runner_emits_status_signal -v -m "unit or integration" 2>&1 | tail -10
```
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui/src/fractal_studio/ui/workers/export_runner.py ui/tests/test_render_workers.py
git commit -m "feat: add ExportRunner for background export jobs"
```

---

## Task 6: Wire async export into `ExportController` and panel state

**Files:**
- Modify: `ui/src/fractal_studio/application/controllers/export_controller.py`
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py`

### 6a: Update `ExportController`

`ExportController` currently has `export_render()` which returns `bytes | None` synchronously. After this task it returns `None` and owns the background thread lifecycle.

- [ ] **Step 1: Read `export_controller.py` in full**

- [ ] **Step 2: Add async export to `ExportController`**

Add imports to `export_controller.py`:
```python
from PySide6.QtCore import QThread, Slot
```

Add instance variables to `__init__`:
```python
    def __init__(self, export_service: ExportService) -> None:
        self._export_service = export_service
        self._export_thread: QThread | None = None
        self._export_runner = None
```

Add a new `start_export()` method (the new async entry point) and `_on_export_done()` slot. Keep the existing `export_render()` unchanged for now (it is used by `_do_export` in panel_state which we update in step 6b):

```python
    def start_export(
        self,
        viewport_state: ViewportState | None,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        on_done: Callable[[bytes | None], None],
        on_status: Callable[[str], None],
    ) -> bool:
        """Start a background export. Returns False if an export is already running."""
        if viewport_state is None:
            return False
        if self._export_thread is not None and self._export_thread.isRunning():
            on_status("Export already in progress.")
            return False

        from fractal_studio.ui.workers.export_runner import ExportRunner

        self._export_runner = ExportRunner(
            self._export_service, viewport_state, palette, width, height
        )
        self._export_thread = QThread()
        self._export_runner.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._export_runner.run)
        self._export_runner.export_done.connect(on_done)
        self._export_runner.status_changed.connect(on_status)
        self._export_runner.export_done.connect(self._export_thread.quit)
        self._export_thread.finished.connect(self._cleanup_export_thread)
        self._export_thread.start()
        return True

    @Slot()
    def _cleanup_export_thread(self) -> None:
        self._export_runner = None
        self._export_thread = None
```

### 6b: Update `MainWindowExportState._do_export()`

`_do_export` currently calls `self._controller.export_render()` (synchronous) then saves the QImage. After this step it calls `self._controller.start_export()` and the QImage save happens in the `on_done` callback on the main thread.

- [ ] **Step 3: Read `MainWindowExportState._do_export()` in `panel_state.py`**

- [ ] **Step 4: Replace `_do_export` in `MainWindowExportState`**

Replace the entire `_do_export` method with:

```python
    def _do_export(
        self,
        viewport_state: object,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        on_status: Callable[[str], None],
    ) -> None:
        from fractal_studio.state import ViewportState
        from PySide6.QtGui import QImage

        if self._controller is None or not isinstance(viewport_state, ViewportState):
            return

        path_str, _ = QFileDialog.getSaveFileName(
            None,
            f"Export {width}×{height} render",
            str(Path.cwd() / f"fractal_{width}x{height}.png"),
            "PNG Image (*.png)",
        )
        if not path_str:
            return

        def on_done(raw: bytes | None) -> None:
            if raw:
                image = QImage(
                    raw, width, height, width * 4, QImage.Format.Format_RGBA8888
                ).copy()
                image.save(path_str)
                on_status(f"Saved {width}×{height} render to {path_str}")

        self._controller.start_export(
            viewport_state=viewport_state,
            palette=palette,
            width=width,
            height=height,
            on_done=on_done,
            on_status=on_status,
        )
```

- [ ] **Step 5: Run full test suite**

```powershell
cd ui && python -m pytest -m "unit or integration" --deselect tests/test_ui_redesign.py::TestColorCubeEditor::test_mouse_press_adds_point_and_hover_status -q 2>&1 | tail -5
```
Expected: all pass.

- [ ] **Step 6: Smoke test the app**

```powershell
timeout 8 python -c "from fractal_studio.app import main; main()" 2>&1; echo "exit:$?"
```
Expected: `exit:124`

- [ ] **Step 7: Commit**

```powershell
git add ui/src/fractal_studio/application/controllers/export_controller.py ui/src/fractal_studio/ui/sections/panel_state.py
git commit -m "feat: async export via ExportRunner; ExportController.start_export() replaces blocking export"
```

---

## Self-Review

**Spec coverage:**
- `RenderRequest` frozen dataclass in `state.py`: Task 1 ✓
- `RenderResult` frozen dataclass (in `render_worker.py`): Task 2 ✓
- `RenderWorker` with `do_render` slot and `render_complete` signal: Task 2 ✓
- `RenderScheduler` with 50ms debounce, generation counter, stale-drop: Task 3 ✓
- `ViewportController.render()` non-blocking via scheduler: Task 4 ✓
- Fallback synchronous render when no scheduler (for tests): Task 4 ✓
- `MainWindowViewportState._on_render_ready()` slot: Task 4 ✓
- Scheduler threaded through `_BasePortsAdapter`/`build_sections_ports`: Task 4 ✓
- `FractalViewportWidget` accepts scheduler: Task 4 ✓
- Factory creates thread/worker/scheduler, wires signals, teardown on quit: Task 4 ✓
- `ExportRunner` with `export_done` and `status_changed` signals: Task 5 ✓
- `ExportController.start_export()` with double-export guard: Task 6 ✓
- `_do_export` async, QImage save in `on_done` callback: Task 6 ✓
- Unit tests for `RenderRequest`, `RenderResult`, stale-drop, debounce: Tasks 1–3 ✓
- Integration tests for worker round-trip, export runner: Tasks 2, 5 ✓

**Placeholder scan:** None found.

**Type consistency:**
- `RenderRequest` defined in Task 1, used in Tasks 2, 3, 4 — consistent.
- `RenderResult` defined in Task 2 (`render_worker.py`), used in Task 3 (scheduler imports it), Task 4 (`_on_render_ready` parameter) — consistent.
- `render_scheduler: RenderScheduler | None` parameter added to `_BasePortsAdapter.__init__` in Task 4 — same type used throughout.
- `start_export()` signature defined in Task 6a, called in Task 6b — consistent.

**Note on `_emit_status` in `ExportRunner`**: `run()` is called from a worker thread. `_emit_status` emits a signal — since `status_changed` is connected in the main thread via a queued connection (default for cross-thread), this is thread-safe. No explicit `Qt.ConnectionType.QueuedConnection` needed; Qt detects the cross-thread case automatically.
