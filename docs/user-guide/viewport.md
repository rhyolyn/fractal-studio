# Fractal Viewport

The viewport is the main canvas. It shows the active fractal and updates as you move around or change parameters.

---

## Navigation

| Action | Result |
|--------|--------|
| **Left-click drag** | Pan the view |
| **Scroll wheel up** | Zoom in, toward the cursor position |
| **Scroll wheel down** | Zoom out |

Render calls are debounced. The fractal re-renders shortly after you stop moving, so the UI does not try to compute every tiny twitch of the mouse.

---

## Formula selector

The **Sidebar** controls which formula is active. Choose one from the formula dropdown:

| Formula | Extra parameters |
|---------|------------------|
| **Mandelbrot** | None |
| **Julia** | cx, cy (constant) |
| **Phoenix** | real, imag (perturbation) |
| **Newton** | trap x, trap y |
| **Burning Ship** | None |
| **Multibrot** | power (integer ≥ 2) |

When you switch formulas, the matching parameter controls appear and the fractal re-renders.

---

## Parameter controls

All controls are in the Sidebar panel.

| Control | Description |
|---------|-------------|
| **Max iterations** | Higher values reveal more detail in boundary regions; increases render time |
| **Scale** | Zoom level, independent of the viewport zoom gesture |
| **Power** | Multibrot exponent; only active when Multibrot is selected |
| **Julia cx / cy** | Real and imaginary parts of the Julia constant |
| **Phoenix real / imag** | Phoenix perturbation parameters |
| **Newton trap x / y** | Trap-point position for Newton coloring |
| **Coloring mode** | How escape-time values are mapped to the palette |
| **Palette offset** | Rotates the palette across the fractal; animate it for color-cycling effects |

---

## Coloring modes

| Mode | Effect |
|------|--------|
| `smooth_escape` | Smooth gradient using fractional escape time; eliminates banding |

More modes can be added in the Rust core later.

---

## Julia mode

Julia mode fixes the iteration constant at the cx / cy value instead of using the pixel coordinate. In practical terms, it turns the Mandelbrot-family view into the corresponding Julia set.

- Set cx and cy in the Sidebar to explore different Julia shapes.
- Values near the Mandelbrot boundary tend to produce the most intricate sets.
- Common starting points: `cx = -0.8`, `cy = 0.156`.

---

## Tips

- Deep zooms usually need higher **max iterations**. Start at 256 and increase it if the boundary turns into a suspiciously boring edge.
- **Palette offset** can make the same fractal look completely different without changing the underlying shape.
- Use **Save favorite** in the Favorites panel before zooming deep into an area you want to revisit.
