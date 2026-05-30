# Settings & Themes

Choose a theme, see where preferences are stored, and check whether the Rust rendering core loaded.

---

## Opening settings

Open settings from the application menu or the settings button in the toolbar.

---

## Theme

Fractal Studio ships with three built-in themes:

| Theme | Description |
|-------|-------------|
| **Light** | Default: white background, dark text |
| **Dark** | Dark background, light text; easier on the eyes when the room is doing its cave impression |
| **Sepia** | Warm off-white background |

Theme changes apply immediately as you select them, so you can preview each option before confirming.

- Clicking **OK** saves the theme to `~/.fractal_studio/settings.json`. The saved theme is restored on next launch.
- Clicking **Cancel** discards the change and reverts to the theme active when you opened the dialog.

---

## Stored settings

Settings are written to `~/.fractal_studio/settings.json`:

```json
{
  "version": 1,
  "data": {
    "theme": "dark"
  }
}
```

If this file is missing or unreadable, the app falls back to the **Light** theme and shows a diagnostic in the status bar.

---

## Backend status

The **Backend** panel in the bottom-right corner shows whether the Rust rendering core loaded:

| Status | Meaning |
|--------|---------|
| Loaded | `fractal_core` is compiled and available; full rendering is enabled |
| Not available | Running in UI-only mode; the viewport shows a placeholder |

If you installed the Rust core but the status still says "Not available", check the boring-but-usually-correct things:

1. You activated the virtual environment that contains the built `fractal_core` module.
2. You ran `maturin develop --release` from the `core/` directory with the same venv active.
3. There are no import errors. Run `python -c "import fractal_core"` in the venv to check.
