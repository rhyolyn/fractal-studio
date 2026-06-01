# Async Rendering Design Spec

**Date:** 2026-05-31
**Status:** Approved
**Scope:** Python UI layer — viewport rendering and export only
**Out of scope:** Rust core changes, cancellation, progress bars, tiled export

---

## Problem

`ViewportController.render()` and `ExportService.export_render()` both call `backend.render_fractal()` synchronously from the Qt event loop. This blocks the UI thread for the duration of every render — visibly on deep zooms, severely on large exports. Rapid parameter changes also queue stale work with no mechanism to discard it.

---

## New types

Two frozen dataclasses added to `ui/src/fractal_studio/state.py`:

```python
@dataclass(frozen=True)
class RenderRequest:
    generation: int
    viewport_state: ViewportState
    palette: list[tuple[int, int, int]]
    width: int
    height: int
```

```python
@dataclass(frozen=True)
class RenderResult:
    generation: int
    image: QImage | None
    status: str | None
```

`generation` is a monotonically increasing integer managed by `RenderScheduler`. It is the mechanism for stale-result rejection: results whose generation does not match the current counter are silently dropped.

---

## New module

```
ui/src/fractal_studio/ui/workers/
    __init__.py
    render_worker.py    — RenderWorker
    render_scheduler.py — RenderScheduler
    export_runner.py    — ExportRunner
```

---

## Components

### RenderWorker

```python
class RenderWorker(QObject):
    render_complete = Signal(RenderResult)

    def __init__(self, backend: CoreBackend) -> None: ...

    @Slot(RenderRequest)
    def do_render(self, request: RenderRequest) -> None: ...
```

Lives permanently in a `QThread` created at app startup. `do_render` is connected to `RenderScheduler.render_requested` via a **queued** connection — Qt automatically marshals the call across threads.

`do_render` calls `backend.render_fractal(...)` with the data from `request`, wraps the raw bytes in a `QImage`, computes the status string, and emits `render_complete(result)`. If the backend returns empty bytes (null object), it emits a result with `image=None` and `status=None`.

The worker holds no Qt widgets and performs no widget operations. It is safe to call from a non-UI thread.

### RenderScheduler

```python
class RenderScheduler(QObject):
    render_requested = Signal(RenderRequest)
    render_ready = Signal(RenderResult)

    def __init__(self) -> None: ...

    def schedule(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None: ...

    @Slot(RenderResult)
    def _on_result(self, result: RenderResult) -> None: ...
```

Lives on the main thread. Contains a `_generation: int` counter and a `QTimer` for debouncing.

**`schedule()`** restarts the debounce timer (50 ms). The timer's timeout slot increments `_generation`, creates a `RenderRequest`, and emits `render_requested(request)`. Because the signal is connected to `RenderWorker.do_render` via a queued connection, the request is delivered to the worker thread's event queue without blocking the main thread.

**`_on_result()`** is connected to `RenderWorker.render_complete`. It checks `result.generation == self._generation`. If stale, it returns without action. If current, it emits `render_ready(result)`.

### ExportRunner

```python
class ExportRunner(QObject):
    export_done = Signal(object)  # bytes | None
    status_changed = Signal(str)

    def __init__(
        self,
        export_service: ExportService,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
    ) -> None: ...

    @Slot()
    def run(self) -> None: ...
```

Created per export, moved to a short-lived `QThread`. `run()` calls `ExportService.export_render(...)` and emits `export_done(raw)`. Status updates during export are emitted via a dedicated `status_changed = Signal(str)` on `ExportRunner`. The panel state connects this signal to its `on_status` callback before starting the thread — Qt's queued connection delivers it safely to the main thread. `ExportRunner` does not call `set_status` directly.

---

## Viewport wiring changes

### `ViewportController`

`render(widget)` is renamed `schedule_render(widget)` and becomes non-blocking:

```python
def schedule_render(self, widget: _ViewportAdapter) -> None:
    if not self._scheduler:
        return
    palette = widget.palette()
    if not palette:
        return
    self._scheduler.schedule(
        viewport_state=widget.to_state(),
        palette=palette,
        width=max(1, widget.width()),
        height=max(1, widget.height()),
    )
```

`ViewportController.__init__` gains a `scheduler: RenderScheduler | None = None` parameter. All call sites that previously called `self.render(widget)` now call `self.schedule_render(widget)`.

### `MainWindowViewportState`

Gains a `_on_render_ready(result: RenderResult)` slot connected to `scheduler.render_ready`. This slot performs what `ViewportController.render()` used to do inline:

```python
def _on_render_ready(self, result: RenderResult) -> None:
    viewport = self._viewport_getter()
    if viewport is None or result.image is None:
        return
    viewport.store_rendered_image(result.image)
    viewport.update()
    if result.status:
        viewport.status_changed.emit(result.status)
```

### Factory wiring in `create_main_window()`

```python
# After panel states, before sections ports:
render_thread = QThread()
render_worker = RenderWorker(backend)
render_worker.moveToThread(render_thread)
render_scheduler = RenderScheduler()
render_scheduler.render_requested.connect(render_worker.do_render)
render_worker.render_complete.connect(render_scheduler._on_result)
render_thread.start()

# Pass scheduler to viewport controller:
viewport_controller = ViewportController(backend, scheduler=render_scheduler)

# Connect scheduler result to viewport panel state:
render_scheduler.render_ready.connect(viewport_state._on_render_ready)

# Ensure clean teardown:
app.aboutToQuit.connect(render_thread.quit)
app.aboutToQuit.connect(render_thread.wait)
```

---

## Export wiring changes

### `ExportController`

`export_render()` gains state to track a running export thread. The file dialog runs synchronously on the UI thread (required). After a path is chosen, execution is handed off to a background thread:

```python
def export_render(
    self,
    parent: QWidget,
    viewport_state: ViewportState | None,
    palette: list[tuple[int, int, int]],
    width: int,
    height: int,
    set_status: Callable[[str], None],
    save_image: Callable[[bytes, str], None],
) -> None:
    if viewport_state is None:
        return
    if self._export_thread is not None and self._export_thread.isRunning():
        set_status("Export already in progress.")
        return

    path, _ = QFileDialog.getSaveFileName(
        parent,
        f"Export {width}×{height} render",
        str(Path.cwd() / f"fractal_{width}x{height}.png"),
        "PNG Image (*.png)",
    )
    if not path:
        return

    self._pending_save = (path, save_image, set_status, width, height)
    self._export_thread = QThread()
    self._export_runner = ExportRunner(
        self._export_service, viewport_state, palette, width, height, set_status
    )
    self._export_runner.moveToThread(self._export_thread)
    self._export_thread.started.connect(self._export_runner.run)
    self._export_runner.export_done.connect(self._on_export_done)
    self._export_runner.export_done.connect(self._export_thread.quit)
    self._export_thread.finished.connect(self._export_thread.deleteLater)
    self._export_thread.start()

def _on_export_done(self, raw: bytes | None) -> None:
    if self._pending_save is None:
        return
    path, save_image, set_status, width, height = self._pending_save
    self._pending_save = None
    self._export_runner = None
    self._export_thread = None
    if raw:
        save_image(raw, path)
        set_status(f"Saved {width}×{height} render to {path}")
```

`save_image` is a callable passed from the panel state that wraps `QImage(...).copy().save(path)`. This keeps Qt out of `ExportController`.

The panel state's export callback assembles the `save_image` lambda and calls the controller. The controller never creates a `QImage` directly.

---

## Testing

### Unit tests — no Qt required

- `RenderRequest` and `RenderResult` are frozen; mutation raises
- `RenderScheduler` generation counter: two rapid `schedule()` calls produce one `render_requested` emission (after debounce) with the higher generation
- `RenderScheduler._on_result()` with a stale generation emits nothing

### Integration tests — Qt required

- Worker round-trip: `schedule()` → `render_complete` → `render_ready` fires with correct generation
- Stale drop: two `schedule()` calls with fake worker; confirm only the second generation's result triggers `render_ready`
- Export guard: `export_render()` called twice in rapid succession; second call returns with "already in progress" status, only one `export_done` fires

---

## Files changed

| Action | File | Change |
|---|---|---|
| Modify | `ui/src/fractal_studio/state.py` | Add `RenderRequest`, `RenderResult` |
| Create | `ui/src/fractal_studio/ui/workers/__init__.py` | Empty |
| Create | `ui/src/fractal_studio/ui/workers/render_worker.py` | `RenderWorker` |
| Create | `ui/src/fractal_studio/ui/workers/render_scheduler.py` | `RenderScheduler` |
| Create | `ui/src/fractal_studio/ui/workers/export_runner.py` | `ExportRunner` |
| Modify | `ui/src/fractal_studio/ui/controllers/viewport_controller.py` | `render()` → `schedule_render()`; accept `scheduler` param |
| Modify | `ui/src/fractal_studio/ui/sections/panel_state.py` | `_on_render_ready` slot on `MainWindowViewportState` |
| Modify | `ui/src/fractal_studio/application/controllers/export_controller.py` | Async export flow; `_export_thread`, `_export_runner`, `_on_export_done` |
| Modify | `ui/src/fractal_studio/main_window_factory.py` | Create thread, worker, scheduler; wire signals; thread teardown |
| Create | `ui/tests/test_render_workers.py` | Unit + integration tests for the new components |
