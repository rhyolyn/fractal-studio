from __future__ import annotations

import datetime
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
from fractal_studio.thumbnail_utils import encode_pixmap
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
        owner._aspect_ratio_combo.currentIndexChanged.connect(
            lambda index: owner._export_panel.on_aspect_ratio_changed(
                index=index,
                apply_aspect_ratio_mode=owner._apply_aspect_ratio_mode,
            )
        )
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
        owner.editor.palette_changed.connect(
            lambda palette: owner._palette_preview.update_palette_previews(
                palette=palette,
                editor=owner.editor,
                backend=owner.backend,
                legacy_palette_size=owner.backend_profile.legacy_palette_size,
                preview_palette=owner.preview_palette,
                preview_legacy=owner.preview_legacy,
                palette_summary=owner.palette_summary,
            )
        )
        owner.editor.control_points_changed.connect(
            lambda points: owner._palette_preview.update_control_summary(owner.point_summary, points)
        )
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
        save_button.clicked.connect(
            lambda: owner._favorites_workflow.save_favorite(
                viewport=owner.viewport,
                editor=owner.editor,
                aspect_ratio_mode=owner._aspect_ratio_mode,
                favorites=owner._favorites,
                build_name=lambda state: owner._favorites_workflow.build_favorite_name(
                    state=state,
                    favorites=owner._favorites,
                    now=datetime.datetime.now,
                ),
                capture_thumbnail=lambda: encode_pixmap(owner.viewport.grab()),
                add_favorite=owner._favorites.append,
                add_row=owner._add_favorite_row,
                persist_favorites=lambda: owner._favorites_controller.persist_favorites(
                    owner._favorites,
                    owner._favorites_repo.save,
                ),
                show_status=owner.statusBar().showMessage,
            )
        )
        load_button = QPushButton("Load JSON")
        load_button.clicked.connect(
            lambda: owner._palette_panel.load_palette_json(
                parent=owner,
                editor=owner.editor,
                backend=owner.backend,
                set_status=owner.statusBar().showMessage,
            )
        )
        export_button = QPushButton("Export .map")
        export_button.clicked.connect(
            lambda: owner._palette_panel.export_legacy_map(
                parent=owner,
                editor=owner.editor,
                backend=owner.backend,
                legacy_palette_size=owner.backend_profile.legacy_palette_size,
                set_status=owner.statusBar().showMessage,
            )
        )

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
        owner._export_presets = owner._export_panel.refresh_export_presets(
            aspect_ratio_mode=owner._aspect_ratio_mode,
            export_combo=owner._export_combo,
            current_presets=owner._export_presets,
            on_export_preset_changed=lambda index: owner._export_panel.on_export_preset_changed(
                index=index,
                export_presets=owner._export_presets,
                custom_width_box=owner._custom_width_box,
                custom_height_box=owner._custom_height_box,
                set_custom_row_visible=lambda visible: owner._custom_width_box.parentWidget().setVisible(visible),
            ),
        )

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(
            lambda: owner._export_panel.on_export_clicked(
                export_presets=owner._export_presets,
                export_combo=owner._export_combo,
                custom_width_box=owner._custom_width_box,
                custom_height_box=owner._custom_height_box,
                set_custom_size=lambda w, h: setattr(owner, "_custom_width", w)
                or setattr(owner, "_custom_height", h),
                export_callback=lambda width, height: owner._controller.export_render(
                    owner,
                    owner.viewport,
                    width,
                    height,
                    owner.statusBar().showMessage,
                ),
            )
        )

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

        owner._export_combo.currentIndexChanged.connect(
            lambda index: owner._export_panel.on_export_preset_changed(
                index=index,
                export_presets=owner._export_presets,
                custom_width_box=owner._custom_width_box,
                custom_height_box=owner._custom_height_box,
                set_custom_row_visible=lambda visible: owner._custom_width_box.parentWidget().setVisible(visible),
            )
        )
        owner._export_panel.on_export_preset_changed(
            index=owner._export_combo.currentIndex(),
            export_presets=owner._export_presets,
            custom_width_box=owner._custom_width_box,
            custom_height_box=owner._custom_height_box,
            set_custom_row_visible=lambda visible: owner._custom_width_box.parentWidget().setVisible(visible),
        )

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
        save_fav_btn.clicked.connect(
            lambda: owner._favorites_workflow.save_favorite(
                viewport=owner.viewport,
                editor=owner.editor,
                aspect_ratio_mode=owner._aspect_ratio_mode,
                favorites=owner._favorites,
                build_name=lambda state: owner._favorites_workflow.build_favorite_name(
                    state=state,
                    favorites=owner._favorites,
                    now=datetime.datetime.now,
                ),
                capture_thumbnail=lambda: encode_pixmap(owner.viewport.grab()),
                add_favorite=owner._favorites.append,
                add_row=owner._add_favorite_row,
                persist_favorites=lambda: owner._favorites_controller.persist_favorites(
                    owner._favorites,
                    owner._favorites_repo.save,
                ),
                show_status=owner.statusBar().showMessage,
            )
        )
        del_fav_btn = QPushButton("Delete")
        del_fav_btn.clicked.connect(
            lambda: setattr(
                owner,
                "_selected_row",
                owner._favorites_workflow.delete_selected_favorite(
                    selected_row=owner._selected_row,
                    rows=owner._fav_rows,
                    favorites=owner._favorites,
                    scroll_layout=owner._fav_scroll_layout,
                    persist_favorites=lambda: owner._favorites_controller.persist_favorites(
                        owner._favorites,
                        owner._favorites_repo.save,
                    ),
                ),
            )
        )
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
        owner._sidebar_wiring.connect_params_and_viewport(owner.params_panel, owner.viewport)

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
