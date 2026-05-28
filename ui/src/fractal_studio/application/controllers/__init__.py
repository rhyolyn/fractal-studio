"""
Controllers — stateless atoms of domain logic.

Rules:
- No mutable state after __init__ (only injected dependencies).
- No direct QWidget references; accept widgets as method arguments only.
- May reference repositories, services, and other controllers.
- One controller per domain concept.
"""
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)
from fractal_studio.application.controllers.main_window_controller import (
    MainWindowController,
    SettingsDialogFactory,
)
from fractal_studio.application.controllers.theme_controller import ThemeController

__all__ = [
    "FavoritesController",
    "MainWindowController",
    "SettingsDialogFactory",
    "ThemeController",
]
