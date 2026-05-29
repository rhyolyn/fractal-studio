# Export

The Export panel renders the current fractal to a PNG file at a resolution you choose.

---

## Aspect ratio

Before picking a resolution, select an **aspect ratio mode**. This controls the shape of the output image.

| Mode | Description |
|------|-------------|
| **Square** | Equal width and height (default) |
| **Widescreen** | 16:9 ratio |

The aspect ratio mode also affects the viewport's own render proportions and the available preset list.

---

## Resolution presets

The **Export preset** dropdown is populated by the Rust core and depends on the active aspect ratio:

| Preset | Typical resolution |
|--------|-------------------|
| 2K | 2048 × 2048 (square) / 2048 × 1152 (widescreen) |
| 4K | 4096 × 4096 / 4096 × 2304 |
| 8K | 8192 × 8192 / 8192 × 4608 |
| Tiled | Large tiled output |
| Custom | Enter width and height manually |

Selecting **Custom** reveals width and height spin boxes.

---

## Exporting

1. Set the aspect ratio and select a preset (or enter custom dimensions).
2. Click **Export**.
3. A file dialog opens — choose a destination and filename (`.png` extension is added automatically if omitted).
4. The Rust core renders at the target resolution and saves the file. A status message confirms completion.

!!! note "Render time"
    High-resolution exports at high iteration counts can take several seconds. The UI remains responsive during export on systems where the Rust core runs on a background thread; otherwise it may pause briefly.

---

## Tips

- The exported fractal uses exactly the same formula, position, palette, and coloring mode shown in the viewport — there is no separate "render settings" step.
- Export at a higher resolution than your display and downscale in an image editor for a supersampled result.
- The **Tiled** preset is intended for very large prints — it renders the fractal in sections and stitches them together.
