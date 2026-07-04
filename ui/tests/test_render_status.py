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
