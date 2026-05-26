# Fractal Studio

Fractal Studio is a modern desktop port of several legacy graphics projects in this repository.

The current direction is:

- **PySide6** for the desktop UI
- **Rust** for the performance-sensitive core
- a shared app that brings together:
  - the legacy **Defense** colormap generator
  - **Mandelbrot** rendering
  - **Julia** rendering

## Current status

The project currently includes:

- a Rust colormap core
- legacy `.map` palette import/export
- modern JSON palette save/load
- a PySide6 six-face colormap editor
- live spline and palette preview

## Near-term plan

1. Build the shared Rust fractal renderer.
2. Feed the live in-app palette into Mandelbrot and Julia rendering.
3. Add viewport interaction and export workflows.

## Development notes

- Internal palettes are higher fidelity than the legacy 256-color format.
- Legacy `.map` export remains supported for compatibility.
- Built artifacts such as wheels should not be committed.
