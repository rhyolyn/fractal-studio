# Getting Started

There are two ways to run Fractal Studio: UI-only if you are working on the interface or palettes, and full mode if you want the Rust renderer doing real work. Both start with a virtual environment.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12 or later | [python.org](https://www.python.org/downloads/) |
| PySide6 | ≥ 6.8 | Installed automatically via pip |
| Rust toolchain | stable | Only needed for fractal rendering |
| maturin | ≥ 1.7, < 2.0 | Only needed for fractal rendering |

---

## Installation

**UI-only** is the quick path and is enough for palette editing, favorites, and settings work. **Full** adds the Rust rendering core so the viewport and export features can render fractals.

=== "UI-only"

    The app launches without the Rust backend. Fractal rendering and PNG export are disabled, but the rest of the UI still works.

    ```powershell
    # Windows — from the fractal-studio/ directory
    python -m venv .venv
    .venv\Scripts\activate
    pip install -e ./ui
    fractal-studio
    ```

    ```bash
    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ./ui
    fractal-studio
    ```

=== "Full · with Rust"

    **Step 1 — Install Rust**

    ```bash
    # macOS / Linux
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    source "$HOME/.cargo/env"
    ```

    On Windows, download and run `rustup-init.exe` from [rustup.rs](https://rustup.rs), then open a new terminal so the PATH update takes effect.

    **Step 2 — Create a virtual environment**

    ```powershell
    python -m venv .venv
    .venv\Scripts\activate       # Windows
    ```

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate    # macOS / Linux
    ```

    **Step 3 — Build the Rust core**

    ```bash
    pip install "maturin>=1.7,<2.0"
    cd core
    maturin develop --release    # first build takes ~30–60 s
    cd ..
    ```

    **Step 4 — Install and run**

    ```bash
    pip install -e ./ui
    fractal-studio
    ```

---

## Verifying the install

When the app opens, check the **Backend** panel in the bottom-right corner. It tells you whether the Rust core loaded:

- **Loaded** — rendering is active; all panels are enabled.
- **Not available** — UI-only mode; the viewport shows a placeholder and export is disabled. Annoying if unexpected, useful if intentional.

---

## Running tests

```bash
cd ui
pytest                 # unit tests only, no PySide6 required
pytest -m unit         # same, explicit
pytest -m integration  # requires PySide6 in the venv
```

---

## Stored data

Fractal Studio writes two files to `~/.fractal_studio/` on first run:

| File | Contents |
|------|----------|
| `settings.json` | Theme preference |
| `favorites.json` | Saved viewport snapshots |

Both files are versioned JSON. If either file is missing or unreadable, the app falls back to defaults and puts a diagnostic message in the status bar.

---

## Updating after code changes

**Python changes** take effect immediately; no reinstall needed because the UI is installed in editable mode.

**Rust changes** require a rebuild:

```bash
cd core
maturin develop --release
```
