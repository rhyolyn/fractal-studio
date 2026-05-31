from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from fractal_studio.ui.sections.adapters.backend_adapter import BackendPanelPortsAdapter
from fractal_studio.ui.sections.adapters.colormap_adapter import ColormapPanelPortsAdapter
from fractal_studio.ui.sections.adapters.export_adapter import ExportPanelPortsAdapter
from fractal_studio.ui.sections.adapters.favorites_adapter import FavoritesPanelPortsAdapter
from fractal_studio.ui.sections.adapters.palette_adapter import PalettePanelPortsAdapter
from fractal_studio.ui.sections.adapters.sidebar_adapter import SidebarPanelPortsAdapter
from fractal_studio.ui.sections.adapters.viewport_adapter import ViewportPanelPortsAdapter
from fractal_studio.ui.sections.ports import MainWindowSectionsPorts

if TYPE_CHECKING:
    from fractal_studio.ui.sections.state import MainWindowSectionsState


def build_sections_ports(
    sections_state: MainWindowSectionsState,
    on_status: Callable[[str], None],
) -> MainWindowSectionsPorts:
    return MainWindowSectionsPorts(
        viewport=ViewportPanelPortsAdapter(sections_state, on_status),
        palette=PalettePanelPortsAdapter(sections_state, on_status),
        colormap=ColormapPanelPortsAdapter(sections_state, on_status),
        backend=BackendPanelPortsAdapter(sections_state, on_status),
        export=ExportPanelPortsAdapter(sections_state, on_status),
        favorites=FavoritesPanelPortsAdapter(sections_state, on_status),
        sidebar=SidebarPanelPortsAdapter(sections_state, on_status),
    )


__all__ = [
    "BackendPanelPortsAdapter",
    "ColormapPanelPortsAdapter",
    "ExportPanelPortsAdapter",
    "FavoritesPanelPortsAdapter",
    "PalettePanelPortsAdapter",
    "SidebarPanelPortsAdapter",
    "ViewportPanelPortsAdapter",
    "build_sections_ports",
]
