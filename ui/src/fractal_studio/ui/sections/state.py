from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from fractal_studio.ui.sections.panel_state import (
    MainWindowColormapState,
    MainWindowExportState,
    MainWindowFavoritesState,
    MainWindowPaletteState,
    MainWindowSidebarState,
    MainWindowViewportState,
)


@dataclass
class MainWindowSectionsState:
    viewport: MainWindowViewportState
    sidebar: MainWindowSidebarState
    palette: MainWindowPaletteState
    colormap: MainWindowColormapState
    favorites: MainWindowFavoritesState
    export: MainWindowExportState

    def validate(self) -> None:
        for f in dataclasses.fields(self):
            if getattr(self, f.name) is None:
                raise RuntimeError(
                    f"MainWindowSectionsState.validate(): '{f.name}' is None."
                )
