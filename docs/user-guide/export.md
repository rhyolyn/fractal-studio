# Export

The Export panel renders the current fractal to a PNG file at the size you choose.

---

## Aspect ratio

Before choosing a resolution, select an **aspect ratio mode**. This controls the shape of the output image.

| Mode | Description |
|------|-------------|
| **Square** | Equal width and height (default) |
| **Widescreen** | 16:9 ratio |

The aspect ratio also affects the viewport proportions and which presets are available.

---

## Resolution presets

The **Export preset** dropdown comes from the Rust core and depends on the active aspect ratio:

| Preset | Typical resolution |
|--------|--------------------|
| 2K | 2048 × 2048 (square) / 2048 × 1152 (widescreen) |
| 4K | 4096 × 4096 / 4096 × 2304 |
| 8K | 8192 × 8192 / 8192 × 4608 |
| Tiled | Large tiled output |
| Custom | Enter width and height manually |

Selecting **Custom** reveals width and height spin boxes.

---

## Exporting

1. Set the aspect ratio and select a preset, or enter custom dimensions.
2. Click **Export**.
3. A file dialog opens. Choose a destination and filename. The `.png` extension is added automatically if omitted.
4. The Rust core renders at the target resolution and saves the file. A status message confirms completion.

!!! note "Render time"
    High-resolution exports with high iteration counts can take several seconds. If the Rust core is running on a background thread, the UI stays responsive. If not, it may pause briefly and pretend this was all part of the plan.

---

## Tips

- The export uses the same formula, position, palette, and coloring mode shown in the viewport. There is no secret second set of render settings.
- Export larger than your display and downscale in an image editor if you want a cleaner final image.
- The **Tiled** preset is for very large prints. It renders the fractal in sections and stitches them together.
