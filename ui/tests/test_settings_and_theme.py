from __future__ import annotations

import gc
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path

import pytest

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QComboBox, QSpinBox
from tests.support import (
    DummyEditorBackend,
    DummyPaletteBackend,
    DummyUnavailableBackend,
    QtWindowTestCase,
    _FULL_CAPS,
    get_app,
)


@pytest.mark.integration
class TestAppearanceSettings(QtWindowTestCase):
    def setUp(self) -> None:
        import fractal_studio.main_window_factory as mwmod

        self._mwmod = mwmod
        self._original_settings_path = mwmod._SETTINGS_PATH
        self._original_favorites_path = mwmod._FAVORITES_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_test_settings_"))
        mwmod._SETTINGS_PATH = self._tmpdir / "settings.json"
        mwmod._FAVORITES_PATH = self._tmpdir / "favorites.json"

    def tearDown(self) -> None:
        self._mwmod._SETTINGS_PATH = self._original_settings_path
        self._mwmod._FAVORITES_PATH = self._original_favorites_path

    def test_appearance_dialog_lists_requested_themes(self) -> None:
        from fractal_studio.ui.dialogs.appearance_settings_dialog import (
            AppearanceSettingsDialog,
        )
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QRadioButton

        dialog = AppearanceSettingsDialog("dark")
        preview_requests: list[str] = []
        dialog.theme_preview_requested.connect(preview_requests.append)

        buttons = {
            button.text().lower(): button
            for button in dialog.findChildren(QRadioButton)
        }
        self.assertSetEqual(set(buttons), {"light", "dark", "sepia"})
        self.assertTrue(all(button.isEnabled() for button in buttons.values()))
        self.assertEqual(dialog.selected_theme(), "dark")

        dialog.show()
        QTest.mouseClick(
            buttons["sepia"],
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(10, 10),
        )
        self.assertEqual(dialog.selected_theme(), "sepia")
        self.assertIn("sepia", preview_requests)

    def test_theme_change_persists_to_settings_file(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.state import UiSettings

        SettingsRepository(self._mwmod._SETTINGS_PATH).save(UiSettings(theme="sepia"))

        w = self.make_window()
        self.assertEqual(w._theme_name, "sepia")
        stored = json.loads(self._mwmod._SETTINGS_PATH.read_text())
        self.assertEqual(stored.get("version"), 1)
        self.assertEqual(stored.get("data", {}).get("theme"), "sepia")

    def test_missing_settings_defaults_to_light_theme(self) -> None:
        w = self.make_window()
        self.assertEqual(w._theme_name, "light")

    def test_preview_does_not_persist_settings(self) -> None:
        from fractal_studio.application.coordinators.settings_dialog_coordinator import (
            SettingsDialogCoordinator,
        )

        class ControllerStub:
            def open_settings_dialog(self, **kwargs) -> None:
                pass

        class SettingsServiceStub:
            def apply_theme_name(self, **kwargs):
                kwargs["apply_theme_to_app"](kwargs["theme_name"])
                return kwargs["theme_name"]

        coordinator = SettingsDialogCoordinator(ControllerStub(), SettingsServiceStub())
        applied: list[str] = []
        persisted: list[str] = []
        refreshed: list[bool] = []

        result = coordinator.apply_theme_name(
            theme_name="dark",
            persist=False,
            current_theme="light",
            apply_theme_to_app=applied.append,
            persist_theme=persisted.append,
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(result, "dark")
        self.assertEqual(applied, ["dark"])
        self.assertEqual(persisted, [])
        self.assertEqual(refreshed, [True])

    def test_legacy_settings_file_is_still_supported(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text(json.dumps({"theme": "dark"}))
        w = self.make_window()
        self.assertEqual(w._theme_name, "dark")
        self.assertIn("legacy settings", w.statusBar().currentMessage().lower())

    def test_versioned_settings_file_is_supported(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text(
            json.dumps({"version": 1, "data": {"theme": "sepia"}})
        )
        w = self.make_window()
        self.assertEqual(w._theme_name, "sepia")

    def test_invalid_settings_file_reports_fallback_diagnostic(self) -> None:
        self._mwmod._SETTINGS_PATH.write_text("not json")
        w = self.make_window()
        self.assertIn(
            "ignored invalid settings file", w.statusBar().currentMessage().lower()
        )

    def test_invalid_favorites_file_reports_fallback_diagnostic(self) -> None:
        self._mwmod._FAVORITES_PATH.write_text("not json")
        w = self.make_window()
        self.assertIn(
            "ignored invalid favorites file", w.statusBar().currentMessage().lower()
        )


@pytest.mark.integration
class TestSettingsWorkflowService(unittest.TestCase):
    def test_backend_state_message_reports_loaded_backend(self) -> None:
        from fractal_studio.services.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.backend_state_message(True, True)

        self.assertEqual(result, "Rust extension loaded.")

    def test_startup_message_reports_legacy_settings(self) -> None:
        from fractal_studio.persistence import SettingsLoadResult
        from fractal_studio.services.settings_service import SettingsWorkflowService
        from fractal_studio.state import UiSettings

        service = SettingsWorkflowService()
        result = service.startup_message(
            SettingsLoadResult(settings=UiSettings(theme="dark"), source="legacy")
        )

        self.assertEqual(result, "Loaded legacy settings file.")

    def test_status_message_reports_legacy_settings_when_backend_missing(self) -> None:
        from fractal_studio.services.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.status_message(False, "legacy")

        self.assertEqual(
            result,
            "Fractal Studio ready with scaffold defaults. Loaded legacy settings file.",
        )

    def test_append_diagnostics_joins_non_empty_messages(self) -> None:
        from fractal_studio.services.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()

        result = service.append_diagnostics(
            "Fractal Studio ready with Rust backend.",
            [
                "",
                "Ignored invalid settings file and loaded defaults.",
                "  ",
                "Ignored invalid favorites file and loaded an empty list.",
            ],
        )

        self.assertEqual(
            result,
            "Fractal Studio ready with Rust backend. Ignored invalid settings file and loaded defaults. Ignored invalid favorites file and loaded an empty list.",
        )

    def test_startup_status_applies_legacy_message_and_diagnostics(self) -> None:
        from fractal_studio.persistence import SettingsLoadResult
        from fractal_studio.services.settings_service import SettingsWorkflowService
        from fractal_studio.state import UiSettings

        service = SettingsWorkflowService()

        result = service.startup_status(
            backend_loaded=True,
            load_result=SettingsLoadResult(
                settings=UiSettings(theme="dark"), source="legacy", diagnostic=""
            ),
            diagnostics=["Ignored invalid favorites file and loaded an empty list."],
        )

        self.assertEqual(
            result,
            "Loaded legacy settings file. Ignored invalid favorites file and loaded an empty list.",
        )

    def test_apply_theme_name_can_preview_without_persisting(self) -> None:
        from fractal_studio.services.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        events: list[tuple[str, bool]] = []

        service.apply_theme_name(
            theme_name="dark",
            persist=False,
            current_theme="light",
            apply_theme_to_app=lambda theme_name: events.append((theme_name, False)),
            persist_theme=lambda theme_name: events.append((theme_name, True)),
        )

        self.assertEqual(events, [("dark", False)])

    def test_apply_theme_name_persists_when_requested(self) -> None:
        from fractal_studio.services.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        events: list[tuple[str, bool]] = []

        service.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            apply_theme_to_app=lambda theme_name: events.append((theme_name, False)),
            persist_theme=lambda theme_name: events.append((theme_name, True)),
        )

        self.assertEqual(events, [("sepia", False), ("sepia", True)])


@pytest.mark.integration
class TestWindowStartupCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_app()

    def setUp(self) -> None:
        import fractal_studio.main_window_factory as mwmod

        self._mwmod = mwmod
        self._original_settings_path = mwmod._SETTINGS_PATH
        self._tmpdir = Path(tempfile.mkdtemp(prefix="fs_startup_"))
        mwmod._SETTINGS_PATH = self._tmpdir / "settings.json"

    def tearDown(self) -> None:
        self._mwmod._SETTINGS_PATH = self._original_settings_path

    def test_bootstrap_uses_versioned_settings_and_applies_theme(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.services.settings_service import SettingsWorkflowService
        from fractal_studio.application.workflows.startup_coordinator import (
            WindowStartupCoordinator,
        )
        from fractal_studio.application.controllers.theme_controller import ThemeController
        from fractal_studio.state import UiSettings

        SettingsRepository(self._mwmod._SETTINGS_PATH).save(UiSettings(theme="sepia"))
        coordinator = WindowStartupCoordinator(
            SettingsRepository(self._mwmod._SETTINGS_PATH),
            SettingsWorkflowService(),
            ThemeController(),
        )

        startup = coordinator.bootstrap(application=get_app())

        self.assertEqual(startup.theme_name, "sepia")
        self.assertEqual(startup.theme_spec.name, "sepia")
        self.assertEqual(startup.load_result.source, "current")

        message = coordinator.compose_startup_message(
            backend_loaded=True,
            startup_state=startup,
            favorites_diagnostic="",
        )

        self.assertEqual(message, "Fractal Studio ready with Rust backend.")

    def test_bootstrap_reports_legacy_settings_and_diagnostics(self) -> None:
        from fractal_studio.persistence import SettingsRepository
        from fractal_studio.services.settings_service import SettingsWorkflowService
        from fractal_studio.application.workflows.startup_coordinator import (
            WindowStartupCoordinator,
        )
        from fractal_studio.application.controllers.theme_controller import ThemeController

        self._mwmod._SETTINGS_PATH.write_text(json.dumps({"theme": "dark"}))
        coordinator = WindowStartupCoordinator(
            SettingsRepository(self._mwmod._SETTINGS_PATH),
            SettingsWorkflowService(),
            ThemeController(),
        )

        startup = coordinator.bootstrap(
            application=get_app(),
        )

        self.assertEqual(startup.theme_name, "dark")
        self.assertEqual(startup.theme_spec.name, "dark")
        self.assertEqual(startup.load_result.source, "legacy")

        message = coordinator.compose_startup_message(
            backend_loaded=False,
            startup_state=startup,
            favorites_diagnostic="Ignored invalid favorites file and loaded an empty list.",
        )

        self.assertEqual(
            message,
            "Loaded legacy settings file. Ignored invalid favorites file and loaded an empty list.",
        )


@pytest.mark.integration
class TestSettingsDialogCoordinator(unittest.TestCase):
    def test_open_settings_dialog_delegates_to_main_window_controller(self) -> None:
        from fractal_studio.application.coordinators.settings_dialog_coordinator import (
            SettingsDialogCoordinator,
        )

        class ControllerStub:
            def __init__(self) -> None:
                self.called: dict[str, object] | None = None

            def open_settings_dialog(self, **kwargs) -> None:
                self.called = kwargs

        class SettingsServiceStub:
            def apply_theme_name(self, **kwargs):
                return kwargs["theme_name"]

        controller = ControllerStub()
        coordinator = SettingsDialogCoordinator(controller, SettingsServiceStub())
        applied: list[tuple[str, bool]] = []

        coordinator.open_settings_dialog(
            parent=object(),
            current_theme="light",
            dialog_factory=lambda theme, parent: object(),
            apply_theme_name=lambda name, persist: applied.append((name, persist)),
        )

        self.assertIsNotNone(controller.called)
        self.assertEqual(controller.called["current_theme"], "light")

    def test_apply_theme_name_applies_and_refreshes(self) -> None:
        from fractal_studio.application.coordinators.settings_dialog_coordinator import (
            SettingsDialogCoordinator,
        )

        class ControllerStub:
            def open_settings_dialog(self, **kwargs) -> None:
                pass

        class SettingsServiceStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def apply_theme_name(self, **kwargs):
                self.calls.append(kwargs)
                kwargs["apply_theme_to_app"](kwargs["theme_name"])
                kwargs["persist_theme"](kwargs["theme_name"])
                return kwargs["theme_name"]

        service = SettingsServiceStub()
        coordinator = SettingsDialogCoordinator(ControllerStub(), service)
        applied: list[str] = []
        persisted: list[str] = []
        refreshed: list[bool] = []

        result = coordinator.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            apply_theme_to_app=applied.append,
            persist_theme=persisted.append,
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(result, "sepia")
        self.assertEqual(applied, ["sepia"])
        self.assertEqual(persisted, ["sepia"])
        self.assertEqual(refreshed, [True])


@pytest.mark.integration
class TestThemeWorkflowCoordinator(unittest.TestCase):
    def test_apply_theme_name_applies_persists_and_returns_updated_spec(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.application.workflows.theme_workflow_coordinator import (
            ThemeWorkflowCoordinator,
        )

        class SettingsDialogStub:
            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def apply_theme(self, application, theme_name: str):
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.updated_themes: list[str] = []

            def load(self):
                from fractal_studio.persistence import SettingsLoadResult
                return SettingsLoadResult(settings=UiSettings(), source="default")

            def update(self, transform) -> UiSettings:
                result = transform(UiSettings())
                self.updated_themes.append(result.theme)
                return result

        refreshed: list[bool] = []
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            ThemeControllerStub(),
            settings_repo,
        )

        theme_name, theme_spec = coordinator.apply_theme_name(
            theme_name="sepia",
            persist=True,
            current_theme="light",
            current_theme_spec="spec-light",
            application=object(),
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(theme_name, "sepia")
        self.assertEqual(theme_spec, "spec-sepia")
        self.assertEqual(settings_repo.updated_themes, ["sepia"])
        self.assertEqual(refreshed, [True])

    def test_apply_theme_name_keeps_current_spec_when_theme_unchanged(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.application.workflows.theme_workflow_coordinator import (
            ThemeWorkflowCoordinator,
        )

        class SettingsDialogStub:
            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def apply_theme(self, application, theme_name: str):
                self.calls.append(theme_name)
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.updated_themes: list[str] = []

            def load(self):
                from fractal_studio.persistence import SettingsLoadResult
                return SettingsLoadResult(settings=UiSettings(), source="default")

            def update(self, transform) -> UiSettings:
                result = transform(UiSettings())
                self.updated_themes.append(result.theme)
                return result

        refreshed: list[bool] = []
        theme_controller = ThemeControllerStub()
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            theme_controller,
            settings_repo,
        )

        theme_name, theme_spec = coordinator.apply_theme_name(
            theme_name="light",
            persist=False,
            current_theme="light",
            current_theme_spec="spec-light",
            application=object(),
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(theme_name, "light")
        self.assertEqual(theme_spec, "spec-light")
        self.assertEqual(theme_controller.calls, [])
        self.assertEqual(settings_repo.updated_themes, [])
        self.assertEqual(refreshed, [True])

    def test_open_settings_returns_updated_theme_and_spec(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.application.workflows.theme_workflow_coordinator import (
            ThemeWorkflowCoordinator,
        )

        class SettingsDialogStub:
            def open_settings_dialog(self, **kwargs) -> None:
                kwargs["apply_theme_name"]("sepia", True)

            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def apply_theme(self, application, theme_name: str):
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.updated_themes: list[str] = []

            def load(self):
                from fractal_studio.persistence import SettingsLoadResult
                return SettingsLoadResult(settings=UiSettings(), source="default")

            def update(self, transform) -> UiSettings:
                result = transform(UiSettings())
                self.updated_themes.append(result.theme)
                return result

        refreshed: list[bool] = []
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            ThemeControllerStub(),
            settings_repo,
        )

        theme_name, theme_spec = coordinator.open_settings(
            parent=object(),
            current_theme="light",
            current_theme_spec="spec-light",
            dialog_factory=lambda theme, parent: object(),
            application=object(),
            refresh_dynamic_widgets=lambda: refreshed.append(True),
        )

        self.assertEqual(theme_name, "sepia")
        self.assertEqual(theme_spec, "spec-sepia")
        self.assertEqual(settings_repo.updated_themes, ["sepia"])
        self.assertEqual(refreshed, [True])

    def test_open_settings_keeps_current_state_when_no_changes(self) -> None:
        from fractal_studio.state import UiSettings
        from fractal_studio.application.workflows.theme_workflow_coordinator import (
            ThemeWorkflowCoordinator,
        )

        class SettingsDialogStub:
            def open_settings_dialog(self, **kwargs) -> None:
                return None

            def apply_theme_name(self, **kwargs):
                if kwargs["theme_name"] != kwargs["current_theme"]:
                    kwargs["apply_theme_to_app"](kwargs["theme_name"])
                if kwargs["persist"]:
                    kwargs["persist_theme"](kwargs["theme_name"])
                kwargs["refresh_dynamic_widgets"]()
                return kwargs["theme_name"]

        class ThemeControllerStub:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def apply_theme(self, application, theme_name: str):
                self.calls.append(theme_name)
                return f"spec-{theme_name}"

        class SettingsRepoStub:
            def __init__(self) -> None:
                self.saved: list[UiSettings] = []

            def save(self, settings: UiSettings) -> None:
                self.saved.append(settings)

        theme_controller = ThemeControllerStub()
        settings_repo = SettingsRepoStub()
        coordinator = ThemeWorkflowCoordinator(
            SettingsDialogStub(),
            theme_controller,
            settings_repo,
        )

        theme_name, theme_spec = coordinator.open_settings(
            parent=object(),
            current_theme="light",
            current_theme_spec="spec-light",
            dialog_factory=lambda theme, parent: object(),
            application=object(),
            refresh_dynamic_widgets=lambda: None,
        )

        self.assertEqual(theme_name, "light")
        self.assertEqual(theme_spec, "spec-light")
        self.assertEqual(theme_controller.calls, [])
        self.assertEqual(settings_repo.saved, [])


@pytest.mark.integration
class TestThemeController(unittest.TestCase):
    def test_refresh_dynamic_widgets_repolishes_hover_panel_and_rows(self) -> None:
        from fractal_studio.application.controllers.theme_controller import (
            ThemeController,
        )

        class FakeStyle:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def unpolish(self, widget) -> None:
                self.calls.append("unpolish")

            def polish(self, widget) -> None:
                self.calls.append("polish")

        class FakeHoverPanel:
            def __init__(self) -> None:
                self._style = FakeStyle()

            def style(self):
                return self._style

        class FakeRow:
            def __init__(self) -> None:
                self.applied = 0

            def _apply_visual_state(self) -> None:
                self.applied += 1

        controller = ThemeController()
        hover_panel = FakeHoverPanel()
        rows = [FakeRow(), FakeRow()]

        controller.refresh_dynamic_widgets(hover_panel, rows)

        self.assertEqual(hover_panel.style().calls, ["unpolish", "polish"])
        self.assertEqual(rows[0].applied, 1)
        self.assertEqual(rows[1].applied, 1)

    def test_build_stylesheet_keeps_expected_sections(self) -> None:
        from fractal_studio.theme import build_stylesheet, get_theme

        stylesheet = build_stylesheet(get_theme("light"))

        self.assertIn("QMainWindow, QDialog", stylesheet)
        self.assertIn("QLabel#hoverPanel", stylesheet)
        self.assertIn("QDialog#settingsDialog", stylesheet)


