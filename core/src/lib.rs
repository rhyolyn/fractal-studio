use std::fs;
use std::path::Path;

use pyo3::exceptions::{PyOSError, PyValueError};
use pyo3::prelude::*;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

const DEFAULT_PALETTE_SIZE: usize = 2048;
const DEFAULT_PREVIEW_WIDTH: u32 = 1280;
const DEFAULT_PREVIEW_HEIGHT: u32 = 720;
const LEGACY_PALETTE_SIZE: usize = 256;
const MODERN_PALETTE_FORMAT: &str = "fractal-studio.palette.v1";

type RawColor = (u8, u8, u8);
type ImageBuffer = Vec<u8>;

#[derive(Clone, Copy, Debug, PartialEq)]
struct ColorPoint {
    red: f64,
    green: f64,
    blue: f64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CubeFace {
    One,
    Two,
    Three,
    Four,
    Five,
    Six,
}

#[derive(Debug, Deserialize, Serialize, PartialEq)]
struct PaletteDocument {
    format: String,
    palette_size: usize,
    control_points: Vec<RawColor>,
}

#[derive(Clone, Copy, Debug)]
struct FractalParams {
    width: usize,
    height: usize,
    center_x: f64,
    center_y: f64,
    scale: f64,
    max_iterations: u32,
    escape_radius: f64,
}

#[derive(Clone, Copy, Debug)]
struct JuliaParams {
    constant_real: f64,
    constant_imaginary: f64,
}

#[derive(Clone, Copy, Debug)]
enum Formula {
    Standard,
    BurningShip,
    Tricorn,
    Celtic,
    Buffalo,
    Multibrot(u32),
    Phoenix { p_real: f64, p_imag: f64 },
    Newton(u32),
}

#[derive(Clone, Copy, Debug)]
enum FractalMode {
    Mandelbrot,
    Julia(JuliaParams),
}

#[derive(Clone, Copy, Debug)]
enum ColoringMode {
    SmoothEscape,
    OrbitTrapCircle,
    OrbitTrapCross,
    OrbitTrapPoint(f64, f64),
    InteriorDwell,
}

impl ColoringMode {
    fn parse(s: &str, trap_x: f64, trap_y: f64) -> Result<Self, &'static str> {
        match s {
            "smooth_escape"     => Ok(Self::SmoothEscape),
            "orbit_trap_circle" => Ok(Self::OrbitTrapCircle),
            "orbit_trap_cross"  => Ok(Self::OrbitTrapCross),
            "orbit_trap_point"  => Ok(Self::OrbitTrapPoint(trap_x, trap_y)),
            "interior_dwell"    => Ok(Self::InteriorDwell),
            _ => Err("coloring_mode must be: smooth_escape, orbit_trap_circle, orbit_trap_cross, orbit_trap_point, or interior_dwell"),
        }
    }
}

impl Formula {
    fn parse(s: &str, power: u32, phoenix_real: f64, phoenix_imag: f64) -> Result<Self, &'static str> {
        match s {
            "standard"     => Ok(Self::Standard),
            "burning_ship" => Ok(Self::BurningShip),
            "tricorn"      => Ok(Self::Tricorn),
            "celtic"       => Ok(Self::Celtic),
            "buffalo"      => Ok(Self::Buffalo),
            "multibrot"    => Ok(Self::Multibrot(power)),
            "phoenix"      => Ok(Self::Phoenix { p_real: phoenix_real, p_imag: phoenix_imag }),
            "newton"       => Ok(Self::Newton(power.max(2))),
            _ => Err("formula must be one of: standard, burning_ship, tricorn, celtic, buffalo, multibrot, phoenix, newton"),
        }
    }

    fn escape_power(self) -> f64 {
        match self {
            Self::Multibrot(n) => f64::from(n),
            _ => 2.0,
        }
    }
}

impl TryFrom<u8> for CubeFace {
    type Error = PyErr;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            1 => Ok(Self::One),
            2 => Ok(Self::Two),
            3 => Ok(Self::Three),
            4 => Ok(Self::Four),
            5 => Ok(Self::Five),
            6 => Ok(Self::Six),
            _ => Err(PyValueError::new_err("face must be an integer in the range 1..=6")),
        }
    }
}

impl ColorPoint {
    fn from_raw(color: RawColor) -> Self {
        Self {
            red: f64::from(color.0),
            green: f64::from(color.1),
            blue: f64::from(color.2),
        }
    }

    fn into_raw(self) -> RawColor {
        (
            channel_to_u8(self.red),
            channel_to_u8(self.green),
            channel_to_u8(self.blue),
        )
    }

    fn clamped(self) -> Self {
        Self {
            red: clamp_channel(self.red),
            green: clamp_channel(self.green),
            blue: clamp_channel(self.blue),
        }
    }
}

impl CubeFace {
    fn color_at(self, position: (f64, f64)) -> ColorPoint {
        let x = clamp_unit(position.0);
        let y = clamp_unit(position.1);
        let low = 0.0;
        let high = 255.0;

        match self {
            Self::One => ColorPoint {
                red: high,
                green: scale_unit(1.0 - x),
                blue: scale_unit(y),
            },
            Self::Two => ColorPoint {
                red: scale_unit(x),
                green: high,
                blue: scale_unit(y),
            },
            Self::Three => ColorPoint {
                red: scale_unit(x),
                green: scale_unit(1.0 - y),
                blue: high,
            },
            Self::Four => ColorPoint {
                red: low,
                green: scale_unit(1.0 - x),
                blue: scale_unit(y),
            },
            Self::Five => ColorPoint {
                red: scale_unit(x),
                green: low,
                blue: scale_unit(y),
            },
            Self::Six => ColorPoint {
                red: scale_unit(x),
                green: scale_unit(1.0 - y),
                blue: low,
            },
        }
    }

    fn project(self, color: ColorPoint) -> (f64, f64) {
        let color = color.clamped();

        match self {
            Self::One | Self::Four => (
                normalize_channel(255.0 - color.green),
                normalize_channel(color.blue),
            ),
            Self::Two | Self::Five => {
                (normalize_channel(color.red), normalize_channel(color.blue))
            }
            Self::Three | Self::Six => (
                normalize_channel(color.red),
                normalize_channel(255.0 - color.green),
            ),
        }
    }

    fn merge(self, current: ColorPoint, sampled: ColorPoint) -> ColorPoint {
        match self {
            Self::One | Self::Four => ColorPoint {
                red: current.red,
                green: sampled.green,
                blue: sampled.blue,
            },
            Self::Two | Self::Five => ColorPoint {
                red: sampled.red,
                green: current.green,
                blue: sampled.blue,
            },
            Self::Three | Self::Six => ColorPoint {
                red: sampled.red,
                green: sampled.green,
                blue: current.blue,
            },
        }
    }
}

impl PaletteDocument {
    fn new(control_points: Vec<RawColor>, palette_size: usize) -> Self {
        Self {
            format: MODERN_PALETTE_FORMAT.into(),
            palette_size,
            control_points,
        }
    }

    fn validate(&self) -> Result<(), String> {
        if self.format != MODERN_PALETTE_FORMAT {
            return Err(format!("unsupported palette format: {}", self.format));
        }

        if self.palette_size == 0 {
            return Err("palette_size must be greater than zero".into());
        }

        Ok(())
    }
}

#[pyfunction]
fn recommended_palette_size() -> usize {
    DEFAULT_PALETTE_SIZE
}

#[pyfunction]
fn default_preview_size() -> (u32, u32) {
    (DEFAULT_PREVIEW_WIDTH, DEFAULT_PREVIEW_HEIGHT)
}

#[pyfunction]
fn coloring_model() -> &'static str {
    "smooth_escape"
}

#[pyfunction]
fn render_strategy() -> &'static str {
    "multithreaded_cpu"
}

#[pyfunction]
fn supports_supersampling() -> bool {
    true
}

#[pyfunction]
fn export_presets() -> Vec<String> {
    vec!["2K".into(), "4K".into(), "8K".into(), "Tiled".into()]
}

#[pyfunction]
fn legacy_palette_size() -> usize {
    LEGACY_PALETTE_SIZE
}

#[pyfunction]
fn color_from_face(face: u8, position: (f64, f64)) -> PyResult<RawColor> {
    let face = CubeFace::try_from(face)?;
    Ok(face.color_at(position).into_raw())
}

#[pyfunction]
fn project_color_to_face(face: u8, color: RawColor) -> PyResult<(f64, f64)> {
    let face = CubeFace::try_from(face)?;
    Ok(face.project(ColorPoint::from_raw(color)))
}

#[pyfunction]
fn update_control_point_from_face(
    face: u8,
    color: RawColor,
    position: (f64, f64),
) -> PyResult<RawColor> {
    let face = CubeFace::try_from(face)?;
    let current = ColorPoint::from_raw(color);
    let sampled = face.color_at(position);
    Ok(face.merge(current, sampled).into_raw())
}

#[pyfunction]
fn generate_palette(control_points: Vec<RawColor>, palette_size: usize) -> Vec<RawColor> {
    let points = control_points
        .into_iter()
        .map(ColorPoint::from_raw)
        .collect::<Vec<_>>();

    generate_palette_from_points(&points, palette_size)
}

#[pyfunction]
fn import_legacy_map(path: String) -> PyResult<Vec<RawColor>> {
    let contents = read_file(&path)?;
    parse_legacy_map(&contents).map_err(PyValueError::new_err)
}

#[pyfunction]
fn export_legacy_map(path: String, palette: Vec<RawColor>) -> PyResult<()> {
    write_file(&path, &serialize_legacy_map(&palette).map_err(PyValueError::new_err)?)
}

#[pyfunction]
fn import_palette_json(path: String) -> PyResult<(usize, Vec<RawColor>)> {
    let contents = read_file(&path)?;
    let document = parse_palette_document(&contents).map_err(PyValueError::new_err)?;
    Ok((document.palette_size, document.control_points))
}

#[pyfunction]
fn export_palette_json(
    path: String,
    control_points: Vec<RawColor>,
    palette_size: usize,
) -> PyResult<()> {
    let document = PaletteDocument::new(control_points, palette_size);
    let contents = serialize_palette_document(&document).map_err(PyValueError::new_err)?;
    write_file(&path, &contents)
}

#[pyfunction]
#[pyo3(signature = (
    width,
    height,
    center_x = -0.5,
    center_y = 0.0,
    scale = 3.0,
    max_iterations = 512,
    palette = Vec::new()
))]
fn render_mandelbrot(
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
    Ok(render_image(params, FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0_f64))
}

#[pyfunction]
#[pyo3(signature = (
    width,
    height,
    constant_real,
    constant_imaginary,
    center_x = 0.0,
    center_y = 0.0,
    scale = 3.0,
    max_iterations = 512,
    palette = Vec::new()
))]
fn render_julia(
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
    Ok(render_image(
        params,
        FractalMode::Julia(JuliaParams {
            constant_real,
            constant_imaginary,
        }),
        Formula::Standard,
        &palette,
        ColoringMode::SmoothEscape,
        0.0_f64,
    ))
}

#[pyfunction]
#[pyo3(signature = (
    formula,
    width,
    height,
    center_x = -0.5,
    center_y = 0.0,
    scale = 3.0,
    max_iterations = 512,
    power = 2_u32,
    julia_real = 0.0_f64,
    julia_imag = 0.0_f64,
    is_julia = false,
    phoenix_real = 0.5_f64,
    phoenix_imag = 0.0_f64,
    palette = Vec::new(),
    coloring_mode = "smooth_escape",
    trap_x = 0.0_f64,
    trap_y = 0.0_f64,
    palette_offset = 0.0_f64
))]
#[allow(clippy::too_many_arguments)]
fn render_fractal(
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
    Ok(render_image(params, mode, formula, &palette, coloring, palette_offset))
}

#[pymodule]
fn fractal_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(recommended_palette_size, module)?)?;
    module.add_function(wrap_pyfunction!(default_preview_size, module)?)?;
    module.add_function(wrap_pyfunction!(coloring_model, module)?)?;
    module.add_function(wrap_pyfunction!(render_strategy, module)?)?;
    module.add_function(wrap_pyfunction!(supports_supersampling, module)?)?;
    module.add_function(wrap_pyfunction!(export_presets, module)?)?;
    module.add_function(wrap_pyfunction!(legacy_palette_size, module)?)?;
    module.add_function(wrap_pyfunction!(color_from_face, module)?)?;
    module.add_function(wrap_pyfunction!(project_color_to_face, module)?)?;
    module.add_function(wrap_pyfunction!(update_control_point_from_face, module)?)?;
    module.add_function(wrap_pyfunction!(generate_palette, module)?)?;
    module.add_function(wrap_pyfunction!(import_legacy_map, module)?)?;
    module.add_function(wrap_pyfunction!(export_legacy_map, module)?)?;
    module.add_function(wrap_pyfunction!(import_palette_json, module)?)?;
    module.add_function(wrap_pyfunction!(export_palette_json, module)?)?;
    module.add_function(wrap_pyfunction!(render_mandelbrot, module)?)?;
    module.add_function(wrap_pyfunction!(render_julia, module)?)?;
    module.add_function(wrap_pyfunction!(render_fractal, module)?)?;
    Ok(())
}

impl FractalParams {
    fn new(
        width: usize,
        height: usize,
        center_x: f64,
        center_y: f64,
        scale: f64,
        max_iterations: u32,
    ) -> Result<Self, &'static str> {
        if width == 0 || height == 0 {
            return Err("width and height must be greater than zero");
        }

        if !scale.is_finite() || scale <= 0.0 {
            return Err("scale must be a finite positive value");
        }

        if max_iterations == 0 {
            return Err("max_iterations must be greater than zero");
        }

        Ok(Self {
            width,
            height,
            center_x,
            center_y,
            scale,
            max_iterations,
            escape_radius: 4.0,
        })
    }
}

fn generate_palette_from_points(points: &[ColorPoint], palette_size: usize) -> Vec<RawColor> {
    if points.len() < 4 || palette_size == 0 {
        return Vec::new();
    }

    if palette_size == 1 {
        return vec![points[1].clamped().into_raw()];
    }

    let segment_count = points.len() - 3;
    (0..palette_size)
        .map(|index| sample_palette(points, segment_count, index, palette_size))
        .collect()
}

fn resolve_palette(palette: Vec<RawColor>) -> Vec<RawColor> {
    if palette.is_empty() {
        generate_palette(default_render_control_points(), DEFAULT_PALETTE_SIZE)
    } else {
        palette
    }
}

fn default_render_control_points() -> Vec<RawColor> {
    vec![
        (0, 0, 0),
        (20, 32, 64),
        (64, 112, 192),
        (192, 224, 255),
        (255, 192, 96),
        (255, 255, 255),
    ]
}

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

fn sample_pixel(
    real: f64,
    imaginary: f64,
    params: FractalParams,
    mode: FractalMode,
    formula: Formula,
    palette: &[RawColor],
    coloring: ColoringMode,
    palette_offset: f64,
) -> RawColor {
    let (mut zr, mut zi, cr, ci) = match mode {
        FractalMode::Mandelbrot => (0.0, 0.0, real, imaginary),
        FractalMode::Julia(c) => (real, imaginary, c.constant_real, c.constant_imaginary),
    };

    let (mut prev_zr, mut prev_zi) = (0.0_f64, 0.0_f64);
    let mut min_trap = f64::MAX;
    let mut iteration = 0_u32;

    while zr * zr + zi * zi <= params.escape_radius && iteration < params.max_iterations {
        let (new_zr, new_zi) = apply_formula(zr, zi, cr, ci, prev_zr, prev_zi, formula);
        (prev_zr, prev_zi) = (zr, zi);
        (zr, zi) = (new_zr, new_zi);
        iteration += 1;
        min_trap = min_trap.min(trap_metric(zr, zi, coloring));
    }

    match coloring {
        ColoringMode::SmoothEscape => {
            if iteration >= params.max_iterations {
                return (0, 0, 0);
            }
            let v = smooth_escape_value(iteration, zr, zi, formula.escape_power());
            palette_lookup(palette, v, palette_offset)
        }
        ColoringMode::OrbitTrapCircle | ColoringMode::OrbitTrapCross | ColoringMode::OrbitTrapPoint(..) => {
            let v = trap_color_value(min_trap, coloring);
            palette_lookup(palette, v, palette_offset)
        }
        ColoringMode::InteriorDwell => {
            if iteration >= params.max_iterations {
                let dwell = (zr * zr + zi * zi) / params.escape_radius;
                palette_lookup(palette, dwell * 20.0, palette_offset)
            } else {
                let v = smooth_escape_value(iteration, zr, zi, formula.escape_power());
                palette_lookup(palette, v, palette_offset)
            }
        }
    }
}

fn apply_formula(zr: f64, zi: f64, cr: f64, ci: f64, prev_zr: f64, prev_zi: f64, formula: Formula) -> (f64, f64) {
    match formula {
        Formula::Standard    => (zr * zr - zi * zi + cr, 2.0 * zr * zi + ci),
        Formula::BurningShip => (zr * zr - zi * zi + cr, 2.0 * zr.abs() * zi.abs() + ci),
        Formula::Tricorn     => (zr * zr - zi * zi + cr, -2.0 * zr * zi + ci),
        Formula::Celtic      => ((zr * zr - zi * zi).abs() + cr, 2.0 * zr * zi + ci),
        Formula::Buffalo     => ((zr * zr - zi * zi).abs() + cr, (2.0 * zr * zi).abs() + ci),
        Formula::Multibrot(n) => {
            let (pr, pi) = complex_pow(zr, zi, n);
            (pr + cr, pi + ci)
        }
        Formula::Phoenix { p_real, p_imag } => (
            zr * zr - zi * zi + cr + p_real * prev_zr - p_imag * prev_zi,
            2.0 * zr * zi + ci + p_real * prev_zi + p_imag * prev_zr,
        ),
        Formula::Newton(_) => unreachable!("Newton is dispatched before sample_pixel"),
    }
}

fn complex_pow(zr: f64, zi: f64, power: u32) -> (f64, f64) {
    let (mut rr, mut ri) = (1.0_f64, 0.0_f64);
    for _ in 0..power {
        (rr, ri) = (rr * zr - ri * zi, rr * zi + ri * zr);
    }
    (rr, ri)
}

fn smooth_escape_value(iteration: u32, zr: f64, zi: f64, power: f64) -> f64 {
    let magnitude_squared = zr * zr + zi * zi;
    let magnitude = magnitude_squared.sqrt().max(1.000_000_1);
    let smooth = iteration as f64 + 1.0 - magnitude.ln().ln() / power.ln();
    smooth.max(0.0)
}

fn trap_metric(zr: f64, zi: f64, coloring: ColoringMode) -> f64 {
    match coloring {
        ColoringMode::OrbitTrapCircle          => zr * zr + zi * zi,
        ColoringMode::OrbitTrapCross           => zr.abs().min(zi.abs()),
        ColoringMode::OrbitTrapPoint(tx, ty)   => { let dr = zr - tx; let di = zi - ty; dr * dr + di * di }
        _                                      => f64::MAX,
    }
}

fn trap_color_value(min_trap: f64, coloring: ColoringMode) -> f64 {
    match coloring {
        ColoringMode::OrbitTrapCircle        => min_trap.sqrt() * 10.0,
        ColoringMode::OrbitTrapCross         => min_trap * 20.0,
        ColoringMode::OrbitTrapPoint(..)     => min_trap.sqrt() * 10.0,
        _                                    => 0.0,
    }
}

fn palette_lookup(palette: &[RawColor], escape_value: f64, offset: f64) -> RawColor {
    if palette.is_empty() {
        return (255, 255, 255);
    }
    let last = palette.len().saturating_sub(1);
    let normalized = (escape_value * 0.025 + offset).fract();
    let offset_px = normalized * last as f64;
    let low = offset_px.floor() as usize;
    let high = offset_px.ceil().min(last as f64) as usize;
    let t = offset_px - low as f64;
    mix_colors(palette[low], palette[high], t)
}

fn sample_newton(
    real: f64,
    imag: f64,
    params: FractalParams,
    power: u32,
    palette: &[RawColor],
    palette_offset: f64,
) -> RawColor {
    let n = power as f64;
    let (mut zr, mut zi) = (real, imag);
    let tolerance_sq = 1e-12_f64;

    let mut iteration = 0_u32;
    loop {
        let (zn1r, zn1i) = complex_pow(zr, zi, power - 1);
        let znr = zn1r * zr - zn1i * zi;
        let zni = zn1r * zi + zn1i * zr;

        let fr = znr - 1.0;
        let fi = zni;
        let dr = n * zn1r;
        let di = n * zn1i;

        let denom = dr * dr + di * di;
        if denom < 1e-24 {
            break;
        }
        let step_r = (fr * dr + fi * di) / denom;
        let step_i = (fi * dr - fr * di) / denom;

        zr -= step_r;
        zi -= step_i;
        iteration += 1;

        if step_r * step_r + step_i * step_i < tolerance_sq || iteration >= params.max_iterations {
            break;
        }
    }

    use std::f64::consts::TAU;
    let angle = zi.atan2(zr).rem_euclid(TAU);
    let root_index = ((angle * n / TAU).round() as usize).min(power as usize - 1);

    let base_t = root_index as f64 / n;
    let brightness = 1.0 - (iteration as f64 / params.max_iterations as f64).sqrt().min(1.0);
    palette_at_t(palette, base_t, brightness, palette_offset)
}

fn palette_at_t(palette: &[RawColor], t: f64, brightness: f64, offset: f64) -> RawColor {
    if palette.is_empty() {
        return (255, 255, 255);
    }
    let n = palette.len();
    let adjusted_t = (t + offset).fract();
    let offset_px = adjusted_t * (n - 1) as f64;
    let low = offset_px.floor() as usize;
    let high = (low + 1).min(n - 1);
    let frac = offset_px - low as f64;
    let base = mix_colors(palette[low], palette[high], frac);
    (
        (f64::from(base.0) * brightness).round().clamp(0.0, 255.0) as u8,
        (f64::from(base.1) * brightness).round().clamp(0.0, 255.0) as u8,
        (f64::from(base.2) * brightness).round().clamp(0.0, 255.0) as u8,
    )
}

fn mix_colors(start: RawColor, end: RawColor, t: f64) -> RawColor {
    let interpolate = |a: u8, b: u8| -> u8 {
        let value = f64::from(a) + (f64::from(b) - f64::from(a)) * t;
        value.round().clamp(0.0, 255.0) as u8
    };

    (
        interpolate(start.0, end.0),
        interpolate(start.1, end.1),
        interpolate(start.2, end.2),
    )
}

fn write_row_pixel(row: &mut [u8], x: usize, color: RawColor) {
    let offset = x * 4;
    row[offset] = color.0;
    row[offset + 1] = color.1;
    row[offset + 2] = color.2;
    row[offset + 3] = 255;
}

fn sample_palette(
    points: &[ColorPoint],
    segment_count: usize,
    index: usize,
    palette_size: usize,
) -> RawColor {
    let last_segment = segment_count - 1;
    let span = segment_count as f64;
    let offset = index as f64 * span / (palette_size - 1) as f64;
    let segment_index = offset.floor().min(last_segment as f64) as usize;
    let t = if index + 1 == palette_size {
        1.0
    } else {
        offset - segment_index as f64
    };

    let point = catmull_rom(
        points[segment_index],
        points[segment_index + 1],
        points[segment_index + 2],
        points[segment_index + 3],
        t,
    );

    point.clamped().into_raw()
}

fn catmull_rom(p0: ColorPoint, p1: ColorPoint, p2: ColorPoint, p3: ColorPoint, t: f64) -> ColorPoint {
    ColorPoint {
        red: catmull_rom_channel(p0.red, p1.red, p2.red, p3.red, t),
        green: catmull_rom_channel(p0.green, p1.green, p2.green, p3.green, t),
        blue: catmull_rom_channel(p0.blue, p1.blue, p2.blue, p3.blue, t),
    }
}

fn catmull_rom_channel(p0: f64, p1: f64, p2: f64, p3: f64, t: f64) -> f64 {
    0.5
        * ((-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
            + (-p0 + p2) * t
            + 2.0 * p1)
}

fn parse_legacy_map(contents: &str) -> Result<Vec<RawColor>, String> {
    let palette = contents
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(parse_legacy_line)
        .collect::<Result<Vec<_>, _>>()?;

    if palette.len() != LEGACY_PALETTE_SIZE {
        return Err(format!(
            "legacy palette must contain exactly {} colors, found {}",
            LEGACY_PALETTE_SIZE,
            palette.len()
        ));
    }

    Ok(palette)
}

fn parse_legacy_line(line: &str) -> Result<RawColor, String> {
    let values = line
        .split_whitespace()
        .map(|part| {
            part.parse::<u16>()
                .map_err(|_| format!("invalid legacy palette value: {part}"))
                .and_then(|value| {
                    u8::try_from(value).map_err(|_| format!("legacy palette value out of range: {value}"))
                })
        })
        .collect::<Result<Vec<_>, _>>()?;

    match values.as_slice() {
        [red, green, blue] => Ok((*red, *green, *blue)),
        _ => Err(format!("legacy palette line must contain exactly 3 integers: {line}")),
    }
}

fn serialize_legacy_map(palette: &[RawColor]) -> Result<String, String> {
    if palette.len() != LEGACY_PALETTE_SIZE {
        return Err(format!(
            "legacy palette export requires exactly {} colors, found {}",
            LEGACY_PALETTE_SIZE,
            palette.len()
        ));
    }

    Ok(palette
        .iter()
        .map(|(red, green, blue)| format!("{red:>3} {green:>3} {blue:>3}"))
        .collect::<Vec<_>>()
        .join("\n")
        + "\n")
}

fn parse_palette_document(contents: &str) -> Result<PaletteDocument, String> {
    let document =
        serde_json::from_str::<PaletteDocument>(contents).map_err(|error| format!("invalid palette json: {error}"))?;
    document.validate()?;
    Ok(document)
}

fn serialize_palette_document(document: &PaletteDocument) -> Result<String, String> {
    document.validate()?;
    serde_json::to_string_pretty(document)
        .map_err(|error| format!("unable to serialize palette json: {error}"))
}

fn read_file(path: &str) -> PyResult<String> {
    fs::read_to_string(Path::new(path)).map_err(|error| PyOSError::new_err(error.to_string()))
}

fn write_file(path: &str, contents: &str) -> PyResult<()> {
    fs::write(Path::new(path), contents).map_err(|error| PyOSError::new_err(error.to_string()))
}

fn clamp_unit(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

fn scale_unit(value: f64) -> f64 {
    clamp_unit(value) * 255.0
}

fn clamp_channel(value: f64) -> f64 {
    value.clamp(0.0, 255.0)
}

fn normalize_channel(value: f64) -> f64 {
    clamp_channel(value) / 255.0
}

fn channel_to_u8(value: f64) -> u8 {
    clamp_channel(value).round() as u8
}

#[cfg(test)]
mod tests {
    use std::env;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    #[derive(Deserialize)]
    struct RegressionFixture {
        control_points: Vec<RawColor>,
        palette_size: usize,
        expected_palette: Vec<RawColor>,
    }

    fn sample_points() -> Vec<RawColor> {
        vec![(0, 0, 0), (32, 64, 96), (128, 160, 192), (224, 240, 255)]
    }

    fn unique_temp_path(name: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after unix epoch")
            .as_nanos();

        env::temp_dir().join(format!("fractal-studio-{stamp}-{name}"))
    }

    fn fixture_path(name: &str) -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join(name)
    }

    #[test]
    fn modern_palette_size_exceeds_legacy_limit() {
        assert!(recommended_palette_size() > legacy_palette_size());
    }

    #[test]
    fn preview_size_is_landscape() {
        let (width, height) = default_preview_size();
        assert!(width > height);
    }

    #[test]
    fn face_two_round_trips_projected_colors() {
        let position = project_color_to_face(2, (64, 255, 128)).unwrap();
        assert_eq!(color_from_face(2, position).unwrap(), (64, 255, 128));
    }

    #[test]
    fn face_one_drag_preserves_red_channel() {
        let updated = update_control_point_from_face(1, (120, 90, 60), (0.25, 0.75)).unwrap();
        assert_eq!(updated.0, 120);
        assert_ne!(updated.1, 90);
        assert_ne!(updated.2, 60);
    }

    #[test]
    fn face_five_drag_preserves_green_channel() {
        let updated = update_control_point_from_face(5, (120, 90, 60), (0.25, 0.75)).unwrap();
        assert_eq!(updated.1, 90);
    }

    #[test]
    fn palette_generation_requires_four_points() {
        let palette = generate_palette(vec![(0, 0, 0), (255, 255, 255), (0, 0, 0)], 64);
        assert!(palette.is_empty());
    }

    #[test]
    fn palette_generation_respects_requested_size() {
        let palette = generate_palette(sample_points(), 64);
        assert_eq!(palette.len(), 64);
    }

    #[test]
    fn palette_generation_starts_and_ends_on_inner_control_points() {
        let points = sample_points();
        let palette = generate_palette(points.clone(), 64);
        assert_eq!(palette.first().copied(), Some(points[1]));
        assert_eq!(palette.last().copied(), Some(points[2]));
    }

    #[test]
    fn palette_generation_clamps_out_of_range_segments() {
        let points = vec![(255, 255, 255), (255, 255, 255), (255, 255, 255), (255, 255, 255)];
        let palette = generate_palette(points, 8);
        assert!(palette.iter().all(|color| *color == (255, 255, 255)));
    }

    #[test]
    fn regression_fixture_matches_expected_palette() {
        let contents = fs::read_to_string(fixture_path("palette_regression_v1.json")).unwrap();
        let fixture = serde_json::from_str::<RegressionFixture>(&contents).unwrap();
        let palette = generate_palette(fixture.control_points, fixture.palette_size);
        assert_eq!(palette, fixture.expected_palette);
    }

    #[test]
    fn legacy_palette_parser_reads_existing_repo_map() {
        let contents = fs::read_to_string(fixture_path("china.map")).unwrap();

        let palette = parse_legacy_map(&contents).unwrap();
        let first_line = contents.lines().find(|line| !line.trim().is_empty()).unwrap();
        let last_line = contents
            .lines()
            .rev()
            .find(|line| !line.trim().is_empty())
            .unwrap();
        assert_eq!(palette.len(), LEGACY_PALETTE_SIZE);
        assert_eq!(palette.first().copied(), Some(parse_legacy_line(first_line).unwrap()));
        assert_eq!(palette.last().copied(), Some(parse_legacy_line(last_line).unwrap()));
    }

    #[test]
    fn legacy_palette_round_trips_through_disk() {
        let palette = generate_palette(
            vec![
                (0, 0, 0),
                (32, 64, 96),
                (96, 128, 160),
                (160, 192, 224),
                (224, 240, 255),
                (255, 255, 255),
            ],
            LEGACY_PALETTE_SIZE,
        );

        let path = unique_temp_path("palette.map");
        export_legacy_map(path.to_string_lossy().into_owned(), palette.clone()).unwrap();
        let loaded = import_legacy_map(path.to_string_lossy().into_owned()).unwrap();
        fs::remove_file(path).unwrap();

        assert_eq!(loaded, palette);
    }

    #[test]
    fn modern_palette_document_round_trips_through_disk() {
        let control_points = vec![
            (0, 0, 0),
            (32, 64, 96),
            (96, 128, 160),
            (160, 192, 224),
        ];
        let path = unique_temp_path("palette.json");

        export_palette_json(
            path.to_string_lossy().into_owned(),
            control_points.clone(),
            DEFAULT_PALETTE_SIZE,
        )
        .unwrap();
        let loaded = import_palette_json(path.to_string_lossy().into_owned()).unwrap();
        fs::remove_file(path).unwrap();

        assert_eq!(loaded, (DEFAULT_PALETTE_SIZE, control_points));
    }

    #[test]
    fn mandelbrot_renderer_returns_rgba_buffer() {
        let palette = generate_palette(default_render_control_points(), 64);
        let image = render_mandelbrot(32, 24, -0.5, 0.0, 3.0, 128, palette).unwrap();
        assert_eq!(image.len(), 32 * 24 * 4);
        assert!(image.chunks_exact(4).all(|pixel| pixel[3] == 255));
    }

    #[test]
    fn julia_renderer_returns_rgba_buffer() {
        let palette = generate_palette(default_render_control_points(), 64);
        let image = render_julia(16, 16, -0.8, 0.156, 0.0, 0.0, 3.0, 128, palette).unwrap();
        assert_eq!(image.len(), 16 * 16 * 4);
        assert!(image.chunks_exact(4).all(|pixel| pixel[3] == 255));
    }

    #[test]
    fn mandelbrot_and_julia_images_differ() {
        let palette = generate_palette(default_render_control_points(), 128);
        let mandelbrot = render_mandelbrot(24, 24, -0.5, 0.0, 3.0, 128, palette.clone()).unwrap();
        let julia = render_julia(24, 24, -0.8, 0.156, 0.0, 0.0, 3.0, 128, palette).unwrap();
        assert_ne!(mandelbrot, julia);
    }

    #[test]
    fn fractal_renderer_rejects_invalid_dimensions() {
        let error = FractalParams::new(0, 24, -0.5, 0.0, 3.0, 128).unwrap_err();
        assert!(error.contains("width and height"));
    }

    #[test]
    fn burning_ship_differs_from_mandelbrot() {
        let palette = generate_palette(default_render_control_points(), 64);
        let mandelbrot = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let burning = render_image(FractalParams::new(24, 24, -0.5, -0.5, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::BurningShip, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, burning);
    }

    #[test]
    fn tricorn_differs_from_mandelbrot() {
        let palette = generate_palette(default_render_control_points(), 64);
        let mandelbrot = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let tricorn = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Tricorn, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, tricorn);
    }

    #[test]
    fn multibrot_power3_differs_from_mandelbrot() {
        let palette = generate_palette(default_render_control_points(), 64);
        let mandelbrot = render_image(FractalParams::new(24, 24, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let multibrot = render_image(FractalParams::new(24, 24, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Multibrot(3), &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, multibrot);
    }

    #[test]
    fn celtic_differs_from_mandelbrot() {
        let palette = generate_palette(default_render_control_points(), 64);
        let mandelbrot = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let celtic = render_image(FractalParams::new(24, 24, -0.5, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Celtic, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, celtic);
    }

    #[test]
    fn buffalo_differs_from_burning_ship() {
        let palette = generate_palette(default_render_control_points(), 64);
        let burning = render_image(FractalParams::new(24, 24, -0.5, -0.5, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::BurningShip, &palette, ColoringMode::SmoothEscape, 0.0);
        let buffalo = render_image(FractalParams::new(24, 24, -0.5, -0.5, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Buffalo, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(burning, buffalo);
    }

    #[test]
    fn phoenix_differs_from_mandelbrot() {
        let palette = generate_palette(default_render_control_points(), 64);
        let mandelbrot = render_image(FractalParams::new(24, 24, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Standard, &palette, ColoringMode::SmoothEscape, 0.0);
        let phoenix = render_image(FractalParams::new(24, 24, 0.0, 0.0, 3.0, 128).unwrap(), FractalMode::Mandelbrot, Formula::Phoenix { p_real: 0.5, p_imag: 0.0 }, &palette, ColoringMode::SmoothEscape, 0.0);
        assert_ne!(mandelbrot, phoenix);
    }

    #[test]
    fn complex_pow_power2_matches_standard_step() {
        let (zr, zi) = (0.3, 0.7);
        let (pr, pi) = complex_pow(zr, zi, 2);
        assert!((pr - (zr * zr - zi * zi)).abs() < 1e-12);
        assert!((pi - (2.0 * zr * zi)).abs() < 1e-12);
    }

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
}
