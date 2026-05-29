from __future__ import annotations

import importlib

import pytest


CANONICAL_MODULES = (
    "fractal_studio.application.controllers",
    "fractal_studio.application.controllers.favorites_controller",
    "fractal_studio.application.controllers.export_controller",
    "fractal_studio.application.controllers.theme_controller",
    "fractal_studio.application.coordinators",
    "fractal_studio.application.coordinators.export_panel_coordinator",
    "fractal_studio.application.coordinators.favorites_panel_coordinator",
    "fractal_studio.application.coordinators.palette_panel_coordinator",
    "fractal_studio.application.coordinators.palette_preview_coordinator",
    "fractal_studio.application.coordinators.settings_dialog_coordinator",
    "fractal_studio.application.coordinators.sidebar_wiring_coordinator",
    "fractal_studio.application.workflows",
    "fractal_studio.application.workflows.favorites_workflow_coordinator",
    "fractal_studio.application.workflows.startup_coordinator",
    "fractal_studio.application.workflows.theme_workflow_coordinator",
    "fractal_studio.services",
    "fractal_studio.services.export_service",
    "fractal_studio.services.palette_service",
    "fractal_studio.services.settings_service",
    "fractal_studio.ui.controllers",
    "fractal_studio.ui.controllers.editor_controller",
    "fractal_studio.ui.controllers.params_panel_controller",
    "fractal_studio.ui.controllers.viewport_controller",
    "fractal_studio.ui.dialogs",
    "fractal_studio.ui.dialogs.appearance_settings_dialog",
    "fractal_studio.ui.dialogs.custom_resolution_dialog",
    "fractal_studio.ui.presenters",
    "fractal_studio.ui.presenters.favorite_hover_presenter",
    "fractal_studio.ui.presenters.favorite_row_style_presenter",
    "fractal_studio.ui.sections",
    "fractal_studio.ui.sections.sections",
    "fractal_studio.ui.sections.adapters",
    "fractal_studio.ui.sections.adapters.backend_adapter",
    "fractal_studio.ui.sections.adapters.base",
    "fractal_studio.ui.sections.adapters.colormap_adapter",
    "fractal_studio.ui.sections.adapters.export_adapter",
    "fractal_studio.ui.sections.adapters.favorites_adapter",
    "fractal_studio.ui.sections.adapters.palette_adapter",
    "fractal_studio.ui.sections.adapters.sidebar_adapter",
    "fractal_studio.ui.sections.adapters.viewport_adapter",
    "fractal_studio.ui.sections.mediator",
    "fractal_studio.ui.sections.panel_state",
    "fractal_studio.ui.sections.ports",
    "fractal_studio.ui.sections.state",
    "fractal_studio.ui.widgets",
    "fractal_studio.ui.widgets.favorite_thumbnail_row",
    "fractal_studio.ui.widgets.placeholder_panel",
)


@pytest.mark.integration
def test_canonical_package_layout_imports() -> None:
    for module_name in CANONICAL_MODULES:
        module = importlib.import_module(module_name)
        assert module is not None, f"failed to import {module_name}"
