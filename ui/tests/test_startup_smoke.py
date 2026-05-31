from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from fractal_studio.backend import CoreBackend, default_profile
from fractal_studio.ui.sections.adapters import build_sections_ports
from fractal_studio.ui.sections.panel_state import (
    MainWindowColormapState,
    MainWindowExportState,
    MainWindowFavoritesState,
    MainWindowPaletteState,
    MainWindowSidebarState,
    MainWindowViewportState,
)
from fractal_studio.ui.sections.state import MainWindowSectionsState


def _make_sections_state() -> MainWindowSectionsState:
    return MainWindowSectionsState(
        viewport=MainWindowViewportState(),
        sidebar=MainWindowSidebarState(),
        palette=MainWindowPaletteState(),
        colormap=MainWindowColormapState(),
        favorites=MainWindowFavoritesState(),
        export=MainWindowExportState(),
    )


@pytest.mark.unit
def test_build_sections_ports_exposes_backend_and_profile() -> None:
    backend = CoreBackend(None)
    profile = default_profile()
    state = _make_sections_state()

    ports = build_sections_ports(state, lambda _: None, backend, profile)

    assert ports.viewport.backend is backend
    assert ports.colormap.backend is backend
    assert ports.colormap.backend_profile is profile


@pytest.mark.unit
def test_adapter_attribute_names_match_sections_state_fields() -> None:
    """Adapters access sections_state via named fields — catch renames that break the wiring."""
    backend = CoreBackend(None)
    profile = default_profile()
    state = _make_sections_state()

    ports = build_sections_ports(state, lambda _: None, backend, profile)

    # Exercise every adapter property that delegates into sections_state fields.
    # If a field was renamed (e.g. _viewport_state -> viewport) these will raise AttributeError.
    assert ports.viewport.backend is backend
    assert ports.colormap.viewport is None  # no widget set yet — returns None, not AttributeError
    _ = ports.sidebar  # constructing the adapter is enough to verify field access


@pytest.mark.integration
def test_create_main_window_launches_without_error() -> None:
    """Full factory smoke test — catches any startup wiring regression."""
    _app = QApplication.instance() or QApplication([])

    from fractal_studio.main_window_factory import create_main_window

    window = create_main_window()
    assert window is not None
    window.close()
