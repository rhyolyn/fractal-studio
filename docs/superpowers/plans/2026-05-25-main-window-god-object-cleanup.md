# MainWindow God Object Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Agent instructions:** Follow `C:\Users\rhyol\AGENTS.md` for repository-wide working preferences.

**Goal:** Reduce `MainWindow` to composition and wiring by moving the remaining startup/theme/settings logic into a dedicated collaborator and deleting the last theme/persistence branching from the window class.

**Architecture:** The app already splits out export, favorites, palette workflow, viewport/editor controllers, and persistence repositories. The remaining `MainWindow` work should target the startup path and theme/settings behavior that still combines load-result handling, status messaging, theme application, and persistence in one class. Keep the new collaborator narrow and let `MainWindow` do only wiring plus UI refresh calls.

**Tech Stack:** Python 3.14, PySide6, pytest, existing `fractal_studio` app modules.

---

### Task 1: Extract startup/theme settings workflow

**Files:**
- Create: `ui/src/fractal_studio/settings_service.py`
- Modify: `ui/src/fractal_studio/main_window.py`
- Test: `ui/tests/test_ui_redesign.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSettingsWorkflowService(unittest.TestCase):
    def test_startup_message_reports_legacy_settings(self) -> None:
        from fractal_studio.persistence import SettingsLoadResult
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        result = service.startup_message(
            SettingsLoadResult(settings=UiSettings(theme="dark"), source="legacy")
        )

        assert result == "Loaded legacy settings file."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k SettingsWorkflowService -v`
Expected: FAIL because `fractal_studio.settings_service` does not exist yet and no startup-settings service owns the startup message.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from collections.abc import Callable

from fractal_studio.persistence import SettingsLoadResult


class SettingsWorkflowService:
    def startup_message(self, load_result: SettingsLoadResult) -> str:
        if load_result.source == "legacy":
            return "Loaded legacy settings file."
        return ""

    def apply_theme_name(
        self,
        theme_name: str,
        persist: bool,
        current_theme: str,
        apply_theme_to_app: Callable[[str], None],
        persist_theme: Callable[[str], None],
    ) -> str:
        if theme_name != current_theme:
            apply_theme_to_app(theme_name)
        if persist:
            persist_theme(theme_name)
        return theme_name
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k SettingsWorkflowService -v`
Expected: PASS.

- [ ] **Step 5: Update `MainWindow` startup to use the service**

```python
from fractal_studio.settings_service import SettingsWorkflowService

# in __init__
self._settings_service = SettingsWorkflowService()
settings = self._load_settings_from_disk()
self._theme_name = settings.settings.theme
self._theme_spec = apply_theme(QApplication.instance(), self._theme_name)
self.statusBar().showMessage(self._settings_service.startup_message(settings))
```

- [ ] **Step 6: Run the focused settings tests again**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k "AppearanceSettings or SettingsWorkflowService" -v`
Expected: PASS.

---

### Task 2: Replace the last theme/persistence branching in `MainWindow`

**Files:**
- Modify: `ui/src/fractal_studio/main_window.py`
- Modify: `ui/src/fractal_studio/settings_service.py`
- Modify: `ui/tests/test_ui_redesign.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSettingsWorkflowService(unittest.TestCase):
    def test_apply_theme_name_can_preview_without_persisting(self) -> None:
        from fractal_studio.settings_service import SettingsWorkflowService

        service = SettingsWorkflowService()
        events: list[tuple[str, bool]] = []

        service.apply_theme_name(
            theme_name="dark",
            persist=False,
            current_theme="light",
            apply_theme_to_app=lambda theme_name: events.append((theme_name, False)),
            persist_theme=lambda theme_name: events.append((theme_name, True)),
        )

        assert events == [("dark", False)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k apply_theme_name_can_preview_without_persisting -v`
Expected: FAIL because the service method does not match the new collaborator boundary yet.

- [ ] **Step 3: Write minimal implementation**

```python
class SettingsWorkflowService:
    def apply_theme_name(
        self,
        theme_name: str,
        persist: bool,
        current_theme: str,
        apply_theme_to_app: Callable[[str], None],
        persist_theme: Callable[[str], None],
    ) -> str:
        if theme_name != current_theme:
            apply_theme_to_app(theme_name)
        if persist:
            persist_theme(theme_name)
        return theme_name
```

- [ ] **Step 4: Update `MainWindow` to delegate to the service**

```python
# MainWindow._apply_theme_name becomes a thin wrapper.
self._theme_name = self._settings_service.apply_theme_name(
    theme_name=theme_name,
    persist=persist,
    current_theme=self._theme_name,
    apply_theme_to_app=lambda name: setattr(self, "_theme_spec", apply_theme(QApplication.instance(), name)),
    persist_theme=lambda name: self._persist_settings(name),
)
self._apply_theme_to_dynamic_widgets()
```

- [ ] **Step 5: Run the focused tests again**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k AppearanceSettings -v`
Expected: PASS.

---

### Task 3: Remove the remaining `MainWindow` persistence wrappers

**Files:**
- Modify: `ui/src/fractal_studio/main_window.py`
- Test: `ui/tests/test_ui_redesign.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSettingsRepository(unittest.TestCase):
    def test_main_window_load_settings_is_thin_wrapper(self) -> None:
        import inspect

        from fractal_studio.main_window import MainWindow

        source = inspect.getsource(MainWindow._load_settings_from_disk)

        assert "self._settings_repo.load()" in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k SettingsRepository -v`
Expected: FAIL if `MainWindow._load_settings_from_disk` still carries extra branching instead of a direct delegation.

- [ ] **Step 3: Keep the repository contract as the single persistence boundary**

```python
@dataclass(frozen=True)
class SettingsLoadResult:
    settings: UiSettings
    source: Literal["current", "legacy", "default"]
```

- [ ] **Step 4: Keep `MainWindow` persistence access thin**

```python
def _persist_settings(self, theme_name: str) -> None:
    self._settings_repo.save(UiSettings(theme=theme_name))
```

- [ ] **Step 5: Run the focused settings tests together**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py -k "SettingsWorkflowService or AppearanceSettings" -v`
Expected: PASS.

---

### Task 4: Clean up the doc and confirm the god-object boundary is actually smaller

**Files:**
- Modify: `docs/architecture-analysis-2026-05-25.md`

- [ ] **Step 1: Update the architecture doc**

```markdown
- Phase 2 decomposition slice 7 is done: remaining startup/theme/settings branching moved behind `SettingsWorkflowService`.
- UI regression suite remains green after slice 7.
```

- [ ] **Step 2: Remove the completed item from the active queue**

Delete the backlog entry for the completed `MainWindow` settings slice and keep only the next unresolved cleanup items.

- [ ] **Step 3: Re-read the doc for contradictions**

Confirm that the doc no longer says the completed settings slice is still pending and that the next package names the remaining `MainWindow` cleanup work.

---

### Task 5: Final validation pass

**Files:**
- No new files expected

- [ ] **Step 1: Run the full UI suite**

Run: `cd ui ; c:/git/graphics/fractal-studio/.venv/Scripts/python.exe -m pytest tests/test_ui_redesign.py`
Expected: PASS.

---

### Task 6: Smoke-test the app launch path

**Files:**
- No new files expected

- [ ] **Step 1: Run the app once**

```markdown
cd fractal-studio
python -m fractal_studio.app
```

- [ ] **Step 2: Confirm startup stays clean**

Expect the app to launch without import errors, startup exceptions, or broken status messaging.

- [ ] **Step 3: Review the diff for accidental coupling**

Run: `git diff -- ui/src/fractal_studio ui/tests/test_ui_redesign.py docs/architecture-analysis-2026-05-25.md`
Expected: only the planned `MainWindow` cleanup, service extraction, tests, and doc updates.

