# Architecture Cleanup 04 — Backend Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `CoreBackend` a pure null object and introduce `BackendCapabilities` so UI code reads capabilities once at startup instead of scattering `backend.available` checks through the application layer.

**Architecture:** Currently `CoreBackend` is inconsistent — `profile()` returns safe defaults when Rust is absent, but operational methods call `_require()` and raise. Other callers guard with `if backend.available`. This plan adds a `BackendCapabilities` frozen dataclass to `backend.py`, exposes it as `CoreBackend.capabilities`, converts all operational methods to return safe defaults instead of raising, and removes all `backend.available` guards from `application/` and `services/` (keeping only the status panel display usage). This plan is independent of arch-01 through arch-03 and can run in any order relative to them.

**Tech Stack:** Python 3.12, pytest (all tests run without PySide6)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `ui/src/fractal_studio/backend.py` | Add `BackendCapabilities`; add `.capabilities` property; remove `_require()`; operational methods return safe defaults |
| Modify | `ui/tests/test_backend.py` | Add tests for `BackendCapabilities` and null-object behavior |
| Modify | `ui/src/fractal_studio/ui/sections/panel_state.py` | Remove `backend.available` guards; use `backend.capabilities` where needed |
| Modify | `ui/src/fractal_studio/application/controllers/favorites_controller.py` | Remove `backend.available` guard in `update_palette_previews` |

---

## Task 1: Add `BackendCapabilities` and null-object operational methods

**Files:**
- Modify: `ui/src/fractal_studio/backend.py`
- Modify: `ui/tests/test_backend.py`

- [ ] **Step 1: Write the failing tests**

Read `ui/tests/test_backend.py` in full. Then add these tests:

```python
import pytest
from fractal_studio.backend import BackendCapabilities, CoreBackend


@pytest.mark.unit
def test_capabilities_all_false_when_no_module() -> None:
    backend = CoreBackend(None)
    caps = backend.capabilities
    assert caps.can_render is False
    assert caps.can_generate_palette is False
    assert caps.can_import_palette is False
    assert caps.can_export_palette is False


@pytest.mark.unit
def test_capabilities_is_frozen() -> None:
    caps = BackendCapabilities(
        can_render=True,
        can_generate_palette=True,
        can_import_palette=True,
        can_export_palette=True,
    )
    import dataclasses
    assert dataclasses.is_dataclass(caps)
    # Frozen dataclasses raise FrozenInstanceError on mutation
    with pytest.raises(Exception):
        caps.can_render = False  # type: ignore[misc]


@pytest.mark.unit
def test_generate_palette_returns_empty_list_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.generate_palette([(0, 0, 0), (255, 255, 255)], 256)
    assert result == []


@pytest.mark.unit
def test_color_from_face_returns_black_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.color_from_face(0, (0.5, 0.5))
    assert result == (0, 0, 0)


@pytest.mark.unit
def test_render_fractal_returns_empty_bytes_when_no_module() -> None:
    backend = CoreBackend(None)
    result = backend.render_fractal("standard", 4, 4)
    assert isinstance(result, bytes)
    assert len(result) == 0


@pytest.mark.unit
def test_available_property_false_when_no_module() -> None:
    backend = CoreBackend(None)
    assert backend.available is False
```

- [ ] **Step 2: Run the tests to see failures**

```powershell
cd ui && pytest tests/test_backend.py -v -m unit -k "capabilities or null"
```

Expected: several tests FAIL with `AttributeError: 'CoreBackend' object has no attribute 'capabilities'` and `RuntimeError` from `_require()`.

- [ ] **Step 3: Add `BackendCapabilities` and update `backend.py`**

In `ui/src/fractal_studio/backend.py`, add the `BackendCapabilities` dataclass immediately after the `BackendProfile` dataclass:

```python
@dataclass(frozen=True)
class BackendCapabilities:
    can_render: bool
    can_generate_palette: bool
    can_import_palette: bool
    can_export_palette: bool
```

Add the `capabilities` property to `CoreBackend`:

```python
    @property
    def capabilities(self) -> BackendCapabilities:
        available = self._module is not None
        return BackendCapabilities(
            can_render=available,
            can_generate_palette=available,
            can_import_palette=available,
            can_export_palette=available,
        )
```

- [ ] **Step 4: Convert operational methods to null-object safe defaults**

Remove `_require()` and update each operational method to return a safe default when `self._module is None`. Replace the entire set of operational methods:

```python
    def color_from_face(self, face: int, position: tuple[float, float]) -> Color:
        if self._module is None:
            return (0, 0, 0)
        return self._module.color_from_face(face, position)

    def project_color_to_face(self, face: int, color: Color) -> tuple[float, float]:
        if self._module is None:
            return (0.0, 0.0)
        return self._module.project_color_to_face(face, color)

    def update_control_point_from_face(
        self,
        face: int,
        color: Color,
        position: tuple[float, float],
    ) -> Color:
        if self._module is None:
            return color
        return self._module.update_control_point_from_face(face, color, position)

    def generate_palette(
        self, control_points: list[Color], palette_size: int
    ) -> list[Color]:
        if self._module is None:
            return []
        return list(self._module.generate_palette(control_points, palette_size))

    def render_fractal(
        self,
        formula: str,
        width: int,
        height: int,
        *,
        is_julia: bool = False,
        julia_real: float = 0.0,
        julia_imag: float = 0.0,
        power: int = 2,
        phoenix_real: float = 0.5,
        phoenix_imag: float = 0.0,
        center_x: float = -0.5,
        center_y: float = 0.0,
        scale: float = 3.0,
        max_iterations: int = 512,
        palette: list[Color] | None = None,
        coloring_mode: str = "smooth_escape",
        trap_x: float = 0.0,
        trap_y: float = 0.0,
        palette_offset: float = 0.0,
    ) -> bytes:
        if self._module is None:
            return b""
        return bytes(
            self._module.render_fractal(
                formula, width, height,
                center_x=center_x, center_y=center_y, scale=scale,
                max_iterations=max_iterations, power=power,
                julia_real=julia_real, julia_imag=julia_imag, is_julia=is_julia,
                phoenix_real=phoenix_real, phoenix_imag=phoenix_imag,
                palette=palette or [], coloring_mode=coloring_mode,
                trap_x=trap_x, trap_y=trap_y, palette_offset=palette_offset,
            )
        )

    def render_mandelbrot(
        self,
        width: int,
        height: int,
        center_x: float,
        center_y: float,
        scale: float,
        max_iterations: int,
        palette: list[Color],
    ) -> bytes:
        if self._module is None:
            return b""
        return bytes(
            self._module.render_mandelbrot(
                width, height, center_x, center_y, scale, max_iterations, palette
            )
        )

    def render_julia(
        self,
        width: int,
        height: int,
        constant_real: float,
        constant_imaginary: float,
        center_x: float,
        center_y: float,
        scale: float,
        max_iterations: int,
        palette: list[Color],
    ) -> bytes:
        if self._module is None:
            return b""
        return bytes(
            self._module.render_julia(
                width, height, constant_real, constant_imaginary,
                center_x, center_y, scale, max_iterations, palette,
            )
        )

    def export_legacy_map(self, path: str, palette: list[Color]) -> None:
        if self._module is None:
            return
        self._module.export_legacy_map(path, palette)

    def export_palette_json(
        self,
        path: str,
        control_points: list[Color],
        palette_size: int,
    ) -> None:
        if self._module is None:
            return
        self._module.export_palette_json(path, control_points, palette_size)

    def import_palette_json(self, path: str) -> tuple[int, list[Color]]:
        if self._module is None:
            return (0, [])
        palette_size, control_points = self._module.import_palette_json(path)
        return palette_size, list(control_points)
```

Delete the `_require()` method entirely.

- [ ] **Step 5: Run the backend tests**

```powershell
cd ui && pytest tests/test_backend.py -v -m unit
```
Expected: all pass.

- [ ] **Step 6: Run the full unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add ui/src/fractal_studio/backend.py ui/tests/test_backend.py
git commit -m "feat: add BackendCapabilities; CoreBackend is now a pure null object"
```

---

## Task 2: Remove `backend.available` guards from `application/` and `services/`

**Files:**
- Modify: `ui/src/fractal_studio/services/export_service.py`
- Modify: `ui/src/fractal_studio/services/palette_service.py`
- Modify: `ui/src/fractal_studio/application/controllers/favorites_controller.py`

Now that `CoreBackend` is a pure null object (all methods return safe defaults), callers in the application and service layers don't need to guard before calling — the null object handles it.

- [ ] **Step 1: Find all `backend.available` usages in `application/` and `services/`**

```powershell
rg -rn "backend\.available\|backend_available\|\.available" ui/src/fractal_studio/application ui/src/fractal_studio/services
```

For each hit, assess whether it's guarding a backend call (remove the guard — the null object returns a safe value) or whether it's used for a UI decision (keep it — see note below).

**Rule:** Guards of the form `if not backend.available: return False` before a backend call → remove them. The null object returns an empty/zero result, which is equally correct and needs no special path. Guards used to display UI state (e.g., enabling/disabling a button) stay in the UI layer and are not part of this task.

- [ ] **Step 2: Update `export_service.py`**

In `ExportService.export_render()`, remove:
```python
        if not self._backend.available:
            set_status("Backend not available.")
            return None
```

The render call will return `b""` when the backend is absent, and `set_status` still gets called with the rendering message. This is acceptable behavior for UI-only mode.

If you want to preserve the "not available" status message, replace the guard with a capabilities check on the result:

```python
        set_status(f"Rendering {width}×{height}...")
        kwargs = viewport_state.to_render_kwargs()
        raw = self._backend.render_fractal(...)
        if not raw:
            set_status("Backend not available — no render produced.")
            return None
        return raw
```

- [ ] **Step 3: Update `palette_service.py`**

Remove `if not backend.available: return False` guards from all three methods. The null object's `export_palette_json`, `import_palette_json`, `generate_palette`, and `export_legacy_map` now return safe defaults without raising.

```python
    def save_palette_json(
        self,
        path: Path | None,
        backend: CoreBackend,
        control_points: list[tuple[int, int, int]],
        palette_size: int,
        set_status: Callable[[str], None],
    ) -> bool:
        if path is None:
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
        if path is None:
            return False
        palette_size, control_points = backend.import_palette_json(str(path))
        if not control_points:
            return False
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
        if path is None or len(control_points) < 4:
            set_status("Add at least four control points before exporting a legacy map.")
            return False
        palette = backend.generate_palette(control_points, legacy_palette_size)
        if not palette:
            return False
        backend.export_legacy_map(str(path), palette)
        set_status(f"Exported legacy palette to {path}")
        return True
```

- [ ] **Step 4: Update `favorites_controller.py`**

In `update_palette_previews()`, the guard `if len(control_points) >= 4 and backend.available` becomes just `if len(control_points) >= 4` — `generate_palette` returns `[]` when the backend is absent, which is the same behavior.

```python
        legacy_palette = (
            backend.generate_palette(control_points, legacy_palette_size)
            if len(control_points) >= 4
            else []
        )
```

- [ ] **Step 5: Run the import policy test to confirm `backend.available` is gone from the service layer**

```powershell
rg -rn "backend\.available" ui/src/fractal_studio/application ui/src/fractal_studio/services
```
Expected: no output (or only hits in files that are legitimately doing UI decisions — check each one).

- [ ] **Step 6: Run the full unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add ui/src/fractal_studio/services/export_service.py ui/src/fractal_studio/services/palette_service.py ui/src/fractal_studio/application/controllers/favorites_controller.py
git commit -m "refactor: remove backend.available guards from services and application layers"
```

---

## Task 3: Use `backend.capabilities` in the UI layer for feature gating

**Files:**
- Modify: `ui/src/fractal_studio/ui/sections/panel_state.py`

The UI layer (panel states) may have `backend.available` checks for enabling/disabling UI controls. These should use `backend.capabilities` going forward so the intent is explicit.

- [ ] **Step 1: Find all `backend.available` usages in `ui/`**

```powershell
rg -rn "backend\.available\|backend_available" ui/src/fractal_studio/ui
```

For each hit, replace `backend.available` (or the `backend_available_getter()` lambda result) with the appropriate `backend.capabilities.can_render` / `backend.capabilities.can_generate_palette` etc., whichever matches the context.

For example, in `MainWindowSidebarState.backend_state_message()`, the `backend_available_getter()` result is passed to `settings_service.backend_state_message()` — this is a UI display decision and should use `backend.capabilities.can_render`.

Read each file before editing to get the exact current usage.

- [ ] **Step 2: Run the full unit suite**

```powershell
cd ui && pytest -m unit -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```powershell
git add ui/src/fractal_studio/ui/sections/panel_state.py
git commit -m "refactor: use backend.capabilities for UI feature gating instead of backend.available"
```

---

## Self-Review

**Spec coverage:**
- `BackendCapabilities` frozen dataclass added to `backend.py`: Task 1 ✓
- `CoreBackend.capabilities` property: Task 1 ✓
- `_require()` removed; all methods return safe defaults: Task 1 ✓
- `backend.available` guards removed from `application/` and `services/`: Task 2 ✓
- UI layer uses `backend.capabilities` for feature gating: Task 3 ✓
- `backend.available` survives only for status panel display: maintained ✓

**Placeholder scan:** Task 3 Step 1 instructs reading files before editing — the exact pattern of `backend.available` usage in UI code varies by panel state and cannot be fully specified without reproducing the entire panel_state.py. The rule (replace with appropriate capability flag) is explicit.

**Type consistency:** `BackendCapabilities` defined in Task 1, used as `backend.capabilities` consistently in Tasks 2 and 3. Field names `can_render`, `can_generate_palette`, `can_import_palette`, `can_export_palette` used throughout.
