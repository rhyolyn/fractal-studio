> **Status: COMPLETED — historical record (executed 2026-05/06, verified in-tree 2026-07-03). Do not execute.** Live work is tracked in [2026-07-03-review-00-master.md](2026-07-03-review-00-master.md).

# Architecture Cleanup 02 — Service Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all PySide6 and widget imports from `services/` and `application/controllers/`, making those layers unit-testable without Qt, and enforce the boundary with an import policy test.

**Architecture:** Every method in `ExportService`, `PaletteWorkflowService`, and `FavoritesController` that currently accepts a Qt widget instance is changed to accept plain Python values instead — frozen dataclasses from `state.py`, `Path` objects, and typed callbacks. The UI edge (panel states and adapters in `ui/sections/`) reads from widgets and passes data down; it receives results and applies them back to widgets. A new import policy check in `test_import_policy.py` verifies no file under `application/` or `services/` imports from `PySide6` or from `fractal_studio.ui.widgets`. Run `arch-01` before this plan — it must be on the branch.

**Tech Stack:** Python 3.12, pytest (unit tests run without PySide6)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `ui/tests/test_import_policy.py` | Add Qt-in-services prohibition check |
| Modify | `ui/src/fractal_studio/services/export_service.py` | Remove `QWidget`, `FractalViewportWidget`, `QApplication`, `QImage`, `QFileDialog`; accept `ViewportState` + palette; return `bytes \| None` |
| Modify | `ui/src/fractal_studio/application/controllers/export_controller.py` | Remove `QWidget`, `FractalViewportWidget`; pass data down; receive bytes and save `QImage` here |
| Modify | `ui/src/fractal_studio/services/palette_service.py` | Remove `QWidget`, `QFileDialog`; accept `Path \| None` directly |
| Modify | `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py` | Show dialog before calling service; pass `Path \| None` |
| Modify | `ui/src/fractal_studio/application/controllers/favorites_controller.py` | Remove `FractalViewportWidget`, `FractalParamsPanel`, `ColorCubeEditor`, `PalettePreviewWidget`; use callbacks and plain state |
| Modify | `ui/src/fractal_studio/ui/sections/panel_state.py` | Update call sites for favorites controller |

---

## Task 1: Add Qt import prohibition to the import policy test

**Files:**
- Modify: `ui/tests/test_import_policy.py`

This test defines the boundary mechanically. Add it first so subsequent tasks have a target to pass.

- [ ] **Step 1: Append the new test to `test_import_policy.py`**

At the end of `ui/tests/test_import_policy.py`, add:

```python
_SERVICES_ROOTS = ("services", "application")
_QT_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+PySide6\b"
)
_WIDGET_IMPORT_PATTERN = re.compile(
    r"^\s*from\s+fractal_studio\.ui\.widgets\b"
)


@pytest.mark.unit
def test_no_qt_imports_in_services_or_application() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src" / "fractal_studio"

    violations: list[str] = []
    for layer in _SERVICES_ROOTS:
        layer_root = src_root / layer
        if not layer_root.exists():
            continue
        for file_path in _iter_python_files(layer_root):
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for line_no, line in enumerate(lines, start=1):
                if _QT_IMPORT_PATTERN.match(line) or _WIDGET_IMPORT_PATTERN.match(line):
                    rel = file_path.relative_to(repo_root)
                    violations.append(f"{rel}:{line_no}: {line.strip()}")

    assert not violations, (
        "PySide6 and ui.widgets imports are forbidden in services/ and application/.\n"
        + "\n".join(violations)
    )
```

- [ ] **Step 2: Run the new test to see current violations**

```powershell
cd ui && pytest tests/test_import_policy.py::test_no_qt_imports_in_services_or_application -v
```

Expected: FAIL — output lists violations in `export_service.py`, `palette_service.py`, `favorites_controller.py`, and others. Record the full list; these are your work queue for this plan.

- [ ] **Step 3: Commit the test (red)**

```powershell
git add ui/tests/test_import_policy.py
git commit -m "test: add Qt import prohibition for services and application layers"
```

---

## Task 2: Fix `ExportService`

**Files:**
- Modify: `ui/src/fractal_studio/services/export_service.py`

**Current signature** (takes `FractalViewportWidget`, calls `QFileDialog`, `QApplication.processEvents()`, wraps in `QImage`):
```python
def export_render(self, parent, viewport, width, height, set_status) -> bool
```

**Target:** service receives pure data, returns raw RGBA bytes. The panel state handles the file dialog and `QImage.save()`.

- [ ] **Step 1: Rewrite `export_service.py`**

Replace the entire file with:

```python
from __future__ import annotations

from collections.abc import Callable

from fractal_studio.backend import CoreBackend
from fractal_studio.state import ViewportState


class ExportService:
    def __init__(self, backend: CoreBackend) -> None:
        self._backend = backend

    def export_render(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bytes | None:
        if not self._backend.available:
            set_status("Backend not available.")
            return None

        set_status(f"Rendering {width}×{height}...")
        kwargs = viewport_state.to_render_kwargs()
        return self._backend.render_fractal(
            viewport_state.formula,
            width,
            height,
            is_julia=viewport_state.is_julia,
            julia_real=kwargs["julia_real"],
            julia_imag=kwargs["julia_imag"],
            power=viewport_state.power,
            phoenix_real=kwargs["phoenix_real"],
            phoenix_imag=kwargs["phoenix_imag"],
            center_x=viewport_state.center_x,
            center_y=viewport_state.center_y,
            scale=viewport_state.scale,
            max_iterations=viewport_state.max_iterations,
            palette=palette,
            coloring_mode=viewport_state.coloring_mode,
            trap_x=kwargs["trap_x"],
            trap_y=kwargs["trap_y"],
            palette_offset=viewport_state.palette_offset,
        )
```

- [ ] **Step 2: Update `ExportController.export_render()` to match the new service**

In `ui/src/fractal_studio/application/controllers/export_controller.py`, the `export_render` method currently passes `parent` and `viewport` widget to the service. Update it to accept data, call the service for bytes, and save the image using `QImage` (Qt is allowed in the controller for now — it will move further in arch-03; for this plan we only care about `services/`).

Replace the `export_render` method and update its imports:

At the top of `export_controller.py`, change:
```python
from PySide6.QtWidgets import QComboBox, QSpinBox, QWidget
from fractal_studio.viewport import FractalViewportWidget
```
to:
```python
from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QComboBox, QFileDialog, QSpinBox, QWidget

from fractal_studio.state import ViewportState
```

Replace the `export_render` method:

```python
    def export_render(
        self,
        parent: QWidget,
        viewport_state: ViewportState | None,
        palette: list[tuple[int, int, int]],
        width: int,
        height: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if viewport_state is None:
            return False

        path, _ = QFileDialog.getSaveFileName(
            parent,
            f"Export {width}×{height} render",
            str(Path.cwd() / f"fractal_{width}x{height}.png"),
            "PNG Image (*.png)",
        )
        if not path:
            return False

        raw = self._export_service.export_render(
            viewport_state, palette, width, height, set_status
        )
        if raw is None:
            return False

        image = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        image.save(path)
        set_status(f"Saved {width}×{height} render to {path}")
        return True
```

- [ ] **Step 3: Find and update callers of `ExportController.export_render()`**

```powershell
rg -rn "export_render" ui/src
```

For each call site (likely in an export panel adapter or panel state), update to pass `viewport.to_state()` and `viewport.palette()` instead of the widget. The call site will look like:

Before (conceptual — match actual code):
```python
controller.export_render(parent, viewport_widget, width, height, set_status)
```

After:
```python
viewport_state = viewport_widget.to_state() if viewport_widget is not None else None
palette = viewport_widget.palette() if viewport_widget is not None else []
controller.export_render(parent, viewport_state, palette, width, height, set_status)
```

Read each call site file before editing to match its exact current code.

- [ ] **Step 4: Run the import policy test**

```powershell
cd ui && pytest tests/test_import_policy.py::test_no_qt_imports_in_services_or_application -v
```

`export_service.py` violations should be gone. Other violations may remain — that's expected.

- [ ] **Step 5: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add ui/src/fractal_studio/services/export_service.py ui/src/fractal_studio/application/controllers/export_controller.py
git commit -m "refactor: ExportService accepts ViewportState+palette; ExportController handles QImage+dialog"
```

---

## Task 3: Fix `PaletteWorkflowService`

**Files:**
- Modify: `ui/src/fractal_studio/services/palette_service.py`
- Modify: `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py`

**Current problem:** Methods accept `parent: QWidget | None` and have `QFileDialog.getSaveFileName` as a default parameter, creating a PySide6 dependency at import time.

**Fix:** Remove `parent` and `get_save_file_name` / `get_open_file_name` parameters — the service accepts a resolved `path: Path | None` directly. The coordinator shows the dialog and passes the resolved path.

- [ ] **Step 1: Rewrite `palette_service.py`**

Replace the entire file with:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fractal_studio.backend import CoreBackend


class PaletteWorkflowService:
    def save_palette_json(
        self,
        path: Path | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if not backend.available or path is None:
            return False
        backend.export_palette_json(str(path), control_points, palette_size)
        set_status(f"Saved palette to {path}")
        return True

    def load_palette_json(
        self,
        path: Path | None,
        backend: CoreBackend,
        set_control_points: Callable[[list[tuple[int, int, int]]], None],
        set_status: Callable[[str], None],
    ) -> bool:
        if not backend.available or path is None:
            return False
        palette_size, control_points = backend.import_palette_json(str(path))
        set_control_points(control_points)
        set_status(
            f"Loaded palette with {len(control_points)} control points. "
            f"Saved palette size was {palette_size}."
        )
        return True

    def export_legacy_map(
        self,
        path: Path | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        legacy_palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if not backend.available or path is None or len(control_points) < 4:
            set_status(
                "Add at least four control points before exporting a legacy map."
            )
            return False
        palette = backend.generate_palette(control_points, legacy_palette_size)
        backend.export_legacy_map(str(path), palette)
        set_status(f"Exported legacy palette to {path}")
        return True
```

- [ ] **Step 2: Find `PalettePanelCoordinator` and update its calls to show dialogs**

```powershell
rg -n "palette_service\|save_palette_json\|load_palette_json\|export_legacy_map" ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py
```

Read `ui/src/fractal_studio/application/coordinators/palette_panel_coordinator.py` in full, then update each call site to:
1. Show the `QFileDialog` in the coordinator (which IS in `application/coordinators/` — check if that's also in scope for the policy)
2. Pass the resolved path to the service

Wait — `application/coordinators/` is also forbidden by the import policy. The dialog must move to the adapter/panel state level (`ui/sections/`).

Find where palette actions are wired in the panel state:
```powershell
rg -rn "load_palette_json\|save_palette_json\|export_legacy_map" ui/src/fractal_studio/ui
```

The coordinator method that calls the service should be updated to accept a `path: Path | None` parameter, and the panel state (which is in `ui/sections/` and CAN use Qt) shows the dialog and passes the path.

For each coordinator method that calls the service, change the signature to accept `path: Path | None` and pass it through to the service. Then in the panel state call site, add the dialog call before invoking the coordinator.

Read each relevant file before editing to get exact current code.

- [ ] **Step 3: Run the import policy test**

```powershell
cd ui && pytest tests/test_import_policy.py::test_no_qt_imports_in_services_or_application -v
```

`palette_service.py` violations should be gone.

- [ ] **Step 4: Run unit tests**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add ui/src/fractal_studio/services/palette_service.py
git commit -m "refactor: PaletteWorkflowService accepts Path instead of QWidget+QFileDialog"
```

---

## Task 4: Fix `FavoritesController`

**Files:**
- Modify: `ui/src/fractal_studio/application/controllers/favorites_controller.py`
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py` (call sites)

**Current problems:**
- `build_snapshot()` accepts `FractalViewportWidget` to call `.to_state()` and `.palette()`
- `save_favorite()` accepts `FractalViewportWidget` and `ColorCubeEditor`
- `restore_snapshot()` accepts `FractalViewportWidget`, `FractalParamsPanel`, `ColorCubeEditor`, `PalettePreviewWidget` and writes to them directly
- `load_favorite_row()` accepts the same widget set
- `update_palette_previews()` accepts `ColorCubeEditor`, `PalettePreviewWidget` instances

**Fix:** Replace widget parameters with data and callbacks.

- [ ] **Step 1: Rewrite `favorites_controller.py`**

Replace the entire file with:

```python
from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

from fractal_studio.state import FavoriteSnapshot, ParamsState, ViewportState


class FavoritesController:
    def build_favorite_name(
        self,
        state: ViewportState,
        existing_names: set[str],
        now: Callable[[], datetime.datetime],
    ) -> str:
        timestamp = now().strftime("%Y-%m-%d %H:%M:%S")
        base_name = (
            f"{state.formula} ({state.center_x:.3f}, {state.center_y:.3f}) {timestamp}"
        )
        if base_name not in existing_names:
            return base_name
        suffix = 2
        while f"{base_name} ({suffix})" in existing_names:
            suffix += 1
        return f"{base_name} ({suffix})"

    def build_snapshot(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        control_points: list[tuple[int, int, int]],
        aspect_ratio_mode: str,
        name: str,
        thumbnail: str,
    ) -> FavoriteSnapshot:
        return FavoriteSnapshot(
            favorite_id=str(uuid.uuid4()),
            saved_at=datetime.datetime.now().isoformat(timespec="seconds"),
            aspect_ratio_mode=aspect_ratio_mode,
            name=name,
            viewport=viewport_state,
            control_points=[(int(p[0]), int(p[1]), int(p[2])) for p in control_points],
            palette=[(int(c[0]), int(c[1]), int(c[2])) for c in palette],
            thumbnail=thumbnail,
        )

    def save_favorite(
        self,
        viewport_state: ViewportState,
        palette: list[tuple[int, int, int]],
        control_points: list[tuple[int, int, int]],
        aspect_ratio_mode: str,
        favorites: list[FavoriteSnapshot],
        build_name: Callable[[ViewportState], str],
        capture_thumbnail: Callable[[], str],
        add_favorite: Callable[[FavoriteSnapshot], None],
        add_row: Callable[[FavoriteSnapshot], None],
        persist: Callable[[], None],
        show_status: Callable[[str], None],
    ) -> FavoriteSnapshot:
        snapshot = self.build_snapshot(
            viewport_state=viewport_state,
            palette=palette,
            control_points=control_points,
            aspect_ratio_mode=aspect_ratio_mode,
            name=build_name(viewport_state),
            thumbnail=capture_thumbnail(),
        )
        add_favorite(snapshot)
        add_row(snapshot)
        persist()
        show_status(f"Saved favorite: {snapshot.name}")
        return snapshot

    def persist_favorites(
        self,
        favorites: list[FavoriteSnapshot],
        save_to_repo: Callable[[list[FavoriteSnapshot]], None],
    ) -> None:
        save_to_repo(list(favorites))

    def load_favorites(
        self,
        load_from_repo: Callable[[], list[FavoriteSnapshot]],
    ) -> list[FavoriteSnapshot]:
        try:
            return list(load_from_repo())
        except (TypeError, ValueError):
            return []

    def load_favorite_row(
        self,
        row: object,
        favorites: list[FavoriteSnapshot],
        rows: list[object],
        restore_snapshot: Callable[[FavoriteSnapshot], None],
        select_row: Callable[[object], None],
        show_status: Callable[[str], None],
    ) -> None:
        idx = rows.index(row)
        snapshot = favorites[idx]
        restore_snapshot(snapshot)
        select_row(row)
        show_status(f"Restored: {snapshot.name}")

    def update_palette_previews(
        self,
        palette: list[tuple[int, int, int]],
        get_control_points: Callable[[], list[tuple[int, int, int]]],
        backend,
        legacy_palette_size: int,
        set_preview_palette: Callable[[list[tuple[int, int, int]]], None],
        set_legacy_palette: Callable[[list[tuple[int, int, int]]], None],
        set_summary_text: Callable[[str], None],
    ) -> None:
        set_preview_palette(palette)
        control_points = get_control_points()
        legacy_palette = (
            backend.generate_palette(control_points, legacy_palette_size)
            if len(control_points) >= 4 and backend.available
            else []
        )
        set_legacy_palette(legacy_palette)
        if palette:
            set_summary_text(
                f"Generated {len(palette)} internal colors and "
                f"{len(legacy_palette)} legacy export colors."
            )
        else:
            set_summary_text("Add four control points to generate a palette.")

    def restore_snapshot(
        self,
        snapshot: FavoriteSnapshot,
        apply_viewport_state: Callable[[ViewportState], None],
        apply_control_points: Callable[[list[tuple[int, int, int]]], None],
        apply_palette: Callable[[list[tuple[int, int, int]]], None],
        apply_params: Callable[[ParamsState], None],
        set_cycle_active: Callable[[bool], None],
        apply_aspect_ratio_mode: Callable[[str], None],
    ) -> None:
        apply_viewport_state(snapshot.viewport)
        apply_aspect_ratio_mode(snapshot.aspect_ratio_mode)

        if snapshot.control_points:
            apply_control_points(snapshot.control_points)

        if snapshot.palette and len(snapshot.control_points) < 4:
            apply_palette(snapshot.palette)

        params_state = ParamsState.from_viewport_state(
            snapshot.viewport, cycle_active=False
        )
        apply_params(params_state)
        set_cycle_active(False)
        apply_viewport_state(snapshot.viewport)

    def sync_params_panel(
        self,
        snapshot: FavoriteSnapshot,
        apply_params: Callable[[ParamsState], None],
    ) -> None:
        params_state = ParamsState.from_viewport_state(
            snapshot.viewport, cycle_active=False
        )
        apply_params(params_state)
```

- [ ] **Step 2: Find all call sites in panel_state.py and update them**

```powershell
rg -n "favorites_controller\.\|save_favorite\|restore_snapshot\|load_favorite_row\|update_palette_previews" ui/src/fractal_studio/ui/sections/panel_state.py
```

Read `panel_state.py` in full. For each call site, update it to:

**`save_favorite` calls:** Extract `viewport_state = viewport.to_state()`, `palette = viewport.palette()`, `control_points = editor.control_points if editor else []` before the call, then pass them as data.

**`restore_snapshot` calls:** Replace widget parameters with callback lambdas:
```python
self._favorites_controller.restore_snapshot(
    snapshot=snapshot,
    apply_viewport_state=lambda state: (
        viewport.apply_state(state, rerender=False) if viewport else None
    ),
    apply_control_points=lambda pts: (editor.set_control_points(pts) if editor else None),
    apply_palette=lambda pal: (
        viewport.set_palette(pal) if viewport else None,
        preview_palette.set_palette(pal) if preview_palette else None,
    ),
    apply_params=lambda params: (params_panel.apply_state(params) if params_panel else None),
    set_cycle_active=lambda active: (viewport.set_cycle_active(active) if viewport else None),
    apply_aspect_ratio_mode=self._apply_aspect_ratio_mode,
)
```

**`load_favorite_row` calls:** Replace widget params with a `restore_snapshot` callback that wraps the updated `restore_snapshot` call above.

**`update_palette_previews` calls:** Replace `editor`, `preview_palette`, `preview_legacy`, `palette_summary` with callables:
```python
self._favorites_controller.update_palette_previews(
    palette=palette,
    get_control_points=lambda: (editor.control_points if editor else []),
    backend=self._backend,
    legacy_palette_size=legacy_palette_size,
    set_preview_palette=lambda pal: (preview_palette.set_palette(pal) if preview_palette else None),
    set_legacy_palette=lambda pal: (preview_legacy.set_palette(pal) if preview_legacy else None),
    set_summary_text=lambda txt: (palette_summary.setText(txt) if palette_summary else None),
)
```

Read the actual current code in panel_state.py for each call site before editing — the exact variable names may differ from the conceptual examples above.

- [ ] **Step 3: Run the import policy test**

```powershell
cd ui && pytest tests/test_import_policy.py::test_no_qt_imports_in_services_or_application -v
```
Expected: PASS — no violations remain in `services/` or `application/`.

- [ ] **Step 4: Run the full unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add ui/src/fractal_studio/application/controllers/favorites_controller.py ui/src/fractal_studio/ui/sections/panel_state.py
git commit -m "refactor: FavoritesController uses data+callbacks instead of widget instances"
```

---

## Task 5: Final verification

- [ ] **Step 1: Run full import policy suite**

```powershell
cd ui && pytest tests/test_import_policy.py -v
```
Expected: all tests PASS including the new Qt prohibition test.

- [ ] **Step 2: Run full unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass, no regressions.

---

## Self-Review

**Spec coverage:**
- Import policy test added and enforced: Task 1 ✓
- `ExportService` Qt-free: Task 2 ✓
- `PaletteWorkflowService` Qt-free: Task 3 ✓
- `FavoritesController` Qt-free: Task 4 ✓
- Call sites updated: Tasks 2–4 ✓

**Placeholder scan:** Task 3 Step 2 and Task 4 Step 2 instruct the implementer to read the actual files before editing. This is intentional — the exact call site code depends on the current state, and the plan shows the pattern with enough detail to apply it.

**Type consistency:** `restore_snapshot` callback parameters use `Callable[[ViewportState], None]`, `Callable[[list[tuple[int, int, int]]], None]`, `Callable[[ParamsState], None]` consistently.
