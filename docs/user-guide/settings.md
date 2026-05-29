# Settings & Themes

## Opening settings

Open the settings dialog from the application menu or the settings button in the toolbar.

---

## Theme

Fractal Studio ships with three built-in themes:

| Theme | Description |
|-------|-------------|
| **Light** | Default — white background, dark text |
| **Dark** | Dark background, light text; easier on the eyes in dim environments |
| **Sepia** | Warm off-white background |

Theme changes apply immediately as you select them — you can preview each option before confirming.

Clicking **OK** saves the theme to `~/.fractal_studio/settings.json`. The saved theme is restored on next launch.

Clicking **Cancel** discards the change and reverts to the theme active when you opened the dialog.

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

If this file is missing or unreadable, the app falls back to the **Light** theme and displays a diagnostic in the status bar.

---

## Backend status

The **Backend** panel (bottom-right) shows whether the Rust rendering core loaded:

| Status | Meaning |
|--------|---------|
| Loaded | `fractal_core` is compiled and available — full rendering enabled |
| Not available | Running in UI-only mode — viewport shows a placeholder |

If you have installed the Rust core but the status still shows "Not available", verify that:

1. You activated the virtual environment that contains the built `fractal_core` module.
2. You ran `maturin develop --release` from the `core/` directory with the same venv active.
3. There are no import errors — run `python -c "import fractal_core"` in the venv to check.
