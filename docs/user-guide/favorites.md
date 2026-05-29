# Favourites

The Favourites panel lets you save named snapshots of the current viewport state and restore them later. Each favourite captures the formula, position, zoom level, all parameters, and the active palette.

---

## Saving a favourite

1. Navigate the viewport to the position and zoom you want to keep.
2. Make sure the palette looks as you want it.
3. Click **Save favourite** in the Favourites panel.

A thumbnail is captured from the live viewport and the favourite is added to the gallery immediately. The name is generated automatically from the active formula and the current date/time (e.g. `Julia 2026-05-28 14:32`).

Favourites are written to `~/.fractal_studio/favorites.json` immediately — they survive closing and reopening the app.

---

## Restoring a favourite

| Action | Result |
|--------|--------|
| **Single click** | Selects the row (highlights it) |
| **Double-click** | Restores the favourite — loads formula, position, parameters, and palette into the viewport |

Restoring a favourite replaces the current viewport state completely. If you want to keep your current state first, save it as a favourite before restoring another.

---

## Deleting a favourite

1. Single-click to select the row.
2. Click **Delete** (or the delete button in the panel).

The favourite is removed from the gallery and from `favorites.json`.

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
| Palette (control points + rendered colours) | Yes |
| Aspect ratio mode | Yes |
| Thumbnail (base64 PNG) | Yes |
| Power (Multibrot) | Yes |

---

## Tips

- Save a favourite before exploring a deep zoom — navigation can be hard to reproduce precisely.
- Favourites load the full palette, so you can use them as palette bookmarks even if you navigate away from the stored position.
- The gallery scrolls vertically; there is no limit on the number of saved favourites beyond disk space.
