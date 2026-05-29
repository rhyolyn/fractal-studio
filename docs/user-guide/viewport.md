# Fractal Viewport

The viewport is the main canvas. It renders the active fractal in real time as you navigate or change parameters.

---

## Navigation

| Action | Result |
|--------|--------|
| **Left-click drag** | Pan the view |
| **Scroll wheel up** | Zoom in (towards cursor position) |
| **Scroll wheel down** | Zoom out |

Render calls are debounced — the fractal re-renders a short moment after you stop moving, so intermediate frames do not stall the UI.

---

## Formula selector

The **Sidebar** panel on the left controls which formula is active. Select from the formula dropdown:

| Formula | Extra parameters |
|---------|-----------------|
| **Mandelbrot** | None |
| **Julia** | cx, cy (constant) |
| **Phoenix** | real, imag (perturbation) |
| **Newton** | trap x, trap y |
| **Burning Ship** | None |
| **Multibrot** | power (integer ≥ 2) |

When you switch formulas, the relevant parameter controls appear and the fractal re-renders immediately.

---

## Parameter controls

All controls are in the Sidebar panel.

| Control | Description |
|---------|-------------|
| **Max iterations** | Higher values reveal more detail in boundary regions; increases render time |
| **Scale** | Zoom level (independent of the viewport zoom gesture) |
| **Power** | Multibrot exponent — only active when Multibrot is selected |
| **Julia cx / cy** | Real and imaginary parts of the Julia constant |
| **Phoenix real / imag** | Phoenix perturbation parameters |
| **Newton trap x / y** | Trap-point position for Newton colouring |
| **Coloring mode** | How escape-time values are mapped to the palette (e.g. smooth escape) |
| **Palette offset** | Rotates the palette across the fractal — animate for colour-cycling effects |

---

## Coloring modes

| Mode | Effect |
|------|--------|
| `smooth_escape` | Smooth gradient using fractional escape time — eliminates banding |

Additional modes may be added by the Rust core.

---

## Julia mode

Enabling **Julia** on any formula fixes the iteration constant at the cx / cy value instead of using the pixel coordinate. This transforms the Mandelbrot-family view into the corresponding Julia set.

- Set cx and cy in the Sidebar to explore different Julia shapes.
- Values near the Mandelbrot boundary tend to produce the most intricate sets.
- Common starting points: cx = −0.8, cy = 0.156.

---

## Tips

- Deep zooms require higher **max iterations** to avoid the boundary looking flat. Start at 256 and increase if you see a hard edge where the fractal should still be detailed.
- **Palette offset** combined with **coloring mode** can dramatically change the appearance of the same fractal without re-rendering.
- Use **Save favourite** (in the Favourites panel) before zooming deep into an area you want to revisit.
