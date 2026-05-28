from __future__ import annotations

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
    from fractal_studio.main_window import MainWindow


def build_sections_ports(owner: MainWindow) -> MainWindowSectionsPorts:
    return MainWindowSectionsPorts(
        viewport=ViewportPanelPortsAdapter(owner),
        palette=PalettePanelPortsAdapter(owner),
        colormap=ColormapPanelPortsAdapter(owner),
        backend=BackendPanelPortsAdapter(owner),
        export=ExportPanelPortsAdapter(owner),
        favorites=FavoritesPanelPortsAdapter(owner),
        sidebar=SidebarPanelPortsAdapter(owner),
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
