"""
Coordinators — boundary layer for each UI panel's use cases.

Rules:
- One coordinator per UI panel section; it owns all orchestration for that panel.
- Thin coordinators are intentional: they represent a panel whose use cases haven't
  grown complex yet. Do not delete them.
- May reference controllers, services, and port protocols.
- Must not subclass QWidget or hold direct widget references.
"""
from fractal_studio.application.coordinators.export_panel_coordinator import (
    ExportPanelCoordinator,
)
from fractal_studio.application.coordinators.favorites_panel_coordinator import (
    FavoritesPanelCoordinator,
)
from fractal_studio.application.coordinators.palette_panel_coordinator import (
    PalettePanelCoordinator,
)
from fractal_studio.application.coordinators.palette_preview_coordinator import (
    PalettePreviewCoordinator,
)
from fractal_studio.application.coordinators.settings_dialog_coordinator import (
    SettingsDialogCoordinator,
)
from fractal_studio.application.coordinators.sidebar_wiring_coordinator import (
    SidebarWiringCoordinator,
)

__all__ = [
    "ExportPanelCoordinator",
    "FavoritesPanelCoordinator",
    "PalettePanelCoordinator",
    "PalettePreviewCoordinator",
    "SettingsDialogCoordinator",
    "SidebarWiringCoordinator",
]
