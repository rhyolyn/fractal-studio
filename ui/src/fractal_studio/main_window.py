from __future__ import annotations

import base64
import datetime
import json
import uuid
import weakref
from pathlib import Path

_FAVORITES_PATH = Path.home() / ".fractal_studio" / "favorites.json"

from PySide6.QtCore import QBuffer, QByteArray, QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.backend import BackendProfile, load_backend
from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget


class CustomResolutionDialog(QDialog):
    def __init__(self, default_width: int = 1920, default_height: int = 1080, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Custom Resolution")
        self._width_box = QSpinBox()
        self._width_box.setRange(64, 16384)
        self._width_box.setValue(default_width)
        self._height_box = QSpinBox()
        self._height_box.setRange(64, 16384)
        self._height_box.setValue(default_height)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout()
        layout.addRow("Width:", self._width_box)
        layout.addRow("Height:", self._height_box)
        layout.addRow(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[int, int]:
        return self._width_box.value(), self._height_box.value()


class FavoriteThumbnailRow(QWidget):
    def __init__(
        self,
        pixmap: QPixmap,
        fav: dict,
        hover_panel: QLabel,
        on_select,
        on_activate=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._fav = fav
        self._hover_panel = hover_panel
        self._on_select = on_select
        self._on_activate = on_activate if on_activate is not None else on_select
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(8)

        self._thumb_label = QLabel()
        self._thumb_label.setObjectName("favoriteThumb")
        self._thumb_label.setFixedSize(48, 36)
        self._thumb_label.setPixmap(
            pixmap.scaled(48, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

        self._name_label = QLabel(fav["name"])
        self._name_label.setObjectName("favoriteName")
        self._name_label.setMinimumWidth(0)
        self._name_label.setWordWrap(False)

        # Let the row receive hover/click events even when the cursor is over child labels.
        self._thumb_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self._thumb_label)
        layout.addWidget(self._name_label, 1)
        self.setLayout(layout)
        self._thumb_label.setStyleSheet("border: 2px solid transparent; border-radius: 3px;")
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_visual_state()

    def _set_hovered(self, hovered: bool) -> None:
        self._hovered = hovered
        self._apply_visual_state()

    def _apply_visual_state(self) -> None:
        if self._selected:
            self.setStyleSheet("border-radius: 4px; border-left: 4px solid #2f6feb; background-color: rgba(47,111,235,0.08);")
            self._thumb_label.setStyleSheet("border: 2px solid #2f6feb; border-radius: 3px;")
            self._name_label.setStyleSheet("font-weight: 600;")
        elif self._hovered:
            self.setStyleSheet("border-radius: 4px; border-left: 4px solid #94a3b8; background-color: rgba(148,163,184,0.10);")
            self._thumb_label.setStyleSheet("border: 2px solid #94a3b8; border-radius: 3px;")
            self._name_label.setStyleSheet("")
        else:
            self.setStyleSheet("border-radius: 4px; border-left: 4px solid transparent; background-color: transparent;")
            self._thumb_label.setStyleSheet("border: 2px solid transparent; border-radius: 3px;")
            self._name_label.setStyleSheet("")
        self.update()

    def mousePressEvent(self, event) -> None:
        self._on_select(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_select(self)
        self._on_activate(self)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        self._hover_panel.setText(self._build_stats_html())
        self._hover_panel.adjustSize()
        mw = self.window()
        global_pos = self.mapToGlobal(QPoint(self.width(), 0))
        local = mw.mapFromGlobal(global_pos)
        panel_w = self._hover_panel.sizeHint().width()
        panel_h = self._hover_panel.sizeHint().height()
        x = local.x() + 4
        if x + panel_w > mw.width():
            x = local.x() - self.width() - panel_w - 8
        y = max(0, min(local.y(), mw.height() - panel_h))
        self._hover_panel.move(x, y)
        self._hover_panel.show()
        self._hover_panel.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        self._hover_panel.hide()
        super().leaveEvent(event)

    def _build_stats_html(self) -> str:
        f = self._fav

        def make_row(label: str, value: str) -> str:
            return (
                f'<tr>'
                f'<td style="color:#6c7086;padding-right:8px;">{label}</td>'
                f'<td style="color:#cdd6f4;">{value}</td>'
                f'</tr>'
            )

        rows = [
            make_row("Formula", f["formula"]),
            make_row("Center", f"{f['center_x']:.6f}, {f['center_y']:.6f}"),
            make_row("Scale", f"{f['scale']:.8f}"),
            make_row("Iterations", str(f["max_iterations"])),
            make_row("Mode", f["coloring_mode"]),
            make_row("Julia", "Yes" if f["is_julia"] else "No"),
        ]
        if f["is_julia"]:
            rows.append(make_row("Julia c", f"{f['julia_real']:.4f}+{f['julia_imag']:.4f}i"))
        rows.append(make_row("Power", str(f["power"])))
        if f["formula"].lower() in ("phoenix",):
            rows.append(make_row("Phoenix", f"{f['phoenix_real']:.4f}+{f['phoenix_imag']:.4f}i"))
        if f["coloring_mode"].lower().startswith("orbit_trap"):
            rows.append(make_row("Trap pt", f"{f['trap_x']:.3f}, {f['trap_y']:.3f}"))

        return (
            '<table style="font-size:11px;font-family:monospace;white-space:nowrap;">'
            + "".join(rows)
            + "</table>"
        )


class PlaceholderPanel(QGroupBox):
    def __init__(self, title: str, lines: list[str]) -> None:
        super().__init__(title)
        layout = QVBoxLayout()
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.backend = load_backend()
        self.backend_loaded = self.backend.available
        self.backend_profile = self.backend.profile()
        self.editor: ColorCubeEditor | None = None
        self.viewport: FractalViewportWidget | None = None
        self.params_panel: FractalParamsPanel | None = None
        self.preview_palette: PalettePreviewWidget | None = None
        self.preview_legacy: PalettePreviewWidget | None = None
        self.point_summary: QLabel | None = None
        self.palette_summary: QLabel | None = None
        self.backend_state_label: QLabel | None = None
        self.viewport_hint_label: QLabel | None = None
        self._aspect_ratio_combo: QComboBox | None = None
        self._aspect_ratio_mode: str = "square"
        self._favorites: list[dict] = []
        self._export_combo: QComboBox | None = None
        self._export_presets: list[tuple[str, int, int]] = []
        self._custom_width: int = 1080
        self._custom_height: int = 1080
        self._custom_width_box: QSpinBox | None = None
        self._custom_height_box: QSpinBox | None = None
        self._selected_row: FavoriteThumbnailRow | None = None
        self._fav_rows: list[FavoriteThumbnailRow] = []
        self._fav_scroll_layout: QVBoxLayout | None = None

        self.setWindowTitle("Fractal Studio")
        self.resize(1500, 940)

        self._hover_panel = QLabel(self)
        self._hover_panel.setStyleSheet(
            "QLabel { background: #181825; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 8px 10px; }"
        )
        self._hover_panel.hide()

        self.setCentralWidget(self._build_layout())
        self.statusBar().showMessage(self._status_message())

    def _build_layout(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_workspace())
        splitter.addWidget(self._build_sidebar())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1200, 300])

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._build_header())
        layout.addWidget(splitter)
        container.setLayout(layout)
        return container

    def _build_header(self) -> QWidget:
        profile = self.backend_profile
        summary = QLabel(
            "Modern defaults: "
            f"{profile.palette_size}-sample internal palettes, "
            f"{profile.coloring_model} coloring, "
            f"{profile.render_strategy} rendering, "
            f"{profile.preview_width}x{profile.preview_height} preview."
        )
        summary.setWordWrap(True)
        summary.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(summary)
        container.setLayout(layout)
        return container

    def _build_workspace(self) -> QWidget:
        layout = QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.addWidget(self._build_viewport_panel(), 0, 0, 2, 1)
        layout.addWidget(self._build_palette_panel(), 0, 1)
        layout.addWidget(self._build_colormap_panel(), 1, 1)

        container = QWidget()
        container.setLayout(layout)
        return container

    def _build_sidebar(self) -> QWidget:
        layout = QVBoxLayout()

        self.params_panel = FractalParamsPanel()
        if self.viewport is not None:
            self.params_panel.formula_changed.connect(self.viewport.set_formula)
            self.params_panel.mode_changed.connect(self.viewport.set_mode)
            self.params_panel.power_changed.connect(self.viewport.set_power)
            self.params_panel.phoenix_changed.connect(self.viewport.set_phoenix_constant)
            self.params_panel.julia_constant_changed.connect(self.viewport.set_julia_constant)
            self.params_panel.max_iterations_changed.connect(self.viewport.set_max_iterations)
            self.params_panel.zoom_changed.connect(self.viewport.set_scale)
            self.viewport.scale_changed.connect(self.params_panel.set_scale)
            self.params_panel.coloring_mode_changed.connect(self.viewport.set_coloring_mode)
            self.params_panel.trap_point_changed.connect(self.viewport.set_trap_point)
            self.params_panel.cycle_toggled.connect(self.viewport.set_cycle_active)
            self.params_panel.cycle_speed_changed.connect(self.viewport.set_cycle_speed)

        layout.addWidget(self.params_panel)
        layout.addWidget(self._build_backend_panel())
        layout.addWidget(self._build_export_panel())
        favorites_panel = self._build_favorites_panel()
        layout.addWidget(favorites_panel, 1)

        container = QWidget()
        container.setLayout(layout)
        return container

    def _build_viewport_panel(self) -> QWidget:
        panel = QGroupBox("Fractal Viewport")
        layout = QVBoxLayout()

        aspect_row = QWidget()
        aspect_layout = QHBoxLayout()
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.addWidget(QLabel("Aspect ratio:"))
        self._aspect_ratio_combo = QComboBox()
        self._aspect_ratio_combo.addItems(["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"])
        self._aspect_ratio_combo.currentIndexChanged.connect(self._on_aspect_ratio_changed)
        aspect_layout.addWidget(self._aspect_ratio_combo, 1)
        aspect_row.setLayout(aspect_layout)

        self.viewport = FractalViewportWidget(self.backend)
        # Match right-column editor/previews default width so both columns start balanced.
        self.viewport.setMinimumWidth(520)
        self.viewport.status_changed.connect(self.statusBar().showMessage)

        self.viewport_hint_label = QLabel("Scroll to zoom  ·  drag to pan  ·  double-click to recenter")
        self.viewport_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport_hint_label.setStyleSheet("color: gray; font-size: 10px;")

        layout.addWidget(aspect_row)
        layout.addStretch()
        layout.addWidget(self.viewport)
        layout.addWidget(self.viewport_hint_label)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _build_palette_panel(self) -> QWidget:
        panel = QGroupBox("Palette Preview")
        layout = QVBoxLayout()

        self.preview_palette = PalettePreviewWidget("Internal palette preview")
        self.preview_legacy = PalettePreviewWidget("Legacy 256-color export preview")
        self.point_summary = QLabel("0 control points")
        self.palette_summary = QLabel("Add four control points to generate a palette.")
        self.point_summary.setWordWrap(True)
        self.palette_summary.setWordWrap(True)

        layout.addWidget(self.preview_palette)
        layout.addWidget(self.preview_legacy)
        layout.addWidget(self.point_summary)
        layout.addWidget(self.palette_summary)
        panel.setLayout(layout)
        return panel

    def _build_colormap_panel(self) -> QWidget:
        panel = QGroupBox("Colormap Editor")
        layout = QVBoxLayout()

        self.editor = ColorCubeEditor(self.backend, self.backend_profile)
        self.editor.palette_changed.connect(self._update_palette_previews)
        self.editor.control_points_changed.connect(self._update_control_summary)
        self.editor.status_changed.connect(self.statusBar().showMessage)
        if self.viewport is not None:
            self.editor.palette_changed.connect(self.viewport.set_palette)

        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.editor.clear_points)
        seed_button = QPushButton("Seed Sample")
        seed_button.clicked.connect(self.editor.seed_points)
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(self._save_palette_json)
        load_button = QPushButton("Load JSON")
        load_button.clicked.connect(self._load_palette_json)
        export_button = QPushButton("Export .map")
        export_button.clicked.connect(self._export_legacy_map)

        for button in (reset_button, seed_button, save_button, load_button, export_button):
            controls_layout.addWidget(button)
        controls_layout.addStretch()
        controls.setLayout(controls_layout)

        layout.addWidget(self.editor)
        layout.addWidget(controls)
        panel.setLayout(layout)

        self.editor.seed_points()
        return panel

    def _build_backend_panel(self) -> QWidget:
        panel = QGroupBox("Backend Profile")
        layout = QVBoxLayout()

        profile = self.backend_profile
        self.backend_state_label = QLabel()
        self.backend_state_label.setWordWrap(True)
        self.backend_state_label.setText(self._backend_state_text())

        for text in (
            f"Coloring model: {profile.coloring_model}",
            f"Render strategy: {profile.render_strategy}",
            f"Export presets: {', '.join(profile.export_presets)}",
            f"Internal palette size: {profile.palette_size}",
            f"Legacy export size: {profile.legacy_palette_size}",
        ):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)

        layout.insertWidget(0, self.backend_state_label)
        panel.setLayout(layout)
        return panel

    def _build_export_panel(self) -> QWidget:
        panel = QGroupBox("Export")
        layout = QVBoxLayout()

        top_row = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._export_combo = QComboBox()
        self._refresh_export_presets()

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._on_export_clicked)

        top_layout.addWidget(self._export_combo, 1)
        top_layout.addWidget(export_btn)
        top_row.setLayout(top_layout)

        custom_row = QWidget()
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.addWidget(QLabel("W:"))
        self._custom_width_box = QSpinBox()
        self._custom_width_box.setRange(64, 16384)
        self._custom_width_box.setValue(self._custom_width)
        custom_layout.addWidget(self._custom_width_box)
        custom_layout.addWidget(QLabel("H:"))
        self._custom_height_box = QSpinBox()
        self._custom_height_box.setRange(64, 16384)
        self._custom_height_box.setValue(self._custom_height)
        custom_layout.addWidget(self._custom_height_box)
        custom_layout.addStretch()
        custom_row.setLayout(custom_layout)

        self._export_combo.currentIndexChanged.connect(self._on_export_preset_changed)
        self._on_export_preset_changed(self._export_combo.currentIndex())

        self._apply_aspect_ratio_mode(self._aspect_ratio_mode, update_combo=False)

        layout.addWidget(top_row)
        layout.addWidget(custom_row)
        panel.setLayout(layout)
        return panel

    def _build_export_presets_for_mode(self, aspect_mode: str) -> list[tuple[str, int, int]]:
        preset_sizes = {
            "square": [(1080, 1080), (1440, 1440), (2160, 2160)],
            "portrait": [(1080, 1440), (1440, 1920), (2160, 2880)],
            "landscape": [(1440, 1080), (1920, 1440), (2880, 2160)],
        }
        sizes = preset_sizes.get(aspect_mode, preset_sizes["square"])
        return [(f"{width} × {height}", width, height) for width, height in sizes] + [("Custom…", 0, 0)]

    def _refresh_export_presets(self) -> None:
        if self._export_combo is None:
            return

        previous_index = self._export_combo.currentIndex()
        previous_is_custom = bool(self._export_presets) and previous_index == len(self._export_presets) - 1
        self._export_presets = self._build_export_presets_for_mode(self._aspect_ratio_mode)

        self._export_combo.blockSignals(True)
        self._export_combo.clear()
        for label, _, _ in self._export_presets:
            self._export_combo.addItem(label)
        if previous_is_custom:
            self._export_combo.setCurrentIndex(len(self._export_presets) - 1)
        else:
            self._export_combo.setCurrentIndex(max(0, min(previous_index, len(self._export_presets) - 1)))
        self._export_combo.blockSignals(False)
        self._on_export_preset_changed(self._export_combo.currentIndex())

    def _apply_aspect_ratio_mode(self, mode: str, update_combo: bool = True) -> None:
        if mode not in ("square", "portrait", "landscape"):
            mode = "square"

        self._aspect_ratio_mode = mode
        if self.viewport is not None:
            self.viewport.set_aspect_ratio_mode(mode)

        if update_combo and self._aspect_ratio_combo is not None:
            index = {"square": 0, "portrait": 1, "landscape": 2}[mode]
            self._aspect_ratio_combo.blockSignals(True)
            self._aspect_ratio_combo.setCurrentIndex(index)
            self._aspect_ratio_combo.blockSignals(False)

        self._refresh_export_presets()

    def _on_aspect_ratio_changed(self, index: int) -> None:
        modes = {0: "square", 1: "portrait", 2: "landscape"}
        self._apply_aspect_ratio_mode(modes.get(index, "square"), update_combo=False)

    def _on_export_preset_changed(self, index: int) -> None:
        if self._custom_width_box is None or self._custom_height_box is None:
            return
        is_custom = index == len(self._export_presets) - 1
        self._custom_width_box.parentWidget().setVisible(is_custom)

    def _on_export_clicked(self) -> None:
        if self._export_combo is None:
            return
        idx = self._export_combo.currentIndex()
        _, w, h = self._export_presets[idx]
        if w == 0:
            if self._custom_width_box is None or self._custom_height_box is None:
                return
            w = self._custom_width_box.value()
            h = self._custom_height_box.value()
            self._custom_width, self._custom_height = w, h
        self._export_render(w, h)

    def _export_render(self, width: int, height: int) -> None:
        if self.viewport is None or not self.backend.available:
            self.statusBar().showMessage("Backend not available.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {width}×{height} render",
            str(Path.cwd() / f"fractal_{width}x{height}.png"),
            "PNG Image (*.png)",
        )
        if not path:
            return

        self.statusBar().showMessage(f"Rendering {width}×{height}…")
        QApplication.processEvents()

        vp = self.viewport
        raw = self.backend.render_fractal(
            vp._formula, width, height,
            is_julia=vp._is_julia,
            julia_real=vp._julia_real,
            julia_imag=vp._julia_imag,
            power=vp._power,
            phoenix_real=vp._phoenix_real,
            phoenix_imag=vp._phoenix_imag,
            center_x=vp._center_x,
            center_y=vp._center_y,
            scale=vp._scale,
            max_iterations=vp._max_iterations,
            palette=vp._palette,
            coloring_mode=vp._coloring_mode,
            trap_x=vp._trap_x,
            trap_y=vp._trap_y,
            palette_offset=vp._palette_offset,
        )
        img = QImage(raw, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        img.save(path)
        self.statusBar().showMessage(f"Saved {width}×{height} render to {path}")

    def _build_favorites_panel(self) -> QWidget:
        panel = QGroupBox("Favorites")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout()

        self._fav_scroll_widget = QWidget()
        self._fav_scroll_layout = QVBoxLayout()
        self._fav_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._fav_scroll_layout.setSpacing(2)
        self._fav_scroll_layout.addStretch()
        self._fav_scroll_widget.setLayout(self._fav_scroll_layout)

        scroll = QScrollArea()
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(self._fav_scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._favorites = self._load_favorites_from_disk()
        for fav in self._favorites:
            self._add_favorite_row(fav)

        btn_row = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        save_fav_btn = QPushButton("Save")
        del_fav_btn = QPushButton("Delete")
        save_fav_btn.clicked.connect(self._save_favorite)
        del_fav_btn.clicked.connect(self._delete_favorite)
        for b in (save_fav_btn, del_fav_btn):
            btn_layout.addWidget(b)
        btn_row.setLayout(btn_layout)

        layout.addWidget(scroll)
        layout.addWidget(btn_row)
        panel.setLayout(layout)
        return panel

    def _add_favorite_row(self, fav: dict) -> None:
        if "thumbnail" in fav:
            try:
                pixmap = MainWindow._decode_thumbnail(fav["thumbnail"])
                if pixmap.isNull():
                    pixmap = MainWindow._placeholder_pixmap()
            except Exception:
                pixmap = MainWindow._placeholder_pixmap()
        else:
            pixmap = MainWindow._placeholder_pixmap()
        # Use a weakref to break the MainWindow ↔ FavoriteThumbnailRow reference cycle
        # so CPython's cyclic GC doesn't finalize Rust-backed objects at unsafe times.
        weak_self = weakref.ref(self)

        def on_select(row: FavoriteThumbnailRow) -> None:
            mw = weak_self()
            if mw is not None:
                mw._on_row_selected(row)

        def on_activate(row: FavoriteThumbnailRow) -> None:
            mw = weak_self()
            if mw is not None:
                mw._load_favorite_row(row)

        row = FavoriteThumbnailRow(pixmap, fav, self._hover_panel, on_select, on_activate)
        self._fav_rows.append(row)
        # Insert before the trailing stretch (always last item)
        self._fav_scroll_layout.insertWidget(len(self._fav_rows) - 1, row)

    def _on_row_selected(self, row: FavoriteThumbnailRow) -> None:
        if self._selected_row is not None:
            self._selected_row.set_selected(False)
        self._selected_row = row
        row.set_selected(True)

    def _save_favorite(self) -> None:
        if self.viewport is None:
            return
        vp = self.viewport
        control_points = self.editor.control_points if self.editor is not None else []
        palette_snapshot = [list(color) for color in vp._palette]
        name = self._build_favorite_name(vp)
        fav = {
            "id": str(uuid.uuid4()),
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "aspect_ratio_mode": self._aspect_ratio_mode,
            "name": name,
            "formula": vp._formula,
            "center_x": vp._center_x,
            "center_y": vp._center_y,
            "scale": vp._scale,
            "max_iterations": vp._max_iterations,
            "is_julia": vp._is_julia,
            "julia_real": vp._julia_real,
            "julia_imag": vp._julia_imag,
            "power": vp._power,
            "phoenix_real": vp._phoenix_real,
            "phoenix_imag": vp._phoenix_imag,
            "coloring_mode": vp._coloring_mode,
            "trap_x": vp._trap_x,
            "trap_y": vp._trap_y,
            "palette_offset": vp._palette_offset,
            "control_points": control_points,
            "palette": palette_snapshot,
            "thumbnail": self._capture_thumbnail(),
        }
        self._favorites.append(fav)
        self._add_favorite_row(fav)
        self._persist_favorites()
        self.statusBar().showMessage(f"Saved favorite: {name}")

    def _build_favorite_name(self, vp: FractalViewportWidget) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_name = f"{vp._formula} ({vp._center_x:.3f}, {vp._center_y:.3f}) {timestamp}"
        return self._make_unique_favorite_name(base_name)

    def _make_unique_favorite_name(self, base_name: str) -> str:
        existing_names = {fav.get("name", "") for fav in self._favorites}
        if base_name not in existing_names:
            return base_name

        suffix = 2
        while f"{base_name} ({suffix})" in existing_names:
            suffix += 1
        return f"{base_name} ({suffix})"

    def _load_favorite(self) -> None:
        if self.viewport is None or self.params_panel is None or self._selected_row is None:
            return
        self._load_favorite_row(self._selected_row)

    def _load_favorite_row(self, row: FavoriteThumbnailRow) -> None:
        if self.viewport is None or self.params_panel is None:
            return
        idx = self._fav_rows.index(row)
        fav = self._favorites[idx]
        vp = self.viewport
        vp._formula = fav["formula"]
        vp._center_x = fav["center_x"]
        vp._center_y = fav["center_y"]
        vp._scale = fav["scale"]
        vp._max_iterations = fav["max_iterations"]
        vp._is_julia = fav["is_julia"]
        vp._julia_real = fav["julia_real"]
        vp._julia_imag = fav["julia_imag"]
        vp._power = fav["power"]
        vp._phoenix_real = fav["phoenix_real"]
        vp._phoenix_imag = fav["phoenix_imag"]
        vp._coloring_mode = fav["coloring_mode"]
        vp._trap_x = fav.get("trap_x", 0.0)
        vp._trap_y = fav.get("trap_y", 0.0)
        vp._palette_offset = float(fav.get("palette_offset", 0.0)) % 1.0

        self._apply_aspect_ratio_mode(fav.get("aspect_ratio_mode", "square"))

        saved_palette = fav.get("palette", [])
        normalized_palette: list[tuple[int, int, int]] = []
        if isinstance(saved_palette, list):
            for color in saved_palette:
                if isinstance(color, (list, tuple)) and len(color) == 3:
                    try:
                        normalized_palette.append((int(color[0]), int(color[1]), int(color[2])))
                    except (TypeError, ValueError):
                        pass

        saved_points = fav.get("control_points")
        restored_points: list[tuple[int, int, int]] = []
        if isinstance(saved_points, list):
            normalized: list[tuple[int, int, int]] = []
            for point in saved_points:
                if isinstance(point, (list, tuple)) and len(point) == 3:
                    try:
                        normalized.append((int(point[0]), int(point[1]), int(point[2])))
                    except (TypeError, ValueError):
                        pass
            restored_points = normalized

        if self.editor is not None and restored_points:
            # Restore editor state first; this also updates preview/viewport palette.
            self.editor.set_control_points(restored_points)

        if normalized_palette and len(restored_points) < 4:
            # If control points are insufficient to regenerate a palette, restore exact saved colors.
            vp.set_palette(normalized_palette)
            if self.preview_palette is not None:
                self.preview_palette.set_palette(normalized_palette)

        self._sync_params_panel_from_favorite(fav)
        if vp._cycle_timer.isActive():
            vp._cycle_timer.stop()
        vp._cycle_active = False

        vp._rerender()
        self._on_row_selected(row)
        self.statusBar().showMessage(f"Restored: {fav['name']}")

    def _sync_params_panel_from_favorite(self, fav: dict) -> None:
        if self.params_panel is None:
            return
        p = self.params_panel
        widgets = [
            p._formula_combo,
            p._mode_combo,
            p._power_spin,
            p._phoenix_real_spin,
            p._phoenix_imag_spin,
            p._julia_real_spin,
            p._julia_imag_spin,
            p._iterations_spin,
            p._coloring_combo,
            p._trap_x_spin,
            p._trap_y_spin,
            p._cycle_button,
        ]
        for widget in widgets:
            widget.blockSignals(True)

        try:
            formula_index = 0
            for idx, (_, key) in enumerate(p._FORMULAS):
                if key == fav["formula"]:
                    formula_index = idx
                    break
            p._formula_combo.setCurrentIndex(formula_index)
            p._set_power_visible(fav["formula"] in ("multibrot", "newton"))
            p._set_phoenix_visible(fav["formula"] == "phoenix")
            p._set_mode_visible(fav["formula"] != "newton")

            p._mode_combo.setCurrentIndex(1 if fav["is_julia"] else 0)
            p._set_julia_visible(bool(fav["is_julia"]))
            p._power_spin.setValue(int(fav["power"]))
            p._phoenix_real_spin.setValue(float(fav["phoenix_real"]))
            p._phoenix_imag_spin.setValue(float(fav["phoenix_imag"]))
            p._julia_real_spin.setValue(float(fav["julia_real"]))
            p._julia_imag_spin.setValue(float(fav["julia_imag"]))
            p._iterations_spin.setValue(int(fav["max_iterations"]))

            color_index = p._coloring_combo.findData(fav["coloring_mode"])
            p._coloring_combo.setCurrentIndex(max(0, color_index))
            p._set_trap_point_visible(fav["coloring_mode"] == "orbit_trap_point")
            p._trap_x_spin.setValue(float(fav.get("trap_x", 0.0)))
            p._trap_y_spin.setValue(float(fav.get("trap_y", 0.0)))

            if p._cycle_button.isChecked():
                p._cycle_button.setChecked(False)
            p.set_scale(float(fav["scale"]))
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    def _delete_favorite(self) -> None:
        if self._selected_row is None:
            return
        idx = self._fav_rows.index(self._selected_row)
        self._favorites.pop(idx)
        row = self._fav_rows.pop(idx)
        self._fav_scroll_layout.removeWidget(row)
        row.deleteLater()
        self._selected_row = None
        self._persist_favorites()

    def _persist_favorites(self) -> None:
        _FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FAVORITES_PATH.write_text(json.dumps(self._favorites, indent=2))

    def _load_favorites_from_disk(self) -> list[dict]:
        try:
            return json.loads(_FAVORITES_PATH.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _update_control_summary(self, control_points: list[tuple[int, int, int]]) -> None:
        if self.point_summary is None:
            return

        self.point_summary.setText(f"{len(control_points)} control points")

    def _update_palette_previews(self, palette: list[tuple[int, int, int]]) -> None:
        if self.preview_palette is None or self.preview_legacy is None or self.palette_summary is None:
            return

        self.preview_palette.set_palette(palette)
        legacy_palette = (
            self.backend.generate_palette(self.editor.control_points, self.backend_profile.legacy_palette_size)
            if self.editor is not None and len(self.editor.control_points) >= 4 and self.backend.available
            else []
        )
        self.preview_legacy.set_palette(legacy_palette)

        if palette:
            self.palette_summary.setText(
                f"Generated {len(palette)} internal colors and {len(legacy_palette)} legacy export colors."
            )
        else:
            self.palette_summary.setText("Add four control points to generate a palette.")

    def _save_palette_json(self) -> None:
        if self.editor is None or not self.backend.available:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save palette",
            str(Path.cwd() / "palette.json"),
            "Fractal Studio Palette (*.json)",
        )
        if not path:
            return

        self.backend.export_palette_json(path, self.editor.control_points, self.backend_profile.palette_size)
        self.statusBar().showMessage(f"Saved palette to {path}")

    def _load_palette_json(self) -> None:
        if self.editor is None or not self.backend.available:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load palette",
            str(Path.cwd()),
            "Fractal Studio Palette (*.json)",
        )
        if not path:
            return

        palette_size, control_points = self.backend.import_palette_json(path)
        self.editor.set_control_points(control_points)
        self.statusBar().showMessage(
            f"Loaded palette with {len(control_points)} control points. Saved palette size was {palette_size}."
        )

    def _export_legacy_map(self) -> None:
        if self.editor is None or not self.backend.available or len(self.editor.control_points) < 4:
            self.statusBar().showMessage("Add at least four control points before exporting a legacy map.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export legacy palette",
            str(Path.cwd() / "palette.map"),
            "Legacy Palette (*.map)",
        )
        if not path:
            return

        palette = self.backend.generate_palette(self.editor.control_points, self.backend_profile.legacy_palette_size)
        self.backend.export_legacy_map(path, palette)
        self.statusBar().showMessage(f"Exported legacy palette to {path}")

    @staticmethod
    def _encode_pixmap(pixmap: QPixmap) -> str:
        scaled = pixmap.scaled(
            96, 72,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        scaled.toImage().save(buf, "PNG")
        buf.close()
        return base64.b64encode(bytes(ba)).decode()

    @staticmethod
    def _decode_thumbnail(b64: str) -> QPixmap:
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(b64))
        return pixmap

    @staticmethod
    def _placeholder_pixmap() -> QPixmap:
        pixmap = QPixmap(48, 36)
        pixmap.fill(QColor("#313244"))
        return pixmap

    def _capture_thumbnail(self) -> str:
        return MainWindow._encode_pixmap(self.viewport.grab())

    def _backend_state_text(self) -> str:
        return (
            "Rust extension loaded."
            if self.backend_loaded and self.backend.available
            else "Rust extension not loaded. Build fractal_core to enable the editor."
        )

    def _status_message(self) -> str:
        source = "Rust backend" if self.backend_loaded else "scaffold defaults"
        return f"Fractal Studio ready with {source}."
