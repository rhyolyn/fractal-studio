from __future__ import annotations

from typing import TYPE_CHECKING

from fractal_studio.ui.sections.backend_adapter import (
    BackendPanelPortsAdapter,
)
from fractal_studio.ui.sections.colormap_adapter import (
    ColormapPanelPortsAdapter,
)
from fractal_studio.ui.sections.export_adapter import (
    ExportPanelPortsAdapter,
)
from fractal_studio.ui.sections.favorites_adapter import (
    FavoritesPanelPortsAdapter,
)
from fractal_studio.ui.sections.palette_adapter import (
    PalettePanelPortsAdapter,
)
from fractal_studio.ui.sections.ports import (
    MainWindowSectionsPorts,
)
from fractal_studio.ui.sections.sidebar_adapter import (
    SidebarPanelPortsAdapter,
)
from fractal_studio.ui.sections.viewport_adapter import (
    ViewportPanelPortsAdapter,
)

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
