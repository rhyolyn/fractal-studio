# Fractal Studio

**Fractal Studio** is a desktop app for playing with fractals and palettes without losing the thread. The viewport, parameters, color-cube editor, exports, and saved favorites all live in one window.

---

## What you can do

<div class="grid cards" markdown>

- **Explore fractals**

    Pan and zoom through Mandelbrot, Julia, Phoenix, Newton, and a few other sets. Switch formulas when you want a different kind of weird.

- **Design palettes**

    Build smooth gradients by placing control points on a 3D color cube. The palette preview updates while you work, which is much nicer than guessing.

- **Save favorites**

    Save a view when you find something worth keeping: formula, position, palette, and thumbnail. Double-click later to get back there.

- **Export high-res images**

    Render PNG files at 2K, 4K, 8K, or a custom size. Use square or widescreen, depending on what the fractal seems to be demanding today.

</div>

---

## Application layout

The viewport stays in the middle, with parameters and palette tools close by. Change a control, and the render you are already looking at updates.

```
┌─────────────────────────────────────────────────────────────────┐
│  Fractal Studio                                                   │
├──────────┬──────────────────────────────────┬───────────────────┤
│          │                                  │  Palette Editor   │
│ Sidebar  │      Fractal Viewport            │  (color cube)     │
│ (params) │                                  ├───────────────────┤
│          │                                  │  Colormap Preview │
├──────────┤                                  ├───────────────────┤
│ Favorites gallery                           │  Export           │
├─────────────────────────────────────────────┴───────────────────┤
│  Status bar                                                       │
└─────────────────────────────────────────────────────────────────┘
```

| Panel | Purpose |
|-------|---------|
| **Viewport** | Main fractal canvas: pan, zoom, render |
| **Sidebar** | Formula and parameter controls |
| **Palette Editor** | Six-face color-cube editor with live preview |
| **Colormap** | Smooth-escape preview and palette offset |
| **Export** | Resolution presets and PNG output |
| **Favorites** | Saved viewport snapshots |
| **Backend status** | Reports whether the Rust rendering core is loaded |

---

## Supported formulas

| Formula | Description |
|---------|-------------|
| Mandelbrot | Classic z² + c escape-time set |
| Julia | Fixed-c variant; set the constant with cx / cy sliders |
| Phoenix | Julia variant with a perturbation term (real, imag) |
| Newton | Newton's method on z³ − 1 with trap-point coloring |
| Burning Ship | Absolute-value variant of Mandelbrot |
| Multibrot | Generalized Mandelbrot with configurable power (≥ 2) |

---

UI-only mode runs without Rust and is enough for palette and UI work. Add the rendering core when you want actual fractals instead of polite placeholders.

[Get started →](getting-started.md){ .md-button .md-button--primary }
