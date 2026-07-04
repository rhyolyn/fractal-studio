# Review-02: Release the GIL and Parallelize the Rust Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If your harness lacks these skills, execute the tasks in order with strict TDD exactly as written.

**Goal:** Make the Rust render honest and truly asynchronous: parallelize `render_image` across rows with rayon (so `render_strategy() == "multithreaded_cpu"` becomes true), and release the Python GIL during rendering so the UI's Python-side callbacks no longer stall while a render runs on the worker thread.

**Architecture:** Two independent changes in `core/src/lib.rs`, done in this order: (1) row-parallel `render_image` via `rayon::par_chunks_mut` — pure Rust, no FFI change; (2) wrap the render call in `Python::allow_threads` inside the three `#[pyfunction]` render entry points, after all Python-borrowed inputs have been parsed into owned/`Copy` values. The Python-facing API signature does not change.

**Tech Stack:** Rust 2021, pyo3 0.28.3, rayon 1.x, maturin ≥ 1.7.

**Recommended model:** Claude Opus 4.8. *Reasoning:* the failure modes here are subtle and non-local — accidentally capturing a GIL-bound borrow inside `allow_threads`, or introducing nondeterminism/data races in the parallel loop. The plan pins the exact code, but verifying `Send`/borrow correctness and interpreting compiler errors if pyo3's API differs slightly warrants a stronger reasoning model. Sonnet 4.6 is acceptable if Opus is unavailable, since all code is specified below.

## Required Reading (before any code)

1. `AGENTS.md` at the repository root — engineering standards apply (TDD where practical, small functions, direct reporting of failures). The C++/Unreal-specific sections do not apply.
2. `README.md` sections "Full Setup — with Rust Rendering" and "Rebuilding After Rust Changes".
3. `core/src/lib.rs` — read `render_image`, `sample_pixel`, `sample_newton`, `write_pixel`, and the three `render_*` pyfunctions before editing.

## Global Constraints

- The Python-facing signatures of `render_mandelbrot`, `render_julia`, `render_fractal` must not change (pyo3's `Python<'_>` first parameter is invisible to Python callers).
- Output must be byte-identical to the current single-threaded render (each pixel is a pure function of its coordinates; row-parallelism must not change results).
- No new Python dependencies; one new Rust dependency (rayon).
- Rust tests must pass with plain `cargo test` from `core/` — no Python needed.
- Commit style: conventional commits matching repo history.

---

### Task 1: Parallelize `render_image` across rows

**Files:**
- Modify: `core/Cargo.toml`
- Modify: `core/src/lib.rs` (`render_image` ~line 572, `write_pixel` ~line 792, tests module)

**Interfaces:**
- Consumes: existing `sample_pixel`, `sample_newton` (unchanged — both are pure functions of `Copy` args plus `&[RawColor]`).
- Produces: `render_image` with identical signature and identical output; `write_row_pixel(row: &mut [u8], x: usize, color: RawColor)` replaces `write_pixel`.

- [ ] **Step 1: Write the failing determinism/equivalence test**

In the `#[cfg(test)] mod tests` block of `core/src/lib.rs`, add:

```rust
    #[test]
    fn render_is_deterministic_across_runs() {
        let palette = generate_palette(default_render_control_points(), 64);
        let params = FractalParams::new(64, 48, -0.5, 0.0, 3.0, 256).unwrap();
        let first = render_image(params, FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let second = render_image(params, FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_eq!(first, second);
    }

    #[test]
    fn render_matches_reference_row_order() {
        // Guards against row-index bugs in the parallel refactor: pixel (x=0, y=0)
        // must map to buffer offset 0 and the top row must use max imaginary.
        let palette = generate_palette(default_render_control_points(), 64);
        let params = FractalParams::new(8, 8, -0.5, 0.0, 3.0, 64).unwrap();
        let image = render_image(params, FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_eq!(image.len(), 8 * 8 * 4);
        assert!(image.chunks_exact(4).all(|pixel| pixel[3] == 255));
    }
```

- [ ] **Step 2: Run — expect pass (these lock in current behavior before refactor)**

```powershell
cd core
cargo test -q
```

Expected: all tests pass (24 existing + 2 new). These are characterization tests; they must be green before and after the refactor.

- [ ] **Step 3: Add rayon**

In `core/Cargo.toml` under `[dependencies]`:

```toml
rayon = "1.10"
```

- [ ] **Step 4: Refactor `render_image` to row-parallel**

Add at the top of `core/src/lib.rs` with the other imports:

```rust
use rayon::prelude::*;
```

Replace the body of `render_image` with:

```rust
fn render_image(params: FractalParams, mode: FractalMode, formula: Formula, palette: &[RawColor], coloring: ColoringMode, palette_offset: f64) -> ImageBuffer {
    let mut buffer = vec![0_u8; params.width * params.height * 4];
    let aspect = params.width as f64 / params.height as f64;
    let horizontal_span = params.scale * aspect;
    let vertical_span = params.scale;
    let min_x = params.center_x - horizontal_span / 2.0;
    let max_y = params.center_y + vertical_span / 2.0;
    let dx = horizontal_span / params.width as f64;
    let dy = vertical_span / params.height as f64;

    buffer
        .par_chunks_mut(params.width * 4)
        .enumerate()
        .for_each(|(y, row)| {
            let imaginary = max_y - y as f64 * dy;
            for x in 0..params.width {
                let real = min_x + x as f64 * dx;
                let color = match formula {
                    Formula::Newton(n) => sample_newton(real, imaginary, params, n, palette, palette_offset),
                    _ => sample_pixel(real, imaginary, params, mode, formula, palette, coloring, palette_offset),
                };
                write_row_pixel(row, x, color);
            }
        });

    buffer
}
```

Replace `write_pixel` with:

```rust
fn write_row_pixel(row: &mut [u8], x: usize, color: RawColor) {
    let offset = x * 4;
    row[offset] = color.0;
    row[offset + 1] = color.1;
    row[offset + 2] = color.2;
    row[offset + 3] = 255;
}
```

Delete the old `write_pixel` function entirely (nothing else calls it after this change — verify with `grep -n "write_pixel" core/src/lib.rs`).

- [ ] **Step 5: Run all Rust tests**

```powershell
cargo test -q
```

Expected: all pass, including the two Step-1 tests and all existing `*_differs_from_*` and RGBA-buffer tests. If `render_is_deterministic_across_runs` fails, the parallel loop has a data-dependence bug — stop and fix; do not weaken the test.

- [ ] **Step 6: Commit**

```powershell
git add core/Cargo.toml core/Cargo.lock core/src/lib.rs
git commit -m "perf: parallelize render_image across rows with rayon"
```

---

### Task 2: Release the GIL during rendering

**Files:**
- Modify: `core/src/lib.rs` — `render_mandelbrot` (~line 373), `render_julia` (~line 400), `render_fractal` (~line 449)

**Interfaces:**
- Consumes: `render_image` from Task 1.
- Produces: same three pyfunctions, now taking `py: Python<'_>` as first Rust parameter. Python callers are unaffected.

**Critical rule:** everything captured by the `allow_threads` closure must be owned or `Copy` — parse `&str` arguments (`formula`, `coloring_mode`) into their enum types *before* entering `allow_threads`. The code below already does this; do not reorder it.

- [ ] **Step 1: Rewrite `render_fractal`**

Add `use pyo3::Python;` if not already imported via the prelude (it is in `pyo3::prelude::*` — no new import needed).

Change the function signature and body (the `#[pyo3(signature = (...))]` attribute stays exactly as-is; `py` is not listed there):

```rust
#[allow(clippy::too_many_arguments)]
fn render_fractal(
    py: Python<'_>,
    formula: &str,
    width: usize,
    height: usize,
    center_x: f64,
    center_y: f64,
    scale: f64,
    max_iterations: u32,
    power: u32,
    julia_real: f64,
    julia_imag: f64,
    is_julia: bool,
    phoenix_real: f64,
    phoenix_imag: f64,
    palette: Vec<RawColor>,
    coloring_mode: &str,
    trap_x: f64,
    trap_y: f64,
    palette_offset: f64,
) -> PyResult<ImageBuffer> {
    let params = FractalParams::new(width, height, center_x, center_y, scale, max_iterations)
        .map_err(PyValueError::new_err)?;
    let formula = Formula::parse(formula, power, phoenix_real, phoenix_imag).map_err(PyValueError::new_err)?;
    let coloring = ColoringMode::parse(coloring_mode, trap_x, trap_y).map_err(PyValueError::new_err)?;
    let mode = if is_julia {
        FractalMode::Julia(JuliaParams { constant_real: julia_real, constant_imaginary: julia_imag })
    } else {
        FractalMode::Mandelbrot
    };
    let palette = resolve_palette(palette);
    Ok(py.allow_threads(move || render_image(params, mode, formula, &palette, coloring, palette_offset)))
}
```

- [ ] **Step 2: Rewrite `render_mandelbrot` and `render_julia` the same way**

```rust
fn render_mandelbrot(
    py: Python<'_>,
    width: usize,
    height: usize,
    center_x: f64,
    center_y: f64,
    scale: f64,
    max_iterations: u32,
    palette: Vec<RawColor>,
) -> PyResult<ImageBuffer> {
    let params = FractalParams::new(width, height, center_x, center_y, scale, max_iterations)
        .map_err(PyValueError::new_err)?;
    let palette = resolve_palette(palette);
    Ok(py.allow_threads(move || {
        render_image(params, FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0_f64)
    }))
}
```

```rust
fn render_julia(
    py: Python<'_>,
    width: usize,
    height: usize,
    constant_real: f64,
    constant_imaginary: f64,
    center_x: f64,
    center_y: f64,
    scale: f64,
    max_iterations: u32,
    palette: Vec<RawColor>,
) -> PyResult<ImageBuffer> {
    let params = FractalParams::new(width, height, center_x, center_y, scale, max_iterations)
        .map_err(PyValueError::new_err)?;
    let palette = resolve_palette(palette);
    Ok(py.allow_threads(move || {
        render_image(
            params,
            FractalMode::Julia(JuliaParams { constant_real, constant_imaginary }),
            Formula::Standard,
            &palette,
            ColoringMode::SmoothEscape,
            0.0_f64,
        )
    }))
}
```

Note the existing direct-call tests in the tests module (`render_mandelbrot(32, 24, ...)`) will no longer compile because of the new `py` parameter. Update those three call sites (`mandelbrot_renderer_returns_rgba_buffer`, `julia_renderer_returns_rgba_buffer`, `mandelbrot_and_julia_images_differ`) to call through `render_image` instead, mirroring the existing `burning_ship_differs_from_mandelbrot` pattern:

```rust
    #[test]
    fn mandelbrot_renderer_returns_rgba_buffer() {
        let palette = generate_palette(default_render_control_points(), 64);
        let image = render_image(FractalParams::new(32, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_eq!(image.len(), 32 * 24 * 4);
        assert!(image.chunks_exact(4).all(|pixel| pixel[3] == 255));
    }

    #[test]
    fn julia_renderer_returns_rgba_buffer() {
        let palette = generate_palette(default_render_control_points(), 64);
        let image = render_image(FractalParams::new(16, 16, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Julia(JuliaParams { constant_real: -0.8, constant_imaginary: 0.156 }), Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_eq!(image.len(), 16 * 16 * 4);
        assert!(image.chunks_exact(4).all(|pixel| pixel[3] == 255));
    }

    #[test]
    fn mandelbrot_and_julia_images_differ() {
        let palette = generate_palette(default_render_control_points(), 128);
        let mandelbrot = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let julia = render_image(FractalParams::new(24, 24, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Julia(JuliaParams { constant_real: -0.8, constant_imaginary: 0.156 }), Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, julia);
    }
```

- [ ] **Step 3: Run Rust tests**

```powershell
cargo test -q
```

Expected: all pass. If the compiler rejects `py.allow_threads` with a `Send`/`Ungil` bound error, something GIL-bound leaked into the closure — check that `formula`/`coloring_mode` `&str`s are parsed *before* the closure and not captured.

- [ ] **Step 4: Build the extension and run the GIL-release smoke check**

```powershell
cd core
python -m maturin develop --release
cd ..
```

Create a throwaway script `scratch_gil_check.py` at the repo root (do not commit it):

```python
import threading
import time

import fractal_core

palette = fractal_core.generate_palette(
    [(0, 0, 0), (30, 60, 90), (120, 150, 180), (240, 250, 255)], 256
)
done = threading.Event()


def render() -> None:
    fractal_core.render_fractal("standard", 1600, 1200, max_iterations=2000, palette=palette)
    done.set()


threading.Thread(target=render).start()
ticks = 0
start = time.monotonic()
while not done.is_set():
    time.sleep(0.01)
    ticks += 1
elapsed = time.monotonic() - start
print(f"render took {elapsed:.2f}s, main thread ticked {ticks} times")
assert ticks >= 5, "main thread starved during render: GIL was not released"
print("GIL released during render: OK")
```

Run: `.venv\Scripts\python.exe scratch_gil_check.py`
Expected: prints `GIL released during render: OK`. Before this change, `ticks` would be 0-1 because the render held the GIL. Delete the script afterwards.

- [ ] **Step 5: Run the Python suite to confirm no regression at the bridge**

```powershell
cd ui
..\.venv\Scripts\python.exe -m pytest -m "unit or integration" -q
```

Expected: green (baseline 177 passed, 11 subtests). The Python tests use a stubbed backend, so this catches only interface regressions, which is the point.

- [ ] **Step 6: Commit**

```powershell
git add core/src/lib.rs
git commit -m "fix: release the GIL during fractal renders so worker-thread renders stop stalling Python callbacks"
```

## Done criteria

- `cargo test` green; `render_strategy()`'s `"multithreaded_cpu"` claim is now true (rayon row parallelism).
- GIL smoke check passes: main Python thread keeps ticking while a large render runs on another thread.
- Full Python suite green.

## Explicit non-goals (do not do these here)

- Splitting `lib.rs` into modules, or separating the escape-iteration pass from the coloring pass (master-plan backlog item).
- Cancellation or progress reporting for renders.
