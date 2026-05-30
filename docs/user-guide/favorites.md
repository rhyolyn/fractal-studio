# Favorites

Save snapshots of views worth keeping. Each favorite captures the formula, position, zoom level, parameters, palette, and a thumbnail.

---

## Saving a favorite

1. Navigate the viewport to the position and zoom you want to keep.
2. Make sure the palette looks as you want it.
3. Click **Save favorite** in the Favorites panel.

A thumbnail is captured from the live viewport and the favorite is added to the gallery immediately. The name is generated from the active formula and the current date/time, for example `Julia 2026-05-28 14:32`.

Favorites are written to `~/.fractal_studio/favorites.json` immediately, so they survive closing and reopening the app. Which is generally the point of saving things.

---

## Restoring a favorite

| Action | Result |
|--------|--------|
| **Single click** | Selects the row and highlights it |
| **Double-click** | Restores the favorite: formula, position, parameters, and palette |

Restoring a favorite replaces the current viewport state completely. If the current view is worth keeping, save it before loading another one.

---

## Deleting a favorite

1. Single-click to select the row.
2. Click **Delete** or the delete button in the panel.

The favorite is removed from the gallery and from `favorites.json`.

---

## What is saved

| Field | Saved |
|-------|-------|
| Formula | Yes |
| Center position (x, y) | Yes |
| Zoom / scale | Yes |
| Max iterations | Yes |
| Formula-specific params (Julia cx/cy, Phoenix, Newton) | Yes |
| Coloring mode | Yes |
| Palette offset | Yes |
| Palette (control points + rendered colors) | Yes |
| Aspect ratio mode | Yes |
| Thumbnail (base64 PNG) | Yes |
| Power (Multibrot) | Yes |

---

## Tips

- Save a favorite before exploring a deep zoom. Navigation can be annoyingly hard to reproduce precisely.
- Favorites load the full palette, so they also work as palette bookmarks.
- The gallery scrolls vertically. There is no fixed limit beyond disk space.
