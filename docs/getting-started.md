# Getting Started

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12 or later | [python.org](https://www.python.org/downloads/) |
| PySide6 | ≥ 6.8 | Installed automatically via pip |
| Rust toolchain | stable | Only needed for fractal rendering |
| maturin | ≥ 1.7, < 2.0 | Only needed for fractal rendering |

---

## Installation

There are two modes. **UI-only** is faster to set up and sufficient for palette editing, favourites, and settings work. **Full** adds the Rust rendering core for fractal render output.

=== "UI-only (no Rust required)"

    The app launches without the Rust backend. Fractal rendering and PNG export are disabled; all other panels work normally.

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

=== "Full (with Rust rendering)"

    **Step 1 — Install Rust**

    ```bash
    # macOS / Linux
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    source "$HOME/.cargo/env"
    ```

    On Windows, download and run `rustup-init.exe` from [rustup.rs](https://rustup.rs), then open a new terminal.

    **Step 2 — Create a virtual environment**

    ```powershell
    python -m venv .venv
    .venv\Scripts\activate       # Windows
    ```
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate    # macOS / Linux
    ```

    **Step 3 — Install maturin and build the Rust core**

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

When the app opens, the **Backend** panel in the bottom-right corner reports whether the Rust core loaded:

- **Loaded** — rendering is active; all panels are enabled.
- **Not available** — UI-only mode; the viewport shows a placeholder and export is disabled.

---

## Running tests

```bash
cd ui
pytest           # unit tests only — no PySide6 required
pytest -m unit   # same, explicit
pytest -m integration  # requires PySide6 in the venv
```

---

## Stored data

Fractal Studio writes two files to `~/.fractal_studio/` on first run:

| File | Contents |
|------|----------|
| `settings.json` | Theme preference |
| `favorites.json` | Saved viewport snapshots |

Both files are versioned JSON. If either is missing or corrupt the app falls back to defaults and shows a diagnostic message in the status bar.

---

## Updating after code changes

**Python changes** take effect immediately — no reinstall needed (editable install).

**Rust changes** require a rebuild:

```bash
cd core
maturin develop --release
```
