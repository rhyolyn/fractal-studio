# Palette Editor

Build smooth color gradients by placing control points on a virtual color cube. The resulting palette is applied to the fractal as you work.

---

## How it works

The editor shows six faces of an RGB color cube. Each face is a 2D slice through color space:

| Face | Axes |
|------|------|
| Front | Red / Green (Blue = 255) |
| Back | Red / Green (Blue = 0) |
| Top | Red / Blue (Green = 255) |
| Bottom | Red / Blue (Green = 0) |
| Right | Green / Blue (Red = 255) |
| Left | Green / Blue (Red = 0) |

Click any face to place a **control point**. The Rust core builds a smooth spline through the points and samples it into the working palette, 2048 colors by default.

---

## Placing and moving control points

| Action | Result |
|--------|--------|
| **Left-click on a face** | Place a new control point at that color |
| **Left-click drag on a point** | Move the control point |

The palette preview updates while you drag. The fractal viewport re-renders after you release, because making it rerender for every tiny movement would be heroic in the least useful way.

---

## Preview strips

Two preview strips are shown below the cube editor:

| Strip | Description |
|-------|-------------|
| **Palette preview** | Full 2048-color gradient as rendered by the Rust core |
| **Legacy preview** | 256-color downsampled version used for `.map` export |

Both update live as you edit control points.

---

## Summary labels

Above the preview strips:

- **Control points** — count and positions of active control points
- **Palette summary** — current palette size and coloring method

---

## Saving and loading palettes

### Save to JSON

Click **Save palette** to write the current control points and palette to a JSON file. The file stores the full 2048-color palette and the control point list, so it can be loaded back without quietly losing detail.

### Load from JSON

Click **Load palette** to open a JSON palette file. The editor replaces the current control points and re-renders.

### Export legacy .map

Click **Export .map** to write a 256-color `.map` file for legacy software. This is a lossy export; the old format simply cannot hold the full internal palette.

---

## Tips

- Three or four control points spread across different faces usually produce better gradients than a pile of points all sulking in one corner.
- The spline wraps, so the color after the last control point transitions back to the first. That makes **palette offset** useful for seamless color cycling.
- Load a palette before saving a favorite if you want the favorite to restore a specific color scheme.
