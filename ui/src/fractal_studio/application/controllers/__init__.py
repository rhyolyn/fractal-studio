"""
Controllers — stateless atoms of domain logic.

Rules:
- No mutable state after __init__ (only injected dependencies).
- No direct QWidget references; accept widgets as method arguments only.
- May reference repositories, services, and other controllers.
- One controller per domain concept.
"""
from fractal_studio.application.controllers.export_controller import ExportController
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)
from fractal_studio.application.controllers.settings_controller import (
    SettingsController,
    SettingsDialogFactory,
)
from fractal_studio.application.controllers.theme_controller import ThemeController

__all__ = [
    "ExportController",
    "FavoritesController",
    "SettingsController",
    "SettingsDialogFactory",
    "ThemeController",
]
