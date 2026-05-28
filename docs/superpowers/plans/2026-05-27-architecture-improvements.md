# Architecture Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the 8-step dependency-ordered architecture improvement plan for fractal-studio's Python UI layer.

**Architecture:** Each task is independently shippable. Steps 1–5 are safe, low-risk changes (config, docs, file moves). Steps 6–8 are structural rewrites with test coverage at each step. The test suite is the safety net — run `pytest -m unit` after every commit.

**Tech Stack:** Python 3.12, PySide6 6.8, pytest, fractal-studio-ui package at `fractal-studio/ui/`

---

## File Structure

Files created or significantly changed across all tasks:

| File | Change |
|------|--------|
| `fractal-studio/ui/pyproject.toml` | Add `[tool.pytest.ini_options]` with markers |
| `fractal-studio/ui/tests/test_backend.py` | Add `@pytest.mark.unit` |
| `fractal-studio/ui/tests/test_import_policy.py` | Add `@pytest.mark.unit` |
| `fractal-studio/ui/tests/test_ui_redesign.py` | Add `@pytest.mark.integration` |
| `fractal-studio/ui/tests/test_package_layout_smoke.py` | Add `@pytest.mark.integration` |
| `fractal-studio/ui/tests/test_main_window_section_panel_states.py` | Add `@pytest.mark.integration` |
| `fractal-studio/ui/src/fractal_studio/ui/sections/panel_state.py` | Add `validate()` per-state methods (Step 2), update imports (Step 6), update `bind_collaborators` (Step 8) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/state.py` | Add `validate()` (Step 2), update imports (Step 6), shrink `bind()` (Step 8) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/` | New directory (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/__init__.py` | New — re-exports all adapters + `build_sections_ports` (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/base.py` | Moved from `sections/base.py` (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/*_adapter.py` | 7 files moved from `sections/` (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/base.py` | Deleted (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/adapters.py` | Deleted (Step 3) |
| `fractal-studio/ui/src/fractal_studio/ui/sections/mediator.py` | Updated imports (Step 3) |
| `fractal-studio/ui/src/fractal_studio/application/controllers/__init__.py` | Add docstring (Step 4), update exports (Step 6) |
| `fractal-studio/ui/src/fractal_studio/application/coordinators/__init__.py` | Add docstring (Step 4) |
| `fractal-studio/ui/src/fractal_studio/application/workflows/__init__.py` | Add docstring (Step 4) |
| `fractal-studio/ui/src/fractal_studio/application/coordinators/*.py` | Add class docstrings (Step 5) |
| `fractal-studio/ui/src/fractal_studio/application/controllers/export_controller.py` | New (Step 6) |
| `fractal-studio/ui/src/fractal_studio/application/controllers/settings_controller.py` | New (Step 6) |
| `fractal-studio/ui/src/fractal_studio/application/controllers/main_window_controller.py` | Deleted (Step 6) |
| `fractal-studio/ui/src/fractal_studio/main_window_factory.py` | Update context (Steps 6, 8) |
| `fractal-studio/ui/src/fractal_studio/state.py` | Add formula param sub-structs (Step 7) |
| `fractal-studio/ui/src/fractal_studio/viewport.py` | Update `to_state`/`apply_state` (Step 7) |
| `fractal-studio/ui/src/fractal_studio/backend.py` | Update render call (Step 7) |
| `fractal-studio/ui/src/fractal_studio/ui/controllers/viewport_controller.py` | Update render call (Step 7) |

---

## Task 1: Add pytest markers and fix test infrastructure

**Files:**
- Modify: `fractal-studio/ui/pyproject.toml`
- Modify: `fractal-studio/ui/tests/test_backend.py`
- Modify: `fractal-studio/ui/tests/test_import_policy.py`
- Modify: `fractal-studio/ui/tests/test_ui_redesign.py`
- Modify: `fractal-studio/ui/tests/test_package_layout_smoke.py`
- Modify: `fractal-studio/ui/tests/test_main_window_section_panel_states.py`

- [ ] **Step 1.1: Add marker config to pyproject.toml**

Add to `fractal-studio/ui/pyproject.toml` after the existing `[tool.ruff.lint.per-file-ignores]` section:

```toml
[tool.pytest.ini_options]
addopts = "-m unit"
markers = [
    "unit: pure-Python tests, no Qt or PySide6 required",
    "integration: tests requiring PySide6 / Qt",
]
```

- [ ] **Step 1.2: Mark test_backend.py as unit**

In `fractal-studio/ui/tests/test_backend.py`, add after the `import unittest` line:

```python
import pytest
```

And add the mark to each test method:

```python
class BackendProfileTests(unittest.TestCase):
    @pytest.mark.unit
    def test_default_profile_uses_modernized_defaults(self) -> None:
        ...

    @pytest.mark.unit
    def test_loader_falls_back_when_rust_extension_is_missing(self) -> None:
        ...
```

- [ ] **Step 1.3: Mark test_import_policy.py as unit**

Open `fractal-studio/ui/tests/test_import_policy.py`. Add `import pytest` at the top and add `@pytest.mark.unit` to every test function/class.

- [ ] **Step 1.4: Mark integration tests**

Add `import pytest` and `@pytest.mark.integration` to every test class or function in:
- `fractal-studio/ui/tests/test_ui_redesign.py`
- `fractal-studio/ui/tests/test_package_layout_smoke.py`
- `fractal-studio/ui/tests/test_main_window_section_panel_states.py`

- [ ] **Step 1.5: Verify unit tests pass**

Run from `fractal-studio/ui/`:
```
python -m pytest -m unit -v
```
Expected: 3 tests pass, 0 failures. No PySide6 import errors.

- [ ] **Step 1.6: Verify integration tests are collected but skipped by default**

Run:
```
python -m pytest --collect-only -m integration
```
Expected: integration tests listed but not executed (they're excluded by default `addopts`).

- [ ] **Step 1.7: Commit**

```
git add fractal-studio/ui/pyproject.toml fractal-studio/ui/tests/
git commit -m "Add unit/integration pytest markers; default run is unit-only"
```

---

## Task 2: Add validate() to detect unbound collaborators

**Files:**
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/panel_state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/state.py`

- [ ] **Step 2.1: Write failing test**

In `fractal-studio/ui/tests/test_backend.py` (unit-marked, no Qt), add a new test class:

```python
@pytest.mark.unit
class ValidateTest(unittest.TestCase):
    def test_validate_raises_when_collaborator_unbound(self) -> None:
        from fractal_studio.ui.sections.state import MainWindowSectionsState
        state = MainWindowSectionsState.__new__(MainWindowSectionsState)
        state.owner = None
        with self.assertRaises(RuntimeError) as ctx:
            state.validate()
        self.assertIn("owner", str(ctx.exception))
```

- [ ] **Step 2.2: Run test to verify it fails**

```
python -m pytest tests/test_backend.py::ValidateTest -v
```
Expected: FAIL — `MainWindowSectionsState` has no `validate` method.

- [ ] **Step 2.3: Add validate() to MainWindowSectionsState**

In `fractal-studio/ui/src/fractal_studio/ui/sections/state.py`, add this method to `MainWindowSectionsState` after the `bind()` method:

```python
def validate(self) -> None:
    required = [
        "owner",
        "favorites_repo",
        "settings_repo",
        "settings_service",
        "startup",
        "favorites_controller",
        "favorites_panel",
        "favorites_workflow",
        "sections",
        "theme_controller",
        "backend",
        "export_service",
        "palette_service",
        "palette_panel",
        "palette_preview",
        "sidebar_wiring",
        "controller",
        "export_panel",
        "settings_dialog",
        "theme_workflow",
    ]
    for name in required:
        if getattr(self, name, None) is None:
            raise RuntimeError(
                f"MainWindowSectionsState.validate(): '{name}' was not bound. "
                f"Call bind(owner, context) before validate()."
            )
```

- [ ] **Step 2.4: Call validate() at end of bind()**

At the end of `MainWindowSectionsState.bind()` in `state.py`, add:

```python
        self.validate()
```

- [ ] **Step 2.5: Run test to verify it passes**

```
python -m pytest tests/test_backend.py::ValidateTest -v
```
Expected: PASS.

- [ ] **Step 2.6: Run full unit suite**

```
python -m pytest -m unit -v
```
Expected: all unit tests pass.

- [ ] **Step 2.7: Commit**

```
git add fractal-studio/ui/src/fractal_studio/ui/sections/state.py fractal-studio/ui/tests/test_backend.py
git commit -m "Add validate() to MainWindowSectionsState to catch unbound collaborators"
```

---

## Task 3: Move adapters into ui/sections/adapters/ subdirectory

The current structure has `base.py` (base classes), `adapters.py` (factory function `build_sections_ports`), and 7 `*_adapter.py` files all loose in `ui/sections/`. The target: an `adapters/` subdirectory that groups all adapter code.

**Files:**
- Create: `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/` (directory)
- Create: `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/__init__.py`
- Create: `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/base.py`
- Move (and update): 7 `*_adapter.py` files
- Delete: `fractal-studio/ui/src/fractal_studio/ui/sections/base.py`
- Delete: `fractal-studio/ui/src/fractal_studio/ui/sections/adapters.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/mediator.py`

- [ ] **Step 3.1: Create adapters/base.py**

Create `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/base.py` with this content (copied from `sections/base.py`, no logic changes):

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fractal_studio.main_window import MainWindow


class _BasePortsAdapter:
    def __init__(self, owner: MainWindow) -> None:
        self._owner = owner
        self._state = owner._sections_state

    @property
    def backend(self):
        return self._state.backend

    @property
    def backend_profile(self):
        return self._state.backend_profile

    @property
    def viewport(self):
        return self._state.viewport

    def show_status(self, message: str) -> None:
        self._owner.statusBar().showMessage(message)


class _FavoriteActionsMixin:
    def save_favorite(self) -> None:
        self._state._favorites_state.save_favorite()
```

- [ ] **Step 3.2: Update each adapter file's import**

Each of the 7 adapter files currently contains `from fractal_studio.ui.sections.base import _BasePortsAdapter`. That import needs to change to `from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter` after they are moved. Read each file, copy it to `adapters/`, update the import, then delete the original. Repeat for all 7:

| Original | Destination | Import change |
|----------|-------------|---------------|
| `sections/backend_adapter.py` | `sections/adapters/backend_adapter.py` | `from fractal_studio.ui.sections.base` → `from fractal_studio.ui.sections.adapters.base` |
| `sections/colormap_adapter.py` | `sections/adapters/colormap_adapter.py` | same |
| `sections/export_adapter.py` | `sections/adapters/export_adapter.py` | same |
| `sections/favorites_adapter.py` | `sections/adapters/favorites_adapter.py` | same |
| `sections/palette_adapter.py` | `sections/adapters/palette_adapter.py` | same |
| `sections/sidebar_adapter.py` | `sections/adapters/sidebar_adapter.py` | same |
| `sections/viewport_adapter.py` | `sections/adapters/viewport_adapter.py` | same |

For example, `sections/adapters/viewport_adapter.py` should read:

```python
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel

from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter
from fractal_studio.viewport import FractalViewportWidget


class ViewportPanelPortsAdapter(_BasePortsAdapter):
    def set_aspect_ratio_combo(self, combo: QComboBox) -> None:
        self._state._viewport_state.set_aspect_ratio_combo(combo)

    def on_aspect_ratio_changed(self, index: int) -> None:
        self._state._viewport_state.handle_aspect_ratio_changed(index)

    def set_viewport(self, viewport: FractalViewportWidget) -> None:
        self._state._viewport_state.set_viewport(viewport)

    def set_viewport_hint_label(self, label: QLabel) -> None:
        self._state._viewport_state.set_viewport_hint_label(label)
```

- [ ] **Step 3.3: Create adapters/__init__.py**

Create `fractal-studio/ui/src/fractal_studio/ui/sections/adapters/__init__.py` with these contents (re-exports all adapters + the factory from the old `adapters.py`):

```python
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
```

- [ ] **Step 3.4: Update mediator.py**

Replace `fractal-studio/ui/src/fractal_studio/ui/sections/mediator.py` with:

```python
from __future__ import annotations

from fractal_studio.ui.sections.adapters import build_sections_ports
from fractal_studio.ui.sections.ports import (
    BackendPanelPorts,
    ColormapPanelPorts,
    ExportPanelPorts,
    FavoritesPanelPorts,
    MainWindowSectionsPorts,
    PalettePanelPorts,
    SidebarPanelPorts,
    ViewportPanelPorts,
)

__all__ = [
    "BackendPanelPorts",
    "ColormapPanelPorts",
    "ExportPanelPorts",
    "FavoritesPanelPorts",
    "MainWindowSectionsPorts",
    "PalettePanelPorts",
    "SidebarPanelPorts",
    "ViewportPanelPorts",
    "build_sections_ports",
]
```

(Import path changes from `fractal_studio.ui.sections.adapters` — same module name, now a package.)

- [ ] **Step 3.5: Delete the old files**

```
git rm fractal-studio/ui/src/fractal_studio/ui/sections/base.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/adapters.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/backend_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/colormap_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/export_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/favorites_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/palette_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/sidebar_adapter.py
git rm fractal-studio/ui/src/fractal_studio/ui/sections/viewport_adapter.py
```

- [ ] **Step 3.6: Check for any remaining imports of old paths**

```
python -m pytest -m unit -v
```

Also run a grep to verify no file still imports from the deleted paths:
```
grep -r "from fractal_studio.ui.sections.base" fractal-studio/ui/src/
grep -r "from fractal_studio.ui.sections.adapters import build" fractal-studio/ui/src/
```
Both should return nothing.

- [ ] **Step 3.7: Commit**

```
git add fractal-studio/ui/src/fractal_studio/ui/sections/
git commit -m "Move adapter files into ui/sections/adapters/ subdirectory"
```

---

## Task 4: Document the Controller/Coordinator/Workflow contract

**Files:**
- Modify: `fractal-studio/ui/src/fractal_studio/application/controllers/__init__.py`
- Modify: `fractal-studio/ui/src/fractal_studio/application/coordinators/__init__.py`
- Modify: `fractal-studio/ui/src/fractal_studio/application/workflows/__init__.py`

- [ ] **Step 4.1: Add docstring to controllers/__init__.py**

Replace the current `application/controllers/__init__.py` with:

```python
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
```

Note: `MainWindowController` will be replaced by `ExportController` + `SettingsController` in Task 6. The docstring added here is what matters; Task 6 will update the imports when it rewrites this file.

- [ ] **Step 4.2: Add docstring to coordinators/__init__.py**

Replace `application/coordinators/__init__.py` with:

```python
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
```

- [ ] **Step 4.3: Add docstring to workflows/__init__.py**

Replace `application/workflows/__init__.py` with:

```python
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
```

- [ ] **Step 4.4: Run unit tests**

```
python -m pytest -m unit -v
```
Expected: all pass.

- [ ] **Step 4.5: Commit**

```
git add fractal-studio/ui/src/fractal_studio/application/
git commit -m "Document controller/coordinator/workflow layer contracts in __init__.py"
```

---

## Task 5: Audit and document each coordinator's mandate

**Files:**
- Modify: all 6 files in `fractal-studio/ui/src/fractal_studio/application/coordinators/`

- [ ] **Step 5.1: Add docstrings to all coordinator classes**

Open each coordinator file and add a one-line class docstring. The exact strings to use:

**`export_panel_coordinator.py`** — add to `ExportPanelCoordinator`:
```python
class ExportPanelCoordinator:
    """Coordinator for the export panel. Owns aspect ratio changes, preset selection, and export execution."""
```

**`palette_preview_coordinator.py`** — add to `PalettePreviewCoordinator`:
```python
class PalettePreviewCoordinator:
    """Coordinator for the palette preview panel. Owns preview refresh and control point summary display."""
```

**`favorites_panel_coordinator.py`** — add to `FavoritesPanelCoordinator`:
```python
class FavoritesPanelCoordinator:
    """Coordinator for the favorites panel. Owns row construction, selection, deletion, and scroll layout management."""
```

**`palette_panel_coordinator.py`** — add to `PalettePanelCoordinator`:
```python
class PalettePanelCoordinator:
    """Coordinator for the colormap panel. Owns palette JSON save/load and legacy .map export."""
```

**`settings_dialog_coordinator.py`** — add to `SettingsDialogCoordinator`:
```python
class SettingsDialogCoordinator:
    """Coordinator for the settings dialog. Owns dialog lifecycle and theme preview vs. persist logic."""
```

**`sidebar_wiring_coordinator.py`** — add to `SidebarWiringCoordinator`:
```python
class SidebarWiringCoordinator:
    """Coordinator for the sidebar panel. Owns signal wiring between the params panel and the viewport."""
```

- [ ] **Step 5.2: Run unit tests**

```
python -m pytest -m unit -v
```
Expected: all pass.

- [ ] **Step 5.3: Commit**

```
git add fractal-studio/ui/src/fractal_studio/application/coordinators/
git commit -m "Add mandate docstrings to all coordinator classes"
```

---

## Task 6: Split MainWindowController into ExportController and SettingsController

`MainWindowController` currently mixes export preset logic with settings dialog logic. This task splits it into two focused controllers.

**Files:**
- Create: `fractal-studio/ui/src/fractal_studio/application/controllers/export_controller.py`
- Create: `fractal-studio/ui/src/fractal_studio/application/controllers/settings_controller.py`
- Delete: `fractal-studio/ui/src/fractal_studio/application/controllers/main_window_controller.py`
- Modify: `fractal-studio/ui/src/fractal_studio/application/controllers/__init__.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/panel_state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/main_window_factory.py`

- [ ] **Step 6.1: Create ExportController**

Create `fractal-studio/ui/src/fractal_studio/application/controllers/export_controller.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QSpinBox, QWidget

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.state import FavoriteSnapshot, ViewportState
from fractal_studio.services.export_service import ExportService
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget
from fractal_studio.application.controllers.favorites_controller import (
    FavoritesController,
)


class ExportController:
    """Controller for export and aspect ratio logic. Owns preset math, aspect ratio application, and export execution."""

    def __init__(
        self, export_service: ExportService, favorites_controller: FavoritesController
    ) -> None:
        self._export_service = export_service
        self._favorites_controller = favorites_controller

    def on_export_clicked(
        self,
        export_presets: list[tuple[str, int, int]],
        index: int,
        custom_width_box: QSpinBox | None,
        custom_height_box: QSpinBox | None,
        set_custom_size: Callable[[int, int], None],
        export_callback: Callable[[int, int], None],
    ) -> None:
        if index < 0 or index >= len(export_presets):
            return
        _, width, height = export_presets[index]
        if width == 0:
            if custom_width_box is None or custom_height_box is None:
                return
            width = custom_width_box.value()
            height = custom_height_box.value()
            set_custom_size(width, height)
        export_callback(width, height)

    def build_export_presets_for_mode(
        self, aspect_mode: str
    ) -> list[tuple[str, int, int]]:
        preset_sizes = {
            "square": [(1080, 1080), (1440, 1440), (2160, 2160)],
            "portrait": [(1080, 1440), (1440, 1920), (2160, 2880)],
            "landscape": [(1440, 1080), (1920, 1440), (2880, 2160)],
        }
        sizes = preset_sizes.get(aspect_mode, preset_sizes["square"])
        return [(f"{width} × {height}", width, height) for width, height in sizes] + [
            ("Custom…", 0, 0)
        ]

    def apply_aspect_ratio_mode(
        self,
        mode: str,
        viewport: FractalViewportWidget | None,
        aspect_ratio_combo: QComboBox | None,
        refresh_export_presets: Callable[[], None],
        update_combo: bool = True,
    ) -> str:
        if mode not in ("square", "portrait", "landscape"):
            mode = "square"
        if viewport is not None:
            viewport.set_aspect_ratio_mode(mode)
        if update_combo and aspect_ratio_combo is not None:
            index = {"square": 0, "portrait": 1, "landscape": 2}[mode]
            aspect_ratio_combo.blockSignals(True)
            aspect_ratio_combo.setCurrentIndex(index)
            aspect_ratio_combo.blockSignals(False)
        refresh_export_presets()
        return mode

    def aspect_mode_from_index(self, index: int) -> str:
        return {0: "square", 1: "portrait", 2: "landscape"}.get(index, "square")

    def should_show_custom_size(self, index: int, presets_count: int) -> bool:
        return index == presets_count - 1

    def refresh_export_presets(
        self,
        aspect_ratio_mode: str,
        export_combo: QComboBox | None,
        current_presets: list[tuple[str, int, int]],
        on_export_preset_changed: Callable[[int], None],
    ) -> list[tuple[str, int, int]]:
        if export_combo is None:
            return current_presets
        previous_index = export_combo.currentIndex()
        previous_is_custom = (
            bool(current_presets) and previous_index == len(current_presets) - 1
        )
        new_presets = self.build_export_presets_for_mode(aspect_ratio_mode)
        export_combo.blockSignals(True)
        export_combo.clear()
        for label, _, _ in new_presets:
            export_combo.addItem(label)
        if previous_is_custom:
            export_combo.setCurrentIndex(len(new_presets) - 1)
        else:
            export_combo.setCurrentIndex(
                max(0, min(previous_index, len(new_presets) - 1))
            )
        export_combo.blockSignals(False)
        on_export_preset_changed(export_combo.currentIndex())
        return new_presets

    def export_render(
        self,
        parent: QWidget,
        viewport: FractalViewportWidget | None,
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bool:
        return self._export_service.export_render(
            parent, viewport, width, height, set_status
        )

    def build_favorite_snapshot(
        self,
        viewport: FractalViewportWidget,
        editor: ColorCubeEditor | None,
        aspect_ratio_mode: str,
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
    ) -> FavoriteSnapshot:
        state = viewport.to_state()
        control_points = editor.control_points if editor is not None else []
        return self._favorites_controller.build_snapshot(
            viewport=viewport,
            aspect_ratio_mode=aspect_ratio_mode,
            name=build_name(state),
            control_points=control_points,
            thumbnail=capture_thumbnail(),
        )

    def restore_favorite_snapshot(
        self,
        snapshot: FavoriteSnapshot,
        viewport: FractalViewportWidget,
        params_panel: FractalParamsPanel,
        editor: ColorCubeEditor | None,
        preview_palette: PalettePreviewWidget | None,
        apply_aspect_ratio_mode: Callable[[str], None],
    ) -> None:
        self._favorites_controller.restore_snapshot(
            snapshot=snapshot,
            viewport=viewport,
            params_panel=params_panel,
            editor=editor,
            preview_palette=preview_palette,
            apply_aspect_ratio_mode=apply_aspect_ratio_mode,
        )

    def sync_params_from_favorite(
        self, favorite: FavoriteSnapshot, params_panel: FractalParamsPanel
    ) -> None:
        self._favorites_controller.sync_params_panel(favorite, params_panel)
```

- [ ] **Step 6.2: Create SettingsController**

Create `fractal-studio/ui/src/fractal_studio/application/controllers/settings_controller.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtWidgets import QDialog, QWidget


class _PreviewSignalLike(Protocol):
    def connect(self, slot: Callable[[str], None]) -> Any: ...


class SettingsDialogLike(Protocol):
    @property
    def theme_preview_requested(self) -> _PreviewSignalLike: ...
    def exec(self) -> int: ...
    def selected_theme(self) -> str: ...


SettingsDialogFactory = Callable[[str, QWidget], SettingsDialogLike]


class SettingsController:
    """Controller for settings dialog lifecycle. Owns theme preview vs. persist decision."""

    def open_settings_dialog(
        self,
        parent: QWidget,
        current_theme: str,
        dialog_factory: SettingsDialogFactory,
        apply_theme_name: Callable[[str, bool], None],
    ) -> None:
        original_theme = current_theme
        dialog = dialog_factory(current_theme, parent)
        dialog.theme_preview_requested.connect(
            lambda theme_name: apply_theme_name(theme_name, False)
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            apply_theme_name(dialog.selected_theme(), True)
        elif dialog.selected_theme() != original_theme:
            apply_theme_name(original_theme, False)
```

- [ ] **Step 6.3: Update controllers/__init__.py**

Replace `application/controllers/__init__.py` with:

```python
"""
Controllers — stateless atoms of domain logic.

Rules:
- No mutable state after __init__ (only injected dependencies).
- No direct QWidget references; accept widgets as method arguments only.
- May reference repositories, services, and other controllers.
- One controller per domain concept.
"""
from fractal_studio.application.controllers.export_controller import ExportController, SettingsDialogFactory
from fractal_studio.application.controllers.favorites_controller import FavoritesController
from fractal_studio.application.controllers.settings_controller import SettingsController
from fractal_studio.application.controllers.theme_controller import ThemeController

__all__ = [
    "ExportController",
    "FavoritesController",
    "SettingsController",
    "SettingsDialogFactory",
    "ThemeController",
]
```

- [ ] **Step 6.4: Update panel_state.py to use ExportController and SettingsController**

In `panel_state.py`, there are two places that reference `MainWindowController`:
- `MainWindowViewportState._controller: MainWindowController | None`
- `MainWindowExportState._controller: MainWindowController | None`

Replace both `MainWindowController` type references with `ExportController`. Update the `TYPE_CHECKING` import block: remove the `main_window_controller` import, add:

```python
from fractal_studio.application.controllers.export_controller import ExportController
from fractal_studio.application.controllers.settings_controller import SettingsController
```

Change field declarations:
```python
# In MainWindowViewportState:
self._controller: ExportController | None = None

# In MainWindowExportState:
self._controller: ExportController | None = None
```

Update `bind_collaborators` signatures in both states to accept `ExportController` instead of `MainWindowController`.

Also update `MainWindowColormapState` if it references `MainWindowController` (check the file — it may not).

- [ ] **Step 6.5: Update state.py to use ExportController**

In `ui/sections/state.py`, the `controller` field currently holds `MainWindowController`. Change:
- Import: remove `main_window_controller` import, add `export_controller` import
- Field: `controller: ExportController | None = None`

The `bind()` method already assigns `self.controller = context.controller` — this will be updated when we update `MainWindowContext` in the next step.

- [ ] **Step 6.6: Update main_window_factory.py**

Read `main_window_factory.py`. Find where `MainWindowController` is constructed and replace it with two constructions:

```python
# Remove:
from fractal_studio.application.controllers.main_window_controller import (
    MainWindowController, SettingsDialogFactory,
)
controller = MainWindowController(
    export_service=export_service,
    favorites_controller=favorites_controller,
)

# Add:
from fractal_studio.application.controllers.export_controller import ExportController
from fractal_studio.application.controllers.settings_controller import SettingsController

export_controller = ExportController(
    export_service=export_service,
    favorites_controller=favorites_controller,
)
settings_controller = SettingsController()
```

Update `MainWindowContext` dataclass: replace `controller: MainWindowController` with `controller: ExportController` and add `settings_controller: SettingsController`.

Update `state.py` field `controller` binding in `bind()` to use `context.controller` (ExportController).

Find all references to `settings_dialog_coordinator` that call `controller.open_settings_dialog` and update them to use the `settings_controller` from context.

- [ ] **Step 6.7: Delete main_window_controller.py**

```
git rm fractal-studio/ui/src/fractal_studio/application/controllers/main_window_controller.py
```

- [ ] **Step 6.8: Run unit tests**

```
python -m pytest -m unit -v
```
Expected: all pass. Fix any remaining `MainWindowController` import references if found.

- [ ] **Step 6.9: Commit**

```
git add fractal-studio/ui/src/fractal_studio/
git commit -m "Split MainWindowController into ExportController and SettingsController"
```

---

## Task 7: Decompose ViewportState into formula-specific sub-structs

`ViewportState` currently has flat fields `julia_real`, `julia_imag`, `phoenix_real`, `phoenix_imag`, `trap_x`, `trap_y`. This task introduces formula-specific parameter sub-structs.

**Files:**
- Modify: `fractal-studio/ui/src/fractal_studio/state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/viewport.py`
- Modify: `fractal-studio/ui/src/fractal_studio/backend.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/controllers/viewport_controller.py`
- Modify: `fractal-studio/ui/tests/test_backend.py`

- [ ] **Step 7.1: Write failing serialization round-trip tests**

Add to `test_backend.py` (unit-marked):

```python
@pytest.mark.unit
class ViewportStateFormulaParamsTests(unittest.TestCase):
    def test_julia_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, JuliaParams
        original = ViewportState(
            formula="standard",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=True,
            formula_params=JuliaParams(cx=-0.8, cy=0.156),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertEqual(restored.formula_params, original.formula_params)

    def test_phoenix_params_round_trip(self) -> None:
        from fractal_studio.state import ViewportState, PhoenixParams
        original = ViewportState(
            formula="phoenix",
            center_x=0.0, center_y=0.0, scale=3.0,
            max_iterations=256, is_julia=False,
            formula_params=PhoenixParams(real=0.5, imag=0.0),
            coloring_mode="smooth_escape",
            palette_offset=0.0,
        )
        restored = ViewportState.from_dict(original.to_dict())
        self.assertEqual(restored.formula_params, original.formula_params)

    def test_legacy_flat_format_loads_correctly(self) -> None:
        from fractal_studio.state import ViewportState, JuliaParams
        legacy = {
            "formula": "standard", "center_x": 0.0, "center_y": 0.0,
            "scale": 3.0, "max_iterations": 256, "is_julia": True,
            "julia_real": -0.8, "julia_imag": 0.156,
            "phoenix_real": 0.5, "phoenix_imag": 0.0,
            "coloring_mode": "smooth_escape",
            "trap_x": 0.0, "trap_y": 0.0, "palette_offset": 0.0,
            "power": 3,
        }
        state = ViewportState.from_dict(legacy)
        self.assertIsInstance(state.formula_params, JuliaParams)
        self.assertAlmostEqual(state.formula_params.cx, -0.8)
```

- [ ] **Step 7.2: Run tests to verify they fail**

```
python -m pytest tests/test_backend.py::ViewportStateFormulaParamsTests -v
```
Expected: FAIL — `JuliaParams`, `PhoenixParams`, `formula_params` don't exist yet.

- [ ] **Step 7.3: Add formula param sub-structs to state.py**

In `fractal-studio/ui/src/fractal_studio/state.py`, add these dataclasses before `ViewportState`:

```python
@dataclass(frozen=True)
class StandardParams:
    pass


@dataclass(frozen=True)
class JuliaParams:
    cx: float = -0.8
    cy: float = 0.156


@dataclass(frozen=True)
class PhoenixParams:
    real: float = 0.5
    imag: float = 0.0


@dataclass(frozen=True)
class NewtonParams:
    trap_x: float = 0.0
    trap_y: float = 0.0


FormulaParams = StandardParams | JuliaParams | PhoenixParams | NewtonParams
```

- [ ] **Step 7.4: Update ViewportState**

Replace the current `ViewportState` fields `julia_real`, `julia_imag`, `phoenix_real`, `phoenix_imag`, `trap_x`, `trap_y` with a single `formula_params: FormulaParams` field. Keep `is_julia: bool` as a top-level field (it is a render mode, not formula-specific).

New `ViewportState` definition:

```python
@dataclass(frozen=True)
class ViewportState:
    formula: str
    center_x: float
    center_y: float
    scale: float
    max_iterations: int
    is_julia: bool
    formula_params: FormulaParams
    coloring_mode: str
    palette_offset: float
    power: int = 3
```

- [ ] **Step 7.5: Update ViewportState.from_dict() with legacy support**

Replace `from_dict` to handle both the new format and the legacy flat format:

```python
@classmethod
def from_dict(cls, raw: dict[str, Any]) -> ViewportState:
    formula = str(raw.get("formula", "standard"))

    if "formula_params" in raw:
        fp_raw = raw["formula_params"]
        fp_type = fp_raw.get("type", "standard")
        if fp_type == "julia":
            formula_params: FormulaParams = JuliaParams(
                cx=float(fp_raw.get("cx", -0.8)),
                cy=float(fp_raw.get("cy", 0.156)),
            )
        elif fp_type == "phoenix":
            formula_params = PhoenixParams(
                real=float(fp_raw.get("real", 0.5)),
                imag=float(fp_raw.get("imag", 0.0)),
            )
        elif fp_type == "newton":
            formula_params = NewtonParams(
                trap_x=float(fp_raw.get("trap_x", 0.0)),
                trap_y=float(fp_raw.get("trap_y", 0.0)),
            )
        else:
            formula_params = StandardParams()
    else:
        # Legacy flat format
        is_julia = bool(raw.get("is_julia", False))
        if formula == "phoenix":
            formula_params = PhoenixParams(
                real=float(raw.get("phoenix_real", 0.5)),
                imag=float(raw.get("phoenix_imag", 0.0)),
            )
        elif formula == "newton":
            formula_params = NewtonParams(
                trap_x=float(raw.get("trap_x", 0.0)),
                trap_y=float(raw.get("trap_y", 0.0)),
            )
        elif is_julia or formula == "julia":
            formula_params = JuliaParams(
                cx=float(raw.get("julia_real", -0.8)),
                cy=float(raw.get("julia_imag", 0.156)),
            )
        else:
            formula_params = StandardParams()

    return cls(
        formula=formula,
        center_x=float(raw.get("center_x", -0.5)),
        center_y=float(raw.get("center_y", 0.0)),
        scale=max(1e-12, float(raw.get("scale", 3.0))),
        max_iterations=max(1, int(raw.get("max_iterations", 256))),
        is_julia=bool(raw.get("is_julia", False)),
        formula_params=formula_params,
        coloring_mode=str(raw.get("coloring_mode", "smooth_escape")),
        palette_offset=float(raw.get("palette_offset", 0.0)) % 1.0,
        power=max(2, int(raw.get("power", 3))),
    )
```

- [ ] **Step 7.6: Update ViewportState.to_dict()**

Replace `to_dict` to serialize `formula_params` as a nested dict with a `type` key:

```python
def to_dict(self) -> dict[str, Any]:
    fp = self.formula_params
    if isinstance(fp, JuliaParams):
        fp_dict: dict[str, Any] = {"type": "julia", "cx": fp.cx, "cy": fp.cy}
    elif isinstance(fp, PhoenixParams):
        fp_dict = {"type": "phoenix", "real": fp.real, "imag": fp.imag}
    elif isinstance(fp, NewtonParams):
        fp_dict = {"type": "newton", "trap_x": fp.trap_x, "trap_y": fp.trap_y}
    else:
        fp_dict = {"type": "standard"}

    return {
        "formula": self.formula,
        "center_x": self.center_x,
        "center_y": self.center_y,
        "scale": self.scale,
        "max_iterations": self.max_iterations,
        "is_julia": self.is_julia,
        "formula_params": fp_dict,
        "coloring_mode": self.coloring_mode,
        "palette_offset": self.palette_offset,
        "power": self.power,
    }
```

- [ ] **Step 7.7: Update ParamsState**

`ParamsState` has its own flat fields (`julia_real`, `julia_imag`, etc.) and `from_viewport_state` / `to_viewport_state`. Update `ParamsState` the same way:

Add `formula_params: FormulaParams` field, remove `julia_real`, `julia_imag`, `phoenix_real`, `phoenix_imag`, `trap_x`, `trap_y`.

Update `from_viewport_state`:
```python
@classmethod
def from_viewport_state(
    cls,
    viewport: ViewportState,
    *,
    cycle_active: bool = False,
    cycle_speed: float = 10.0,
) -> ParamsState:
    return cls(
        formula=viewport.formula,
        is_julia=viewport.is_julia,
        power=viewport.power,
        formula_params=viewport.formula_params,
        max_iterations=viewport.max_iterations,
        scale=viewport.scale,
        coloring_mode=viewport.coloring_mode,
        cycle_active=cycle_active,
        cycle_speed=cycle_speed,
    )
```

Update `to_viewport_state`:
```python
def to_viewport_state(
    self,
    *,
    center_x: float = -0.5,
    center_y: float = 0.0,
    palette_offset: float = 0.0,
) -> ViewportState:
    return ViewportState(
        formula=self.formula,
        center_x=center_x,
        center_y=center_y,
        scale=self.scale,
        max_iterations=self.max_iterations,
        is_julia=self.is_julia,
        formula_params=self.formula_params,
        coloring_mode=self.coloring_mode,
        palette_offset=palette_offset,
        power=self.power,
    )
```

- [ ] **Step 7.8: Update callers in viewport.py**

In `fractal-studio/ui/src/fractal_studio/viewport.py`, `FractalParamsPanel.to_state()` constructs a `ViewportState` from widget values. Update it to build the appropriate `FormulaParams` based on the current formula:

```python
from fractal_studio.state import (
    JuliaParams, PhoenixParams, NewtonParams, StandardParams, ViewportState
)

# Inside to_state():
formula = self._formula_combo.currentText().lower()
is_julia = self._mode_combo.currentIndex() == 1

if formula == "phoenix":
    formula_params = PhoenixParams(
        real=self._phoenix_real_spin.value(),
        imag=self._phoenix_imag_spin.value(),
    )
elif formula == "newton":
    formula_params = NewtonParams(
        trap_x=self._trap_x_spin.value(),
        trap_y=self._trap_y_spin.value(),
    )
elif is_julia or formula == "julia":
    formula_params = JuliaParams(
        cx=self._julia_real_spin.value(),
        cy=self._julia_imag_spin.value(),
    )
else:
    formula_params = StandardParams()
```

Update `apply_state()` to read from `formula_params` instead of flat fields.

- [ ] **Step 7.9: Update viewport_controller.py**

In `ui/controllers/viewport_controller.py`, the render call passes formula-specific params to the backend. Update it to unpack `formula_params`:

```python
fp = state.formula_params
julia_real = fp.cx if isinstance(fp, JuliaParams) else 0.0
julia_imag = fp.cy if isinstance(fp, JuliaParams) else 0.0
phoenix_real = fp.real if isinstance(fp, PhoenixParams) else 0.0
phoenix_imag = fp.imag if isinstance(fp, PhoenixParams) else 0.0
trap_x = fp.trap_x if isinstance(fp, NewtonParams) else 0.0
trap_y = fp.trap_y if isinstance(fp, NewtonParams) else 0.0
```

Pass these unpacked values to `backend.render_fractal()` as before.

- [ ] **Step 7.10: Run serialization tests**

```
python -m pytest tests/test_backend.py::ViewportStateFormulaParamsTests -v
```
Expected: all 3 pass.

- [ ] **Step 7.11: Run full unit suite**

```
python -m pytest -m unit -v
```
Expected: all pass.

- [ ] **Step 7.12: Commit**

```
git add fractal-studio/ui/src/fractal_studio/state.py fractal-studio/ui/src/fractal_studio/viewport.py fractal-studio/ui/src/fractal_studio/backend.py fractal-studio/ui/src/fractal_studio/ui/controllers/ fractal-studio/ui/tests/test_backend.py
git commit -m "Decompose ViewportState flat fields into formula-specific sub-structs"
```

---

## Task 8: Shrink MainWindowSectionsState.bind()

Currently `bind()` is ~80 lines because it constructs lambda closures to wire collaborators to panel state machines after construction. This task moves collaborators into panel state constructors, making each state machine self-contained.

**Files:**
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/panel_state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/ui/sections/state.py`
- Modify: `fractal-studio/ui/src/fractal_studio/main_window_factory.py`

- [ ] **Step 8.1: Update MainWindowViewportState constructor**

In `panel_state.py`, change `MainWindowViewportState.__init__` to accept its collaborators directly and remove `bind_collaborators()`. Note that `refresh_export_presets` must be included — the old `bind_collaborators` accepted it and `apply_aspect_ratio_mode` calls it:

```python
class MainWindowViewportState:
    def __init__(
        self,
        sections_state: MainWindowSectionsState,
        controller: ExportController | None = None,
        export_panel: ExportPanelCoordinator | None = None,
        refresh_export_presets: Callable[[], None] | None = None,
    ) -> None:
        self._sections_state = sections_state
        self._controller = controller
        self._export_panel = export_panel
        self._refresh_export_presets = refresh_export_presets
        self.viewport: FractalViewportWidget | None = None
        self.viewport_hint_label: QLabel | None = None
        self.aspect_ratio_combo: QComboBox | None = None
        self.aspect_ratio_mode: str = "square"
```

Remove `bind_collaborators()` from this class.

- [ ] **Step 8.2: Update all remaining panel state constructors**

Apply the same pattern as Step 8.1 to each of the five remaining panel state classes. For each: copy the parameter list from its existing `bind_collaborators()` signature into `__init__`, default all to `None`, assign to `self._x`, then delete `bind_collaborators()`.

The most complex is `MainWindowFavoritesState` — show it explicitly:

```python
class MainWindowFavoritesState:
    def __init__(
        self,
        sections_state: MainWindowSectionsState,
        favorites_controller: FavoritesController | None = None,
        favorites_panel: FavoritesPanelCoordinator | None = None,
        favorites_workflow: FavoritesWorkflowCoordinator | None = None,
        favorites_repo: FavoritesRepository | None = None,
        owner: MainWindow | None = None,
        hover_panel_getter: Callable[[], QLabel | None] | None = None,
        viewport_getter: Callable[[], FractalViewportWidget | None] | None = None,
        params_panel_getter: Callable[[], FractalParamsPanel | None] | None = None,
        editor_getter: Callable[[], ColorCubeEditor | None] | None = None,
        preview_palette_getter: Callable[[], PalettePreviewWidget | None] | None = None,
        apply_aspect_ratio_mode: Callable[[str, bool], str] | None = None,
        aspect_ratio_mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self._sections_state = sections_state
        self._favorites_controller = favorites_controller
        self._favorites_panel = favorites_panel
        self._favorites_workflow = favorites_workflow
        self._favorites_repo = favorites_repo
        self._owner = owner
        self._hover_panel_getter = hover_panel_getter
        self._viewport_getter = viewport_getter
        self._params_panel_getter = params_panel_getter
        self._editor_getter = editor_getter
        self._preview_palette_getter = preview_palette_getter
        self._apply_aspect_ratio_mode = apply_aspect_ratio_mode
        self._aspect_ratio_mode_getter = aspect_ratio_mode_getter
        self.favorites: list[FavoriteSnapshot] = []
        self.selected_row: FavoriteThumbnailRow | None = None
        self.fav_rows: list[FavoriteThumbnailRow] = []
        self.fav_scroll_widget: QWidget | None = None
        self.fav_scroll_layout: QVBoxLayout | None = None
```

The signatures for the remaining three states (`MainWindowSidebarState`, `MainWindowPaletteState`, `MainWindowColormapState`, `MainWindowExportState`) follow the exact same pattern — copy from their existing `bind_collaborators()` parameter lists.

- [ ] **Step 8.3: Rewrite MainWindowSectionsState.__post_init__ to pass collaborators at construction**

In `state.py`, `__post_init__` currently constructs all panel states with just `self`. After this step it will pass all collaborators. But `__post_init__` runs before `bind()` is called — so we need to restructure: panel states are constructed IN `bind()` instead of `__post_init__`.

Replace `__post_init__` + `bind()` with a single `bind()` that constructs panel states:

```python
def bind(self, owner: MainWindow, context: MainWindowContext) -> None:
    self.owner = owner
    self.favorites_repo = context.favorites_repo
    self.settings_repo = context.settings_repo
    # ... (all the existing field assignments) ...
    self.theme_workflow = context.theme_workflow
    self.backend_loaded = context.backend_loaded
    self.backend_profile = context.backend_profile

    # Construct panel states with collaborators
    self._export_state = MainWindowExportState(
        sections_state=self,
        export_panel=self.export_panel,
        controller=self.controller,
        owner=self.owner,
        viewport_getter=lambda: self.viewport,
        aspect_ratio_mode_getter=lambda: self.aspect_ratio_mode,
    )
    self._viewport_state = MainWindowViewportState(
        sections_state=self,
        controller=self.controller,
        export_panel=self.export_panel,
        refresh_export_presets=self._export_state.refresh_export_presets,
    )
    self._sidebar_state = MainWindowSidebarState(
        sections_state=self,
        sidebar_wiring=self.sidebar_wiring,
        viewport_getter=lambda: self.viewport,
        settings_service=self.settings_service,
        backend_loaded_getter=lambda: self.backend_loaded,
        backend_available_getter=lambda: (
            self.backend.available if self.backend is not None else False
        ),
    )
    self._palette_state = MainWindowPaletteState(
        sections_state=self,
        palette_preview=self.palette_preview,
        backend=self.backend,
        legacy_palette_size_getter=lambda: (
            None if self.backend_profile is None
            else self.backend_profile.legacy_palette_size
        ),
        editor_getter=lambda: self._colormap_state.editor,
    )
    self._colormap_state = MainWindowColormapState(
        sections_state=self,
        palette_panel=self.palette_panel,
        backend=self.backend,
        owner=self.owner,
        legacy_palette_size_getter=lambda: (
            None if self.backend_profile is None
            else self.backend_profile.legacy_palette_size
        ),
    )
    self._favorites_state = MainWindowFavoritesState(
        sections_state=self,
        favorites_controller=self.favorites_controller,
        favorites_panel=self.favorites_panel,
        favorites_workflow=self.favorites_workflow,
        favorites_repo=self.favorites_repo,
        owner=self.owner,
        hover_panel_getter=lambda: self.hover_panel,
        viewport_getter=lambda: self.viewport,
        params_panel_getter=lambda: self.params_panel,
        editor_getter=lambda: self._colormap_state.editor,
        preview_palette_getter=lambda: self._palette_state.preview_palette,
        apply_aspect_ratio_mode=self._viewport_state.apply_aspect_ratio_mode,
        aspect_ratio_mode_getter=lambda: self.aspect_ratio_mode,
    )

    self.validate()
```

All `editor_getter`, `preview_palette_getter`, etc. are lambdas — they capture `self` and are evaluated lazily when called, so construction order does not matter.

Remove `__post_init__` entirely.

- [ ] **Step 8.4: Update validate() for constructor-based wiring**

`validate()` no longer checks post-bind attributes on panel states (they're now constructor args). Simplify it to only check the top-level `MainWindowSectionsState` fields — the panel state constructors enforce their own preconditions via type hints:

```python
def validate(self) -> None:
    required = [
        "owner", "favorites_repo", "settings_repo", "settings_service",
        "startup", "favorites_controller", "favorites_panel",
        "favorites_workflow", "sections", "theme_controller", "backend",
        "export_service", "palette_service", "palette_panel",
        "palette_preview", "sidebar_wiring", "controller",
        "export_panel", "settings_dialog", "theme_workflow",
    ]
    for name in required:
        if getattr(self, name, None) is None:
            raise RuntimeError(
                f"MainWindowSectionsState.validate(): '{name}' was not bound."
            )
```

- [ ] **Step 8.5: Run unit tests**

```
python -m pytest -m unit -v
```
Expected: all pass.

- [ ] **Step 8.6: Confirm bind() line count**

```
python -c "
import ast, textwrap
src = open('src/fractal_studio/ui/sections/state.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'bind':
        print(f'bind() is {node.end_lineno - node.lineno + 1} lines')
"
```
Expected: under 60 lines (down from ~80). The lambda closures for wiring are now in the constructor calls, making the structure clearer.

- [ ] **Step 8.7: Commit**

```
git add fractal-studio/ui/src/fractal_studio/ui/sections/ fractal-studio/ui/src/fractal_studio/main_window_factory.py
git commit -m "Move panel state collaborators into constructors; shrink bind()"
```

---

## Final Verification

- [ ] Run `python -m pytest -m unit -v` — all unit tests green.
- [ ] Confirm no references to deleted files remain: `grep -r "main_window_controller" fractal-studio/ui/src/` should return empty.
- [ ] Confirm adapter directory structure: `find fractal-studio/ui/src/fractal_studio/ui/sections/ -name "*.py"` should show `adapters/` subdirectory and no loose `*_adapter.py` files.
