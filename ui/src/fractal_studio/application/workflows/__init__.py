"""
Workflows — user-visible multi-step operations.

Rules:
- Each workflow corresponds to one named user action (save favorite, change theme,
  startup). Named after the action, not the panel.
- Workflows cross panel boundaries and produce UI feedback (status messages, dialogs).
- Workflows may call coordinators and controllers; they are the top of the
  application logic stack.
"""
from fractal_studio.application.workflows.favorites_workflow_coordinator import (
    FavoritesWorkflowCoordinator,
)
from fractal_studio.application.workflows.startup_coordinator import (
    WindowStartupCoordinator,
    WindowStartupState,
)
from fractal_studio.application.workflows.theme_workflow_coordinator import (
    ThemeWorkflowCoordinator,
)

__all__ = [
    "FavoritesWorkflowCoordinator",
    "ThemeWorkflowCoordinator",
    "WindowStartupCoordinator",
    "WindowStartupState",
]
