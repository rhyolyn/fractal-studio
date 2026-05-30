# UI Polish — Design Spec
**Date:** 2026-05-29
**Scope:** Spec 1 of 2. Spec 2 (3D Cube Mode) is a separate document.

---

## Goal

Make the app look more professional: better visual hierarchy between panels, less crowded labels and spacing, and move the Backend Profile to a less prominent location. No changes to column proportions, the colormap editor widget, or any business logic.

---

## What Changes

| Area | Change |
|---|---|
| All panels | Replace `QGroupBox` with new `SectionPanel` widget |
| Theme | Five new `ThemeSpec` tokens |
| Viewport | `ViewportWell` container draws checkerboard dead space; aspect ratio combo in panel header |
| Right sidebar | Collapsible sections; Export and Favorites collapse state persists |
| Backend Profile | Removed from sidebar; data moved to Settings "Environment" tab |
| Favorites | 48px thumbnails; accent left-border on selected row; clean timestamps |
| Export | Primary-styled Export button; IO buttons remain ghost |

## What Does Not Change

- Column proportions (workspace 1:1 viewport:middle, sidebar ~300px)
- `ColorCubeEditor` widget — untouched
- `PalettePreviewWidget` — untouched
- All signals, controllers, coordinators, business logic

---

## Future Task (Spec 2)

The colormap panel will gain a **Curves / 3D Cube** mode toggle as a separate implementation. The `SectionPanel` header's `set_header_widget()` slot is designed to accommodate this toggle without changes.

---

## New Widgets

### `SectionPanel` — `ui/widgets/section_panel.py`

Replaces `QGroupBox` as the standard panel container. Has one clear job: render a styled header row and a collapsible body.

**Structure:**
```
SectionPanel(QWidget)
├── _header (QWidget)           — always visible, full-width clickable when collapsible
│   ├── _title_label (QLabel)   — uppercase, letter-spaced, section_heading colour
│   ├── _tag_label (QLabel)     — optional, right-aligned (e.g. "5 points", "4 saved")
│   ├── _header_widget (QWidget)— optional, right-aligned arbitrary widget (e.g. aspect combo)
│   └── _toggle_btn (QLabel)    — optional ▾/▸, shown only when collapsible=True
└── _body_container (QWidget)   — shown/hidden on toggle; caller populates via body_layout()
```

**Constructor:**
```python
SectionPanel(
    title: str,
    *,
    collapsible: bool = False,
    collapsed: bool = False,
    parent: QWidget | None = None,
)
```

**Public API:**
```python
def body_layout(self) -> QVBoxLayout: ...       # add children here
def set_tag(self, text: str) -> None: ...       # update optional tag label
def set_header_widget(self, w: QWidget) -> None: ...  # right-aligned header slot
def set_collapsed(self, collapsed: bool) -> None: ...
def is_collapsed(self) -> bool: ...
def set_theme(self, spec: ThemeSpec) -> None: ... # called by ThemeController on theme switch

collapse_changed: Signal(bool)                  # emitted on user toggle
```

**QSS targeting:** `_title_label` carries `objectName("sectionTitle")` so the QSS rule `QLabel#sectionTitle` targets it precisely without matching other labels in the app.

**Behaviour:**
- When `collapsible=True`, clicking anywhere on `_header` toggles collapse.
- Collapse hides `_body_container` instantly (no animation in v1).
- Toggle arrow updates: `▾` expanded, `▸` collapsed.
- Non-collapsible panels omit the toggle button entirely.

**Styling (via QSS in `theme.py`):**
- Title: `font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: {theme.section_heading}`
- Header background: `{theme.panel_surface}`
- Header padding: 11px vertical, 14px horizontal
- Body padding: 14px all sides, 10px spacing between children
- Bottom border on header: `1px solid {theme.border}`

**Tests:** `test_section_panel.py` (unit, no Qt required beyond basic widget instantiation — mark `integration`).

---

### `ViewportWell` — `ui/widgets/viewport_well.py`

Wraps `FractalViewportWidget` and draws the checkerboard dead-space background. Has one clear job: provide a themed background and centre the canvas while respecting its aspect ratio.

**Structure:**
```
ViewportWell(QWidget)
└── FractalViewportWidget   — centred, aspect ratio maintained via hasHeightForWidth
```

**Behaviour:**
- `paintEvent`: draws a 45°-rotated (diagonal) checkerboard across the full widget area, approximating the Design's `repeating-conic-gradient`. Implementation: fill background with `checker_a`, then draw `checker_b` diamonds at every 22px grid intersection using `QPainter.drawPolygon()` with a rotated square path. The two colours are intentionally very close (subtle pattern).
- Layout: `QVBoxLayout` containing `QHBoxLayout` with the viewport widget; no stretches added — Qt's `hasHeightForWidth` propagation handles sizing naturally.
- When the viewport widget is resized (e.g. window resize or aspect ratio change), `updateGeometry()` is called and the checkerboard repaints.
- Theme colours read at paint time from the `ThemeSpec` passed at construction; updated via `set_theme(spec)` called by `ThemeController.refresh_dynamic_widgets`.

**Constructor:**
```python
ViewportWell(viewport: FractalViewportWidget, theme: ThemeSpec, parent=None)
```

**`ThemeController.refresh_dynamic_widgets` update:**
Add `ViewportWell` to the list of widgets that receive `set_theme()` on theme switch.

---

## Theme Changes — `theme.py`

Five new fields on `ThemeSpec` (frozen dataclass):

| Field | Dark | Light | Sepia | Purpose |
|---|---|---|---|---|
| `section_heading` | `#6b7080` | `#8b91a2` | `#9a8b7a` | Panel title label colour |
| `panel_surface` | `#161821` | `#ffffff` | `#f4ebd9` | Panel header/body card background |
| `primary_button` | `#2fd4b8` | `#1f9e89` | `#b3673b` | Export button fill |
| `checker_a` | `#0a0b0e` | `#e3e6ec` | `#ddd0b5` | Checkerboard tile colour A |
| `checker_b` | `#101116` | `#d8dce4` | `#d2c4a7` | Checkerboard tile colour B |

New QSS rules added to `build_stylesheet()`:
- `SectionPanel` title label selector
- `SectionPanel` header background
- `QPushButton#primaryButton` — filled, `primary_button` background, contrasting text
- `FavoriteThumbnailRow[selected="true"]` — `border-left: 3px solid {theme.accent}`

---

## Viewport Panel

**`build_viewport_panel()` in `sections.py`:**
- Returns `SectionPanel("Fractal Viewport", collapsible=False)`
- Aspect ratio combo placed in header via `panel.set_header_widget(aspect_row)`
- Body contains only `ViewportWell(viewport, theme)` — no stretches, no hint label padding hacks
- Hint label ("Scroll zoom · Drag pan · Double-click recenter") becomes a child `QLabel` of `ViewportWell` positioned as an overlay: geometry set in `ViewportWell.resizeEvent()` to bottom-left, semi-transparent background via QSS. This matches the Design's `viewport-hud` pattern and avoids layout interference with the aspect-ratio-constrained canvas.

---

## Right Sidebar

**`build_sidebar()` in `sections.py`:**

```
sidebar (QVBoxLayout)
├── SectionPanel("Fractal Parameters", collapsible=True, collapsed=False)  ← expanded
├── SectionPanel("Export", collapsible=True, collapsed=True)               ← collapsed
│   header_widget: [preset combo] [Export button]                          ← always visible
└── SectionPanel("Favorites", collapsible=True, collapsed=False)           ← expanded
```

Backend Profile panel is **removed entirely** from this list.

**Export panel collapsed-header design:**
When collapsed, the Export section shows its full action row (preset dropdown + primary Export button) inline in the header. The body contains only additional options (custom resolution trigger). This means you can export without ever expanding the section.

**Collapse state persistence:**

- `SettingsRepository` gains `load_sidebar_state() -> dict[str, bool]` and `save_sidebar_state(state: dict[str, bool]) -> None`
- Keys: `"export"`, `"favorites"` (Parameters is always expanded — not persisted)
- Loaded in `WindowStartupCoordinator.bootstrap()`, passed to `build_sidebar()`
- Each `SectionPanel.collapse_changed` signal connects to a slot in `MainWindowSectionsState` that calls `save_sidebar_state()`

---

## Backend Profile → Settings Dialog

**`AppearanceSettingsDialog` gains an Environment section using the existing sidebar/stack navigation pattern (not QTabWidget):**

```
AppearanceSettingsDialog (custom sidebar nav)
├── Nav "Appearance"  — existing theme picker (unchanged)
└── Nav "Environment" — new, read-only backend profile display
```

Environment tab content: labelled read-only rows (monospace value column) for:
- Extension (e.g. "Rust · loaded" or "Python fallback")
- Coloring model
- Render strategy
- Internal palette size
- Legacy palette size

Data passed at dialog construction via a `BackendProfile | None` argument (already available at the call site in `MainWindow._open_settings`). No live updates — dialog is modal and reads snapshot at open time.

---

## Favorites Panel

- `FavoriteThumbnailRow`: thumbnail size changes from `48×36` to `48×48` (square, `KeepAspectRatioByExpanding`)
- Selected state: already implemented correctly in `FavoriteRowStylePresenter` (`border-left: 4px solid selected_border` + `selection_bg` fill) — no change needed
- Timestamps: not displayed in the current UI (`FavoriteThumbnailRow` shows `fav["name"]` only); no change needed

---

## Architecture Notes

- `SectionPanel` and `ViewportWell` each have one responsibility and communicate through narrow interfaces. Neither knows about sections, the main window, or business logic.
- Theme-sensitive widgets (`ViewportWell`, `SectionPanel`) receive theme via constructor and `set_theme()` — they do not reach into global state to read it.
- Collapse state persistence goes through `SettingsRepository` (already the abstraction boundary for settings I/O) — no new I/O path needed.
- `sections.py` is the only file that wires things together. The new panel types are drop-in replacements; the wiring logic (signal connections, coordinator calls) is unchanged.
- `build_backend_panel()` in `sections.py` is deleted; callers updated.
