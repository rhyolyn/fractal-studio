# Fractal Studio

**Fractal Studio** is a desktop application for exploring fractals and authoring palettes. It combines an interactive fractal viewport, a six-face colour-cube palette editor, and a favorites system for saving and restoring viewport states — all in one window.

---

## What you can do

<div class="grid cards" markdown>

- **Explore fractals**

    Pan and zoom the Mandelbrot set, Julia sets, Phoenix, Newton, and more. Switch formulas and coloring modes in real time.

- **Design palettes**

    Build smooth colour gradients by placing control points on a 3D colour cube. See a live preview of the resulting palette rendered onto the fractal.

- **Save favourites**

    Capture any viewport state — formula, position, palette — as a named favourite with a thumbnail. Restore it with a double-click.

- **Export high-res images**

    Render to PNG at 2K, 4K, 8K, or a custom resolution. Choose square or widescreen aspect ratios.

</div>

---

## Application layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Fractal Studio                                                   │
├──────────┬──────────────────────────────────┬───────────────────┤
│          │                                  │  Palette Editor   │
│ Sidebar  │      Fractal Viewport            │  (colour cube)    │
│ (params) │                                  ├───────────────────┤
│          │                                  │  Colormap Preview │
├──────────┤                                  ├───────────────────┤
│ Favourites gallery                          │  Export           │
├─────────────────────────────────────────────┴───────────────────┤
│  Status bar                                                       │
└─────────────────────────────────────────────────────────────────┘
```

| Panel | Purpose |
|-------|---------|
| **Viewport** | Main fractal canvas — pan, zoom, render |
| **Sidebar** | Formula and parameter controls |
| **Palette Editor** | Six-face colour-cube editor with live preview |
| **Colormap** | Smooth-escape preview and palette offset |
| **Export** | Resolution presets and PNG output |
| **Favourites** | Saved viewport snapshots |
| **Backend status** | Reports whether the Rust rendering core is loaded |

---

## Supported formulas

| Formula | Description |
|---------|-------------|
| Mandelbrot | Classic z² + c escape-time set |
| Julia | Fixed-c variant; set the constant with cx / cy sliders |
| Phoenix | Julia variant with a perturbation term (real, imag) |
| Newton | Newton's method on z³ − 1 with trap-point colouring |
| Burning Ship | Absolute-value variant of Mandelbrot |
| Multibrot | Generalised Mandelbrot with configurable power (≥ 2) |

---

[Get started →](getting-started.md){ .md-button .md-button--primary }
