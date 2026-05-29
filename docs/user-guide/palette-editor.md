# Palette Editor

The palette editor lets you design smooth colour gradients by placing control points on a virtual colour cube. The resulting palette is applied to the fractal in real time.

---

## How it works

The editor shows six faces of an RGB colour cube. Each face represents a 2D slice through colour space:

| Face | Axes |
|------|------|
| Front | Red / Green (Blue = 255) |
| Back | Red / Green (Blue = 0) |
| Top | Red / Blue (Green = 255) |
| Bottom | Red / Blue (Green = 0) |
| Right | Green / Blue (Red = 255) |
| Left | Green / Blue (Red = 0) |

Click on any face to place a **control point**. The Rust core generates a smooth spline through all control points and samples it into the working palette (2048 colours by default).

---

## Placing and moving control points

| Action | Result |
|--------|--------|
| **Left-click on a face** | Place a new control point at that colour |
| **Left-click drag on a point** | Move the control point |

The palette preview updates immediately as you drag. The fractal viewport re-renders after you release.

---

## Preview strips

Two preview strips are shown below the cube editor:

| Strip | Description |
|-------|-------------|
| **Palette preview** | Full 2048-colour gradient as rendered by the Rust core |
| **Legacy preview** | 256-colour downsampled version (used for `.map` export) |

Both update live as you edit control points.

---

## Summary labels

Above the preview strips:

- **Control points** — count and positions of active control points
- **Palette summary** — current palette size and coloring method

---

## Saving and loading palettes

### Save to JSON

Click **Save palette** to write the current control points and palette to a JSON file. The file stores the full 2048-colour palette and the control point list, so it can be loaded back at full fidelity.

### Load from JSON

Click **Load palette** to open a JSON palette file. The editor replaces the current control points and re-renders.

### Export legacy .map

Click **Export .map** to write a 256-colour `.map` file compatible with legacy software. This is a lossy export — the 256-colour limit cannot represent the full internal palette resolution.

---

## Tips

- Three or four control points spread across different faces typically produce more interesting gradients than many points clustered together.
- The spline wraps — the colour after the last control point transitions back to the first, making seamless palette-cycle animations with **palette offset**.
- Load a palette before saving a favourite if you want the favourite to restore a specific colour scheme.
