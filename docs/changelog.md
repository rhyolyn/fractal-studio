# Changelog

Notable changes to Fractal Studio, mostly so future me does not have to reconstruct history from commit messages and vague memories.

---

## Unreleased

### Added

- Live documentation site (`pages/`) with user guide, changelog, and developer architecture pages
- Independent Codex architectural review with prioritised findings and resolution status
- `BackendCapabilities` frozen dataclass — explicit capability flags replace scattered `backend.available` checks
- Async rendering — `RenderWorker` runs Rust renders on a background `QThread`; `RenderScheduler` debounces requests and drops stale results via a generation counter; the UI stays fully responsive during pan, zoom, and parameter changes
- Async export — `ExportRunner` handles PNG export on a background thread; the window remains interactive during large 4K / 8K renders
- Startup smoke tests catch factory wiring regressions without needing a full GUI
- Favourite thumbnails now 48×48 with aspect-ratio fill
- Backend profile exposed in Settings dialog — Environment tab shows Rust core details

### Changed

- UI panels replaced `QGroupBox` with custom `SectionPanel` widget — collapsible headers, consistent borders, right sidebar folds away
- Fractal viewport wrapped in `ViewportWell` — checkerboard dead space, clean sizing contract
- Settings writes go through `SettingsRepository.update()` — single aggregate write path; theme changes no longer erase sidebar collapse state
- `ExportService`, `PaletteWorkflowService`, `FavoritesController` are now Qt-free — services accept typed dataclasses and callbacks, not widget instances; import policy test enforces the boundary
- `CoreBackend` is now a pure null object — `_require()` removed; all methods return safe defaults when Rust is absent
- `MainWindowSectionsState` is now a plain `@dataclass` container — `bind()` and `attach_context()` deleted; factory builds everything in a single construction pass
- Panel states no longer accept `MainWindow` directly — status callbacks injected as `on_status: Callable[[str], None]`
- `build_sections_ports()` accepts `MainWindowSectionsState` directly — adapters no longer reach into `owner._sections_state`
- `validate()` uses `dataclasses.fields()` — complete coverage by construction, no hardcoded string list
- Rust test suite fixture moved into `core/tests/fixtures/` — `cargo test` is reliably green from any working directory
- `ViewportState` formula-specific parameters decomposed into typed sub-structs (`JuliaParams`, `PhoenixParams`, `NewtonParams`, `StandardParams`)
- `MainWindowController` split into `ExportController` and `SettingsController`
- Adapter files consolidated into `ui/sections/adapters/` subdirectory

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
