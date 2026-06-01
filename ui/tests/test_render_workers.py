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
