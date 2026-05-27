from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

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
    from fractal_studio.main_window_sections_mediator import MainWindowSectionsMediator


class MainWindowSections:
    def __init__(self, mediator: MainWindowSectionsMediator) -> None:
        self._mediator = mediator

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
        mediator = self._mediator
        panel = QGroupBox("Fractal Viewport")
        layout = QVBoxLayout()

        aspect_row = QWidget()
        aspect_layout = QHBoxLayout()
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.addWidget(QLabel("Aspect ratio:"))
        aspect_ratio_combo = QComboBox()
        aspect_ratio_combo.addItems(["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"])
        aspect_ratio_combo.currentIndexChanged.connect(mediator.on_aspect_ratio_changed)
        mediator.set_aspect_ratio_combo(aspect_ratio_combo)
        aspect_layout.addWidget(aspect_ratio_combo, 1)
        aspect_row.setLayout(aspect_layout)

        viewport = FractalViewportWidget(mediator.backend)
        # Match right-column editor/previews default width so both columns start balanced.
        viewport.setMinimumWidth(520)
        viewport.status_changed.connect(mediator.show_status)
        mediator.set_viewport(viewport)

        viewport_hint_label = QLabel("Scroll to zoom  ·  drag to pan  ·  double-click to recenter")
        viewport_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewport_hint_label.setObjectName("viewportHint")
        mediator.set_viewport_hint_label(viewport_hint_label)

        layout.addWidget(aspect_row)
        layout.addStretch()
        layout.addWidget(viewport)
        layout.addWidget(viewport_hint_label)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def build_palette_panel(self) -> QWidget:
        mediator = self._mediator
        panel = QGroupBox("Palette Preview")
        layout = QVBoxLayout()

        preview_palette = PalettePreviewWidget("Internal palette preview")
        preview_legacy = PalettePreviewWidget("Legacy 256-color export preview")
        point_summary = QLabel("0 control points")
        palette_summary = QLabel("Add four control points to generate a palette.")
        point_summary.setWordWrap(True)
        palette_summary.setWordWrap(True)

        mediator.set_preview_widgets(preview_palette, preview_legacy)
        mediator.set_palette_summary_labels(point_summary, palette_summary)

        layout.addWidget(preview_palette)
        layout.addWidget(preview_legacy)
        layout.addWidget(point_summary)
        layout.addWidget(palette_summary)
        panel.setLayout(layout)
        return panel

    def build_colormap_panel(self) -> QWidget:
        mediator = self._mediator
        panel = QGroupBox("Colormap Editor")
        layout = QVBoxLayout()

        editor = ColorCubeEditor(mediator.backend, mediator.backend_profile)
        editor.palette_changed.connect(mediator.update_palette_previews)
        editor.control_points_changed.connect(mediator.update_control_summary)
        editor.status_changed.connect(mediator.show_status)
        if mediator.viewport is not None:
            editor.palette_changed.connect(mediator.viewport.set_palette)
        mediator.set_editor(editor)

        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(editor.clear_points)
        seed_button = QPushButton("Seed Sample")
        seed_button.clicked.connect(editor.seed_points)
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(mediator.save_favorite)
        load_button = QPushButton("Load JSON")
        load_button.clicked.connect(mediator.load_palette_json)
        export_button = QPushButton("Export .map")
        export_button.clicked.connect(mediator.export_legacy_map)

        for button in (reset_button, seed_button, save_button, load_button, export_button):
            controls_layout.addWidget(button)
        controls_layout.addStretch()
        controls.setLayout(controls_layout)

        layout.addWidget(editor)
        layout.addWidget(controls)
        panel.setLayout(layout)

        editor.seed_points()
        return panel

    def build_backend_panel(self, profile: BackendProfile, backend_state_text: str) -> QWidget:
        mediator = self._mediator
        panel = QGroupBox("Backend Profile")
        layout = QVBoxLayout()

        backend_state_label = QLabel()
        backend_state_label.setWordWrap(True)
        backend_state_label.setText(backend_state_text)
        mediator.set_backend_state_label(backend_state_label)

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

        layout.insertWidget(0, backend_state_label)
        panel.setLayout(layout)
        return panel

    def build_export_panel(self) -> QWidget:
        mediator = self._mediator
        panel = QGroupBox("Export")
        layout = QVBoxLayout()

        top_row = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        export_combo = QComboBox()
        mediator.refresh_export_presets(export_combo)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(mediator.on_export_clicked)

        top_layout.addWidget(export_combo, 1)
        top_layout.addWidget(export_btn)
        top_row.setLayout(top_layout)

        custom_row = QWidget()
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.addWidget(QLabel("W:"))
        custom_width_box = QSpinBox()
        custom_width_box.setRange(64, 16384)
        custom_width, custom_height = mediator.custom_size_values()
        custom_width_box.setValue(custom_width)
        custom_layout.addWidget(custom_width_box)
        custom_layout.addWidget(QLabel("H:"))
        custom_height_box = QSpinBox()
        custom_height_box.setRange(64, 16384)
        custom_height_box.setValue(custom_height)
        custom_layout.addWidget(custom_height_box)
        custom_layout.addStretch()
        custom_row.setLayout(custom_layout)
        mediator.set_custom_size_boxes(custom_width_box, custom_height_box)

        export_combo.currentIndexChanged.connect(mediator.on_export_preset_changed)
        mediator.on_export_preset_changed(export_combo.currentIndex())

        mediator.apply_aspect_ratio_mode(update_combo=False)

        layout.addWidget(top_row)
        layout.addWidget(custom_row)
        panel.setLayout(layout)
        return panel

    def build_favorites_panel(self) -> QWidget:
        mediator = self._mediator
        panel = QGroupBox("Favorites")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout()

        fav_scroll_widget = QWidget()
        fav_scroll_layout = QVBoxLayout()
        fav_scroll_layout.setContentsMargins(0, 0, 0, 0)
        fav_scroll_layout.setSpacing(2)
        fav_scroll_layout.addStretch()
        fav_scroll_widget.setLayout(fav_scroll_layout)
        mediator.set_favorites_scroll_container(fav_scroll_widget, fav_scroll_layout)

        scroll = QScrollArea()
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(fav_scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for favorite in mediator.load_favorites():
            mediator.add_favorite_row(favorite)

        btn_row = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        save_fav_btn = QPushButton("Save")
        save_fav_btn.clicked.connect(mediator.save_favorite)
        del_fav_btn = QPushButton("Delete")
        del_fav_btn.clicked.connect(mediator.delete_selected_favorite)
        for button in (save_fav_btn, del_fav_btn):
            btn_layout.addWidget(button)
        btn_row.setLayout(btn_layout)

        layout.addWidget(scroll)
        layout.addWidget(btn_row)
        panel.setLayout(layout)
        return panel

    def build_workspace(self) -> QWidget:
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
        mediator = self._mediator
        layout = QVBoxLayout()

        params_panel = FractalParamsPanel()
        mediator.set_params_panel(params_panel)
        mediator.connect_params_and_viewport()

        layout.addWidget(params_panel)
        layout.addWidget(
            self.build_backend_panel(
                mediator.backend_profile,
                mediator.backend_state_message(),
            )
        )
        layout.addWidget(self.build_export_panel())
        favorites_panel = self.build_favorites_panel()
        layout.addWidget(favorites_panel, 1)

        container = QWidget()
        container.setLayout(layout)
        return container
