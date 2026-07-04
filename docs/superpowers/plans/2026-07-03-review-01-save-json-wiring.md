# Review-01: Rewire Colormap "Save JSON" to Palette Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written.

**Goal:** Fix the user-facing bug where the Colormap Editor's "Save JSON" button saves a *favorites snapshot* instead of exporting the palette to a JSON file.

**Architecture:** The palette-JSON save pipeline (`PaletteWorkflowService.save_palette_json` → `PalettePanelCoordinator.save_palette_json`) already exists and is unit-tested but is unreachable from the UI. We add the missing UI edge: a `save_palette_json` method on `MainWindowColormapState` (owns the file dialog), expose it through `ColormapPanelPorts` and `ColormapPanelPortsAdapter`, and connect the button to it. The colormap panel then no longer needs `save_favorite`, so we remove `_FavoriteActionsMixin` from its adapter and `save_favorite` from its port protocol.

**Tech Stack:** Python 3.12, PySide6 ≥ 6.8, pytest (markers: `unit`, `integration`).

**Recommended model:** Claude Sonnet 4.6. *Reasoning:* single well-specified wiring fix with the design fully decided in this plan; the executor needs fidelity, not judgment. Cheap, fast, and low-risk.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — follow its engineering standards (SOLID, small functions, TDD, direct communication, commit safety). Its instructions take precedence over this plan on style questions. Note: its C++ guard-macro and Unreal/Builder sections do not apply to this Python repo; use plain early returns.
2. `README.md` sections "Running Tests" and "Quick Start — UI Only".

## Global Constraints

- Python ≥ 3.12; PySide6 ≥ 6.8; no new dependencies.
- The app must keep working in UI-only mode (Rust core absent, `CoreBackend(None)`); never assume `fractal_core` is importable.
- Tests requiring Qt get `pytestmark = pytest.mark.integration`; pure-Python tests get `@pytest.mark.unit`.
- Run tests from the `ui/` directory with the repo venv: `..\.venv\Scripts\python.exe -m pytest` (Windows) — default runs unit only; use `-m "unit or integration"` for the full suite.
- Follow existing local patterns (optional collaborators with getter callables) — a later plan (review-06) hardens them; do not do that hardening here.
- Commit messages: conventional-commit style matching repo history (`fix:`, `feat:`, `test:`, `refactor:`).

## Background — the bug

`ui/src/fractal_studio/ui/sections/sections.py` lines 164-165:

```python
save_button = QPushButton("Save JSON")
save_button.clicked.connect(ports.save_favorite)
```

`ports` here is `ColormapPanelPortsAdapter`, whose `save_favorite` (inherited from `_FavoriteActionsMixin` in `ui/src/fractal_studio/ui/sections/adapters/base.py`) calls `self._state.favorites.save_favorite()` — saving a viewport favorite. The user expects a palette JSON file dialog. `PalettePanelCoordinator.save_palette_json` (`ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py:16-33`) is the intended target and is currently dead from the UI.

---

### Task 1: Regression test proving the button is miswired

**Files:**
- Create: `ui/tests/test_colormap_panel_wiring.py`

**Interfaces:**
- Consumes: `MainWindowSections` (`fractal_studio.ui.sections.sections`), `MainWindowSectionsPorts` (`fractal_studio.ui.sections.ports`), `CoreBackend`, `default_profile` (`fractal_studio.backend`).
- Produces: test module later tasks keep green; stub class `RecordingColormapPorts` used only inside this file.

- [ ] **Step 1: Write the failing test**

Create `ui/tests/test_colormap_panel_wiring.py`:

```python
from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.integration

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from fractal_studio.backend import CoreBackend, default_profile  # noqa: E402
from fractal_studio.ui.sections.ports import MainWindowSectionsPorts  # noqa: E402
from fractal_studio.ui.sections.sections import MainWindowSections  # noqa: E402


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class RecordingColormapPorts:
    """Implements ColormapPanelPorts, recording which port methods fire."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.backend = CoreBackend(None)
        self.backend_profile = default_profile()
        self.viewport = None

    def show_status(self, message: str) -> None:
        self.calls.append("show_status")

    def set_editor(self, editor) -> None:
        self.calls.append("set_editor")

    def update_palette_previews(self, palette) -> None:
        pass

    def update_control_summary(self, points) -> None:
        pass

    def save_favorite(self) -> None:
        self.calls.append("save_favorite")

    def save_palette_json(self) -> None:
        self.calls.append("save_palette_json")

    def load_palette_json(self) -> None:
        self.calls.append("load_palette_json")

    def export_legacy_map(self) -> None:
        self.calls.append("export_legacy_map")


def _find_button(panel, label: str) -> QPushButton:
    buttons = [b for b in panel.findChildren(QPushButton) if b.text() == label]
    assert len(buttons) == 1, f"expected exactly one '{label}' button, found {len(buttons)}"
    return buttons[0]


class TestColormapSaveJsonWiring(unittest.TestCase):
    def test_save_json_button_triggers_palette_save_not_favorite(self) -> None:
        _get_app()
        colormap_ports = RecordingColormapPorts()
        sections = MainWindowSections(
            MainWindowSectionsPorts(
                viewport=None,
                palette=None,
                colormap=colormap_ports,
                backend=None,
                export=None,
                favorites=None,
                sidebar=None,
            )
        )
        panel = sections.build_colormap_panel()

        _find_button(panel, "Save JSON").click()

        self.assertIn("save_palette_json", colormap_ports.calls)
        self.assertNotIn("save_favorite", colormap_ports.calls)
```

Note: `build_colormap_panel` only touches `ports.colormap`, so `None` placeholders for the other six port groups are safe. `MainWindowSectionsPorts` is a plain frozen dataclass; it does not validate field types at runtime.

- [ ] **Step 2: Run the test to verify it fails for the right reason**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest tests/test_colormap_panel_wiring.py -m integration -v
```

Expected: FAIL — `AssertionError` because `calls` contains `"save_favorite"` and not `"save_palette_json"` (the stub's `save_palette_json` is never connected).

- [ ] **Step 3: Commit the failing test (red)**

```powershell
git add ui/tests/test_colormap_panel_wiring.py
git commit -m "test: prove Colormap 'Save JSON' button is wired to save_favorite"
```

---

### Task 2: Add `save_palette_json` to the colormap panel state

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (class `MainWindowColormapState`, currently lines 219-279)
- Modify: `ui/src/fractal_studio/main_window_factory.py` (construction of `MainWindowColormapState`, currently lines 134-139)
- Create: `ui/tests/test_colormap_panel_state.py`

**Interfaces:**
- Consumes: `PalettePanelCoordinator.save_palette_json(*, path, editor, backend, palette_size, set_status) -> bool` (exists, unchanged).
- Produces: `MainWindowColormapState.save_palette_json() -> None` — Task 3's adapter calls exactly this; constructor gains keyword arg `palette_size_getter: Callable[[], int | None] | None = None`.

- [ ] **Step 1: Write the failing unit-level test**

Create `ui/tests/test_colormap_panel_state.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # panel_state imports PySide6

from fractal_studio.ui.sections import panel_state as panel_state_module  # noqa: E402
from fractal_studio.ui.sections.panel_state import MainWindowColormapState  # noqa: E402


class RecordingPalettePanel:
    def __init__(self) -> None:
        self.save_kwargs: dict | None = None

    def save_palette_json(self, **kwargs) -> bool:
        self.save_kwargs = kwargs
        return True


class TestColormapStateSavePaletteJson(unittest.TestCase):
    def test_save_palette_json_delegates_with_profile_palette_size(self) -> None:
        panel = RecordingPalettePanel()
        statuses: list[str] = []
        state = MainWindowColormapState(
            palette_panel=panel,
            backend=object(),
            on_status=statuses.append,
            legacy_palette_size_getter=lambda: 256,
            palette_size_getter=lambda: 2048,
        )
        state.set_editor(object())

        original_dialog = panel_state_module.QFileDialog.getSaveFileName
        panel_state_module.QFileDialog.getSaveFileName = staticmethod(
            lambda *args, **kwargs: (str(Path("C:/tmp/out.json")), "")
        )
        try:
            state.save_palette_json()
        finally:
            panel_state_module.QFileDialog.getSaveFileName = original_dialog

        assert panel.save_kwargs is not None
        self.assertEqual(panel.save_kwargs["palette_size"], 2048)
        self.assertEqual(panel.save_kwargs["path"], Path("C:/tmp/out.json"))

    def test_save_palette_json_passes_none_path_when_dialog_cancelled(self) -> None:
        panel = RecordingPalettePanel()
        state = MainWindowColormapState(
            palette_panel=panel,
            backend=object(),
            on_status=lambda _msg: None,
            legacy_palette_size_getter=lambda: 256,
            palette_size_getter=lambda: 2048,
        )
        original_dialog = panel_state_module.QFileDialog.getSaveFileName
        panel_state_module.QFileDialog.getSaveFileName = staticmethod(
            lambda *args, **kwargs: ("", "")
        )
        try:
            state.save_palette_json()
        finally:
            panel_state_module.QFileDialog.getSaveFileName = original_dialog

        assert panel.save_kwargs is not None
        self.assertIsNone(panel.save_kwargs["path"])
```

- [ ] **Step 2: Run it — expect failure**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest tests/test_colormap_panel_state.py -m integration -v
```

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'palette_size_getter'`.

- [ ] **Step 3: Implement**

In `ui/src/fractal_studio/ui/sections/panel_state.py`, class `MainWindowColormapState`:

Add the constructor parameter (after `legacy_palette_size_getter`):

```python
    def __init__(
        self,
        *,
        palette_panel: PalettePanelCoordinator | None = None,
        backend: CoreBackend | None = None,
        on_status: Callable[[str], None] | None = None,
        legacy_palette_size_getter: Callable[[], int | None] | None = None,
        palette_size_getter: Callable[[], int | None] | None = None,
    ) -> None:
        self._palette_panel: PalettePanelCoordinator | None = palette_panel
        self._backend: CoreBackend | None = backend
        self._on_status: Callable[[str], None] | None = on_status
        self._legacy_palette_size_getter: Callable[[], int | None] | None = (
            legacy_palette_size_getter
        )
        self._palette_size_getter: Callable[[], int | None] | None = palette_size_getter
        self.editor: ColorCubeEditor | None = None
```

Add the method (place it directly above the existing `load_palette_json`, mirroring its shape):

```python
    def save_palette_json(self) -> None:
        if (
            self._palette_panel is None
            or self._backend is None
            or self._palette_size_getter is None
        ):
            return
        palette_size = self._palette_size_getter()
        if palette_size is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            None,
            "Save palette",
            str(Path.cwd() / "palette.json"),
            "Fractal Studio Palette (*.json)",
        )
        path = Path(path_str) if path_str else None
        self._palette_panel.save_palette_json(
            path=path,
            editor=self.editor,
            backend=self._backend,
            palette_size=palette_size,
            set_status=self._on_status if self._on_status is not None else lambda _: None,
        )
```

In `ui/src/fractal_studio/main_window_factory.py`, extend the `MainWindowColormapState` construction:

```python
    colormap_state = MainWindowColormapState(
        palette_panel=palette_panel,
        backend=backend,
        on_status=on_status,
        legacy_palette_size_getter=legacy_size,
        palette_size_getter=lambda: backend_profile.palette_size,
    )
```

- [ ] **Step 4: Run the new tests — expect pass**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_colormap_panel_state.py -m integration -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```powershell
git add ui/src/fractal_studio/ui/sections/panel_state.py ui/src/fractal_studio/main_window_factory.py ui/tests/test_colormap_panel_state.py
git commit -m "feat: add save_palette_json to colormap panel state"
```

---

### Task 3: Expose the port and rewire the button

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/ports.py` (protocol `ColormapPanelPorts`, lines 36-52)
- Modify: `ui/src/fractal_studio/ui/sections/adapters/colormap_adapter.py`
- Modify: `ui/src/fractal_studio/ui/sections/sections.py` (lines 160-169, `build_colormap_panel` buttons)

**Interfaces:**
- Consumes: `MainWindowColormapState.save_palette_json()` from Task 2.
- Produces: `ColormapPanelPortsAdapter.save_palette_json() -> None`; `ColormapPanelPorts` protocol gains `save_palette_json` and loses `save_favorite`.

- [ ] **Step 1: Update the protocol**

In `ui/src/fractal_studio/ui/sections/ports.py`, in `ColormapPanelPorts`, replace the line `def save_favorite(self) -> None: ...` with:

```python
    def save_palette_json(self) -> None: ...
```

(Keep `load_palette_json` and `export_legacy_map` as they are. `FavoritesPanelPorts.save_favorite` is untouched.)

- [ ] **Step 2: Update the adapter**

Replace the full contents of `ui/src/fractal_studio/ui/sections/adapters/colormap_adapter.py` with:

```python
from __future__ import annotations

from fractal_studio.editor import ColorCubeEditor
from fractal_studio.ui.sections.adapters.base import _BasePortsAdapter


class ColormapPanelPortsAdapter(_BasePortsAdapter):
    def set_editor(self, editor: ColorCubeEditor) -> None:
        self._state.colormap.set_editor(editor)

    def update_palette_previews(self, palette) -> None:
        self._state.palette.update_palette_previews(palette)

    def update_control_summary(self, points) -> None:
        self._state.palette.update_control_summary(points)

    def save_palette_json(self) -> None:
        self._state.colormap.save_palette_json()

    def load_palette_json(self) -> None:
        self._state.colormap.load_palette_json()

    def export_legacy_map(self) -> None:
        self._state.colormap.export_legacy_map()
```

(`_FavoriteActionsMixin` remains in `adapters/base.py` — `FavoritesPanelPortsAdapter` still uses it.)

- [ ] **Step 3: Rewire the button**

In `ui/src/fractal_studio/ui/sections/sections.py`, `build_colormap_panel`, change:

```python
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(ports.save_favorite)
```

to:

```python
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(ports.save_palette_json)
```

- [ ] **Step 4: Run the Task 1 regression test — expect pass**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_colormap_panel_wiring.py -m integration -v
```

Expected: PASS.

- [ ] **Step 5: Run the full suite**

```powershell
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q
```

Expected: everything passes (baseline before this plan: 177 passed, 11 subtests). If any existing test asserted `ColormapPanelPorts.save_favorite` or the mixin on the colormap adapter, update it to expect `save_palette_json` — search first: `grep -rn "save_favorite" ui/tests/`.

- [ ] **Step 6: Commit**

```powershell
git add ui/src/fractal_studio/ui/sections/ports.py ui/src/fractal_studio/ui/sections/adapters/colormap_adapter.py ui/src/fractal_studio/ui/sections/sections.py
git commit -m "fix: wire Colormap 'Save JSON' button to palette JSON save, not favorites"
```

---

### Task 4: Manual verification (only if `fractal_core` is built in the venv)

- [ ] Launch `fractal-studio`, click Colormap Editor → "Save JSON", choose a path. Verify a `.json` file is written containing `"format": "fractal-studio.palette.v1"`, and that **no** new row appears in the Favorites panel. If the Rust core is not built, skip — the dialog still appears and the service reports status, which is sufficient.

## Done criteria

- Regression test from Task 1 passes; full suite green.
- Clicking "Save JSON" opens a save-file dialog for `*.json` and never creates a favorite.
