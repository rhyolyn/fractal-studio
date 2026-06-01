from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
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


@pytest.mark.unit
def test_render_result_is_frozen() -> None:
    import dataclasses
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


@pytest.mark.integration
def test_scheduler_drops_stale_results() -> None:
    from PySide6.QtWidgets import QApplication
    from fractal_studio.state import ViewportState, StandardParams
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
    from fractal_studio.ui.workers.render_worker import RenderResult

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
