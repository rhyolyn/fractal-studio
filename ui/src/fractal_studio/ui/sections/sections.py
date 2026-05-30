from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
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
from fractal_studio.theme import ThemeSpec, get_theme
from fractal_studio.ui.widgets.section_panel import SectionPanel
from fractal_studio.ui.widgets.viewport_well import ViewportWell
from fractal_studio.viewport import FractalParamsPanel, FractalViewportWidget

if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile
    from fractal_studio.ui.sections.ports import (
        MainWindowSectionsPorts,
    )


class MainWindowSections:
    def __init__(self, ports: MainWindowSectionsPorts) -> None:
        self._ports = ports
        self._theme: ThemeSpec | None = None
        self._viewport_well: ViewportWell | None = None

    def set_theme(self, spec: ThemeSpec) -> None:
        self._theme = spec

    @property
    def viewport_well(self) -> ViewportWell | None:
        return self._viewport_well

    def build_header(
        self, profile: BackendProfile, on_open_settings: Callable[[], None]
    ) -> QWidget:
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
        ports = self._ports.viewport
        panel = SectionPanel("Fractal Viewport", collapsible=False)

        aspect_row = QWidget()
        aspect_layout = QHBoxLayout()
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.addWidget(QLabel("Aspect:"))
        aspect_ratio_combo = QComboBox()
        aspect_ratio_combo.addItems(
            ["Square (1:1)", "Portrait (3:4)", "Landscape (4:3)"]
        )
        aspect_ratio_combo.currentIndexChanged.connect(ports.on_aspect_ratio_changed)
        ports.set_aspect_ratio_combo(aspect_ratio_combo)
        aspect_layout.addWidget(aspect_ratio_combo)
        aspect_row.setLayout(aspect_layout)
        panel.set_header_widget(aspect_row)

        viewport = FractalViewportWidget(ports.backend)
        viewport.setMinimumWidth(520)
        viewport.status_changed.connect(ports.show_status)
        ports.set_viewport(viewport)

        hint_label = QLabel(
            "Scroll to zoom  ·  drag to pan  ·  double-click to recenter"
        )
        hint_label.setObjectName("viewportHint")
        ports.set_viewport_hint_label(hint_label)

        theme = self._theme if self._theme is not None else get_theme("light")
        well = ViewportWell(viewport, theme, hint_label)
        self._viewport_well = well

        panel.body_layout().setContentsMargins(0, 0, 0, 0)  # ViewportWell bleeds edge-to-edge
        panel.body_layout().addWidget(well)
        return panel

    def build_palette_panel(self) -> QWidget:
        ports = self._ports.palette
        panel = SectionPanel("Palette Preview", collapsible=False)

        preview_palette = PalettePreviewWidget("Internal palette preview")
        preview_legacy = PalettePreviewWidget("Legacy 256-color export preview")
        point_summary = QLabel("0 control points")
        palette_summary = QLabel("Add four control points to generate a palette.")
        point_summary.setWordWrap(True)
        palette_summary.setWordWrap(True)

        ports.set_preview_widgets(preview_palette, preview_legacy)
        ports.set_palette_summary_labels(point_summary, palette_summary)

        panel.body_layout().addWidget(preview_palette)
        panel.body_layout().addWidget(preview_legacy)
        panel.body_layout().addWidget(point_summary)
        panel.body_layout().addWidget(palette_summary)
        return panel

    def build_colormap_panel(self) -> QWidget:
        ports = self._ports.colormap
        panel = SectionPanel("Colormap Editor", collapsible=False)

        editor = ColorCubeEditor(ports.backend, ports.backend_profile)
        editor.palette_changed.connect(ports.update_palette_previews)
        editor.control_points_changed.connect(ports.update_control_summary)
        editor.status_changed.connect(ports.show_status)
        if ports.viewport is not None:
            editor.palette_changed.connect(ports.viewport.set_palette)
        ports.set_editor(editor)

        controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addStretch()

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(editor.clear_points)
        seed_button = QPushButton("Seed Sample")
        seed_button.clicked.connect(editor.seed_points)
        save_button = QPushButton("Save JSON")
        save_button.clicked.connect(ports.save_favorite)
        load_button = QPushButton("Load JSON")
        load_button.clicked.connect(ports.load_palette_json)
        export_button = QPushButton("Export .map")
        export_button.clicked.connect(ports.export_legacy_map)

        for button in (reset_button, seed_button, save_button, load_button, export_button):
            controls_layout.addWidget(button)
        controls_layout.addStretch()
        controls.setLayout(controls_layout)

        panel.body_layout().addWidget(editor)
        panel.body_layout().addWidget(controls)

        editor.seed_points()
        return panel

    def _build_export_section(self, collapsed: bool) -> SectionPanel:
        ports = self._ports.export
        panel = SectionPanel("Export", collapsible=True, collapsed=collapsed)
        # Build custom row first so spinboxes are registered before preset init signals fire.
        custom_row = self._build_export_custom_row(ports)
        panel.body_layout().addWidget(custom_row)
        panel.set_header_widget(self._build_export_action_row(ports))
        ports.on_export_preset_changed(0)  # initialise with default combo index
        ports.apply_aspect_ratio_mode(update_combo=False)
        return panel

    def _build_export_action_row(self, ports) -> QWidget:
        export_combo = QComboBox()
        ports.refresh_export_presets(export_combo)
        export_combo.currentIndexChanged.connect(ports.on_export_preset_changed)

        export_btn = QPushButton("Export")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(ports.on_export_clicked)

        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(export_combo, 1)
        layout.addWidget(export_btn)
        row.setLayout(layout)

        return row

    def _build_export_custom_row(self, ports) -> QWidget:
        custom_width, custom_height = ports.custom_size_values()

        custom_width_box = QSpinBox()
        custom_width_box.setRange(64, 16384)
        custom_width_box.setValue(custom_width)

        custom_height_box = QSpinBox()
        custom_height_box.setRange(64, 16384)
        custom_height_box.setValue(custom_height)

        ports.set_custom_size_boxes(custom_width_box, custom_height_box)

        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("W:"))
        layout.addWidget(custom_width_box)
        layout.addWidget(QLabel("H:"))
        layout.addWidget(custom_height_box)
        layout.addStretch()
        row.setLayout(layout)
        return row

    def _build_favorites_section(self, collapsed: bool) -> SectionPanel:
        ports = self._ports.favorites
        panel = SectionPanel("Favorites", collapsible=True, collapsed=collapsed)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel.body_layout().addWidget(self._build_favorites_scroll(ports))
        panel.body_layout().addWidget(self._build_favorites_buttons(ports))
        return panel

    def _build_favorites_scroll(self, ports) -> QScrollArea:
        fav_scroll_widget = QWidget()
        fav_scroll_layout = QVBoxLayout()
        fav_scroll_layout.setContentsMargins(0, 0, 0, 0)
        fav_scroll_layout.setSpacing(2)
        fav_scroll_layout.addStretch()
        fav_scroll_widget.setLayout(fav_scroll_layout)
        ports.set_favorites_scroll_container(fav_scroll_widget, fav_scroll_layout)

        for favorite in ports.load_favorites():
            ports.add_favorite_row(favorite)

        scroll = QScrollArea()
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(fav_scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll

    def _build_favorites_buttons(self, ports) -> QWidget:
        save_fav_btn = QPushButton("Save")
        save_fav_btn.setObjectName("primaryButton")
        save_fav_btn.clicked.connect(ports.save_favorite)
        del_fav_btn = QPushButton("Delete")
        del_fav_btn.clicked.connect(ports.delete_selected_favorite)

        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(save_fav_btn)
        layout.addWidget(del_fav_btn)
        row.setLayout(layout)
        return row

    def build_workspace(self) -> QWidget:
        layout = QGridLayout()
        layout.setSpacing(2)   # visible gap between panels acts as separator line
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

    def build_sidebar(
        self,
        sidebar_collapsed: dict[str, bool] | None = None,
        on_section_collapsed: Callable[[str, bool], None] | None = None,
    ) -> QWidget:
        collapsed = sidebar_collapsed or {}
        ports = self._ports.sidebar
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Parameters (always expanded, not persisted)
        params_section = SectionPanel(
            "Fractal Parameters", collapsible=True, collapsed=False
        )
        params_section.body_layout().setContentsMargins(8, 12, 8, 8)
        params_panel = FractalParamsPanel()
        ports.set_params_panel(params_panel)
        ports.connect_params_and_viewport()
        params_section.body_layout().addWidget(params_panel)
        layout.addWidget(params_section)

        # Export (collapsed by default, persisted)
        export_section = self._build_export_section(collapsed.get("export", True))
        if on_section_collapsed is not None:
            export_section.collapse_changed.connect(
                lambda c, key="export": on_section_collapsed(key, c)
            )
        layout.addWidget(export_section)

        # Favorites (expanded by default, persisted)
        favorites_section = self._build_favorites_section(collapsed.get("favorites", False))
        if on_section_collapsed is not None:
            favorites_section.collapse_changed.connect(
                lambda c, key="favorites": on_section_collapsed(key, c)
            )
        layout.addWidget(favorites_section, 1)

        container = QWidget()
        container.setLayout(layout)
        return container
