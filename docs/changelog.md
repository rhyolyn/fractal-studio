# Changelog

Notable changes to Fractal Studio, mostly so future me does not have to reconstruct history from commit messages and vague memories.

---

## Unreleased

### Added

- Architectural design document with SOLID analysis and Mermaid diagrams
- Developer README with full setup instructions for UI-only and Rust modes

### Changed

- `ViewportState` formula-specific parameters decomposed into typed sub-structs (`JuliaParams`, `PhoenixParams`, `NewtonParams`, `StandardParams`), eliminating invalid parameter combinations
- `MainWindowController` split into `ExportController` and `SettingsController`
- Adapter files consolidated into `ui/sections/adapters/` subdirectory
- Panel state machines now receive collaborators via constructor injection
- `MainWindowSectionsState.validate()` added, catching missing collaborator wiring at startup rather than silently at runtime

---

## Earlier work

Fractal Studio grew out of several older graphics experiments in this repository:

- Rust colormap core
- Legacy `.map` palette import/export
- Modern JSON palette save/load
- PySide6 six-face colormap editor
- Live spline and palette preview
- Mandelbrot and Julia rendering via Rust core
- Favorites system with thumbnail gallery
- Export workflow (2K / 4K / 8K / Tiled)
- Light, dark, and sepia themes
