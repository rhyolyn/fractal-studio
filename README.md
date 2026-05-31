# Fractal Studio

A desktop application for interactive fractal exploration and palette authoring, built on a **PySide6/Qt** UI over a **Rust** rendering core.

The app brings together several historically separate tools — Mandelbrot/Julia rendering, a six-face color-cube palette editor, palette import/export, and a favorites gallery — into one integrated workspace. The Rust backend is optional: the full UI launches and persists data without it, which makes pure Python UI development practical without a Rust toolchain.

---

## Panels at a Glance

| Panel | Description |
|-------|-------------|
| **Viewport** | Interactive fractal canvas — pan, zoom, switch formulas |
| **Sidebar** | Formula selector and parameter controls (iterations, scale, Julia constant, Phoenix/Newton params) |
| **Palette** | Six-face color-cube editor with live spline preview |
| **Colormap** | Smooth-escape colormap preview with palette-offset animation |
| **Export** | Render to PNG at preset resolutions (2K / 4K / 8K / Tiled) |
| **Favorites** | Save and restore named viewport snapshots with thumbnails |
| **Backend** | Status panel — reports whether the Rust core is loaded |

---

## Documentation

| Document | Format |
|----------|--------|
| [Architecture page](pages/architecture.html) | Live site (open in browser) |
| [Codex Architectural Analysis](pages/codex-analysis.html) | Live site — independent code review with resolution status |
| [Codex Analysis source](docs/codex-architectural-analysis-2026-05-30.md) | Markdown (GitHub-readable) |

The `pages/` site is the canonical developer reference. Open any `.html` file directly in a browser — no server needed.

---

## Supported Formulas

- **Mandelbrot** — classic z² + c escape-time
- **Julia** — fixed-c variant with configurable constant (cx, cy)
- **Phoenix** — Julia variant with a perturbation term (real, imag)
- **Newton** — Newton's method for z³ − 1, with trap-point coloring
- **Burning Ship**, **Multibrot** (power ≥ 2)

---

## Prerequisites

### Required for UI-only mode

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12 or later | [python.org](https://www.python.org/downloads/) |
| PySide6 | ≥ 6.8 | auto-installed via pip |

### Additional requirements for full rendering

| Tool | Version | Install |
|------|---------|---------|
| Rust toolchain | stable (2021 edition) | [rustup.rs](https://rustup.rs) |
| maturin | ≥ 1.7, < 2.0 | `python -m pip install maturin` |

> **Rust dependencies** (fetched automatically by cargo — no action needed):
> - `pyo3` 0.28.3 — Python/Rust FFI bridge
> - `serde` + `serde_json` 1.x — JSON serialization for palette I/O

---

## Quick Start — UI Only

Use this path when working on the Python UI, tests, or anything that doesn't require the rendered fractal output.

```powershell
# From the fractal-studio/ directory:
python -m venv .venv
.venv\Scripts\activate           # Windows PowerShell

python -m pip install -e ./ui
fractal-studio
```

```bash
# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -e ./ui
fractal-studio
```

The app will open with all panels active. Fractal rendering, palette generation, and PNG export are disabled (the Rust core is absent); the status panel will report this. All other features — favorites, palette editing, settings, theme — work normally.

---

## Full Setup — with Rust Rendering

### 1. Install Rust

```powershell
# Windows: download and run rustup-init.exe from https://rustup.rs
# Then open a new terminal to pick up PATH changes.
rustc --version   # should print e.g. rustc 1.78.0
```

```bash
# macOS / Linux:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
rustc --version
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install maturin

```bash
python -m pip install "maturin>=1.7,<2.0"
```

### 4. Build the Rust core

```bash
cd core
python -m maturin develop --release   # compiles Rust, installs fractal_core into the active venv
cd ..
```

`--release` enables Rust's optimisation passes. The first build takes 30–60 seconds; subsequent incremental builds are much faster.

### 5. Install the Python UI

```bash
python -m pip install -e ./ui
```

### 6. Run

```bash
fractal-studio
```

The status panel should now report the backend as loaded.

---

## Rebuilding After Rust Changes

Rust source lives in `core/src/lib.rs`. After editing it:

```bash
cd core
python -m maturin develop --release
cd ..
fractal-studio
```

Python-only changes take effect immediately (editable install) — no rebuild step required.

---

## Running Tests

Tests are split into two groups by marker:

| Marker | Requires | Default run |
|--------|----------|-------------|
| `unit` | Python only, no Qt | yes |
| `integration` | PySide6 / Qt | no |

```bash
cd ui

pytest                   # unit tests only (green without PySide6)
pytest -m unit           # same, explicit
pytest -m integration    # requires PySide6 in the venv
pytest -m "unit or integration"  # full suite
```

> Test configuration lives in `ui/pyproject.toml` under `[tool.pytest.ini_options]`.

---

## Project Structure

```
fractal-studio/
├── core/                        Rust rendering engine
│   ├── src/lib.rs               PyO3 module exports
│   ├── Cargo.toml               Rust dependencies (pyo3, serde)
│   └── pyproject.toml           maturin build config
│
├── ui/                          Python UI package
│   ├── src/fractal_studio/
│   │   ├── app.py               Entry point
│   │   ├── main_window.py       QMainWindow shell
│   │   ├── main_window_factory.py  Dependency injection root
│   │   ├── state.py             Immutable domain objects
│   │   ├── persistence.py       JSON repositories
│   │   ├── backend.py           Rust bridge + null object
│   │   ├── application/         Controllers / coordinators / workflows
│   │   ├── services/            Cross-cutting services
│   │   └── ui/                  Sections, adapters, widgets, dialogs
│   ├── tests/
│   └── pyproject.toml           Python package + pytest config
│
├── pages/                       Static documentation site (deployed to GitHub Pages via CI)
│   ├── index.html               Site home
│   ├── architecture.html        Developer — architecture design
│   ├── codex-analysis.html      Developer — independent Codex code review
│   └── styles.css               Shared stylesheet
│
└── docs/                        Reference documents (GitHub-readable)
    └── codex-architectural-analysis-2026-05-30.md
```

---

## User Data

Fractal Studio persists data in `~/.fractal_studio/` (created automatically on first run):

| File | Contents |
|------|----------|
| `settings.json` | Theme preference, UI settings |
| `favorites.json` | Saved viewport snapshots (formula params + palette + base64 thumbnail) |

Both files use versioned JSON. The app loads gracefully if either file is missing or malformed, falling back to defaults and displaying a diagnostic in the status bar.

---

## Development Notes

- **Editable install:** `python -m pip install -e ./ui` links the source directory directly. Python changes are live with no reinstall. Only the Rust core requires a `python -m maturin develop` rebuild.

- **Without the Rust core:** The app launches and is fully navigable. UI-layer work (layout, favorites, palette editor, settings) does not require a Rust build. The `CoreBackend` null object returns safe defaults for all rendering calls.

- **Architecture:** The Python UI follows a layered Ports & Adapters architecture with a single-pass composition root. See the [architecture page](pages/architecture.html) for the full design and SOLID analysis.

- **Import policy test:** `tests/test_import_policy.py` enforces that lower layers (`state.py`, `persistence.py`) do not import from application or UI layers. Run it as part of the unit suite.

- **State storage:** All domain state is immutable (`@dataclass(frozen=True)`). Mutating a viewport state means constructing a new `ViewportState` with `dataclasses.replace(...)`.
