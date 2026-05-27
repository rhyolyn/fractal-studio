from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.editor import ColorCubeEditor, PalettePreviewWidget
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget

if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile


class MainWindowSections:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

    def build_header(self, profile: BackendProfile, on_open_settings: Callable[[], None]) -> QWidget:
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
        settings_button = QToolButton()
        settings_button.setObjectName("settingsButton")
        settings_button.setText("⚙")
        settings_button.setToolTip("Settings")
        settings_button.clicked.connect(on_open_settings)
        layout.addWidget(settings_button)
        container.setLayout(layout)
        return container

    def build_viewport_panel(self) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Fractal Viewport")
        layout = QVBoxLayout()

        aspect_row = QWidget()
        aspect_layout = QHBoxLayout()
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.addWidget(QLabel("Aspect ratio:"))
        owner._aspect_ratio_combo = QComboBox()
        owner._aspect_ratio_combo.addItems(["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"])
        owner._aspect_ratio_combo.currentIndexChanged.connect(owner._on_aspect_ratio_changed)
        aspect_layout.addWidget(owner._aspect_ratio_combo, 1)
        aspect_row.setLayout(aspect_layout)

        owner.viewport = FractalViewportWidget(owner.backend)
        # Match right-column editor/previews default width so both columns start balanced.
        owner.viewport.setMinimumWidth(520)
        owner.viewport.status_changed.connect(owner.statusBar().showMessage)

        owner.viewport_hint_label = QLabel("Scroll to zoom  ·  drag to pan  ·  double-click to recenter")
        owner.viewport_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        owner.viewport_hint_label.setObjectName("viewportHint")

        layout.addWidget(aspect_row)
        layout.addStretch()
        layout.addWidget(owner.viewport)
        layout.addWidget(owner.viewport_hint_label)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def build_palette_panel(self) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Palette Preview")
        layout = QVBoxLayout()

        owner.preview_palette = PalettePreviewWidget("Internal palette preview")
        owner.preview_legacy = PalettePreviewWidget("Legacy 256-color export preview")
        owner.point_summary = QLabel("0 control points")
        owner.palette_summary = QLabel("Add four control points to generate a palette.")
        owner.point_summary.setWordWrap(True)
        owner.palette_summary.setWordWrap(True)

        layout.addWidget(owner.preview_palette)
        layout.addWidget(owner.preview_legacy)
        layout.addWidget(owner.point_summary)
        layout.addWidget(owner.palette_summary)
        panel.setLayout(layout)
        return panel

    def build_colormap_panel(self) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Colormap Editor")
        layout = QVBoxLayout()

        owner.editor = ColorCubeEditor(owner.backend, owner.backend_profile)
        owner.editor.palette_changed.connect(owner._update_palette_previews)
        owner.editor.control_points_changed.connect(owner._update_control_summary)
        owner.editor.status_changed.connect(owner.statusBar().showMessage)
        if owner.viewport is not None:
            owner.editor.palette_changed.connect(owner.viewport.set_palette)

        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(owner.editor.clear_points)
        seed_button = QPushButton("Seed Sample")
        seed_button.clicked.connect(owner.editor.seed_points)
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(owner._save_palette_json)
        load_button = QPushButton("Load JSON")
        load_button.clicked.connect(owner._load_palette_json)
        export_button = QPushButton("Export .map")
        export_button.clicked.connect(owner._export_legacy_map)

        for button in (reset_button, seed_button, save_button, load_button, export_button):
            controls_layout.addWidget(button)
        controls_layout.addStretch()
        controls.setLayout(controls_layout)

        layout.addWidget(owner.editor)
        layout.addWidget(controls)
        panel.setLayout(layout)

        owner.editor.seed_points()
        return panel

    def build_backend_panel(self, profile: BackendProfile, backend_state_text: str) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Backend Profile")
        layout = QVBoxLayout()

        owner.backend_state_label = QLabel()
        owner.backend_state_label.setWordWrap(True)
        owner.backend_state_label.setText(backend_state_text)

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

        layout.insertWidget(0, owner.backend_state_label)
        panel.setLayout(layout)
        return panel

    def build_export_panel(self) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Export")
        layout = QVBoxLayout()

        top_row = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        owner._export_combo = QComboBox()
        owner._refresh_export_presets()

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(owner._on_export_clicked)

        top_layout.addWidget(owner._export_combo, 1)
        top_layout.addWidget(export_btn)
        top_row.setLayout(top_layout)

        custom_row = QWidget()
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.addWidget(QLabel("W:"))
        owner._custom_width_box = QSpinBox()
        owner._custom_width_box.setRange(64, 16384)
        owner._custom_width_box.setValue(owner._custom_width)
        custom_layout.addWidget(owner._custom_width_box)
        custom_layout.addWidget(QLabel("H:"))
        owner._custom_height_box = QSpinBox()
        owner._custom_height_box.setRange(64, 16384)
        owner._custom_height_box.setValue(owner._custom_height)
        custom_layout.addWidget(owner._custom_height_box)
        custom_layout.addStretch()
        custom_row.setLayout(custom_layout)

        owner._export_combo.currentIndexChanged.connect(owner._on_export_preset_changed)
        owner._on_export_preset_changed(owner._export_combo.currentIndex())

        owner._apply_aspect_ratio_mode(owner._aspect_ratio_mode, update_combo=False)

        layout.addWidget(top_row)
        layout.addWidget(custom_row)
        panel.setLayout(layout)
        return panel

    def build_favorites_panel(self) -> QWidget:
        owner = self._owner
        panel = QGroupBox("Favorites")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout()

        owner._fav_scroll_widget = QWidget()
        owner._fav_scroll_layout = QVBoxLayout()
        owner._fav_scroll_layout.setContentsMargins(0, 0, 0, 0)
        owner._fav_scroll_layout.setSpacing(2)
        owner._fav_scroll_layout.addStretch()
        owner._fav_scroll_widget.setLayout(owner._fav_scroll_layout)

        scroll = QScrollArea()
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(owner._fav_scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        owner._favorites = owner._favorites_controller.load_favorites(owner._favorites_repo.load)
        for fav in owner._favorites:
            owner._add_favorite_row(fav)

        btn_row = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        save_fav_btn = QPushButton("Save")
        del_fav_btn = QPushButton("Delete")
        save_fav_btn.clicked.connect(owner._save_favorite)
        del_fav_btn.clicked.connect(owner._delete_favorite)
        for button in (save_fav_btn, del_fav_btn):
            btn_layout.addWidget(button)
        btn_row.setLayout(btn_layout)

        layout.addWidget(scroll)
        layout.addWidget(btn_row)
        panel.setLayout(layout)
        return panel

    def build_workspace(self) -> QWidget:
        owner = self._owner
        layout = QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.addWidget(self.build_viewport_panel(), 0, 0, 2, 1)
        layout.addWidget(self.build_palette_panel(), 0, 1)
        layout.addWidget(self.build_colormap_panel(), 1, 1)

        container = QWidget()
        container.setLayout(layout)
        return container

    def build_sidebar(self) -> QWidget:
        owner = self._owner
        layout = QVBoxLayout()

        owner.params_panel = FractalParamsPanel()
        if owner.viewport is not None:
            owner.params_panel.formula_changed.connect(owner.viewport.set_formula)
            owner.params_panel.mode_changed.connect(owner.viewport.set_mode)
            owner.params_panel.power_changed.connect(owner.viewport.set_power)
            owner.params_panel.phoenix_changed.connect(owner.viewport.set_phoenix_constant)
            owner.params_panel.julia_constant_changed.connect(owner.viewport.set_julia_constant)
            owner.params_panel.max_iterations_changed.connect(owner.viewport.set_max_iterations)
            owner.params_panel.zoom_changed.connect(owner.viewport.set_scale)
            owner.viewport.scale_changed.connect(owner.params_panel.set_scale)
            owner.params_panel.coloring_mode_changed.connect(owner.viewport.set_coloring_mode)
            owner.params_panel.trap_point_changed.connect(owner.viewport.set_trap_point)
            owner.params_panel.cycle_toggled.connect(owner.viewport.set_cycle_active)
            owner.params_panel.cycle_speed_changed.connect(owner.viewport.set_cycle_speed)

        layout.addWidget(owner.params_panel)
        layout.addWidget(
            self.build_backend_panel(
                owner.backend_profile,
                owner._settings_service.backend_state_message(owner.backend_loaded, owner.backend.available),
            )
        )
        layout.addWidget(self.build_export_panel())
        favorites_panel = self.build_favorites_panel()
        layout.addWidget(favorites_panel, 1)

        container = QWidget()
        container.setLayout(layout)
        return container
