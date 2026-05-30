from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from fractal_studio.ui.widgets.section_panel import SectionPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.integration
class TestSectionPanel:
    def test_title_label_text(self, app):
        panel = SectionPanel("My Panel")
        assert panel._title_label.text() == "MY PANEL"

    def test_tag_hidden_by_default(self, app):
        panel = SectionPanel("X")
        assert panel._tag_label.isHidden()

    def test_set_tag_shows_label(self, app):
        panel = SectionPanel("X")
        panel.set_tag("5 points")
        assert not panel._tag_label.isHidden()
        assert panel._tag_label.text() == "5 points"

    def test_non_collapsible_has_no_toggle(self, app):
        panel = SectionPanel("X", collapsible=False)
        assert panel._toggle_btn.isHidden()

    def test_collapsible_has_toggle(self, app):
        panel = SectionPanel("X", collapsible=True)
        assert not panel._toggle_btn.isHidden()

    def test_body_visible_when_not_collapsed(self, app):
        panel = SectionPanel("X", collapsible=True, collapsed=False)
        assert not panel._body_container.isHidden()

    def test_body_hidden_when_collapsed(self, app):
        panel = SectionPanel("X", collapsible=True, collapsed=True)
        assert panel._body_container.isHidden()

    def test_toggle_emits_signal(self, app):
        panel = SectionPanel("X", collapsible=True, collapsed=False)
        emitted = []
        panel.collapse_changed.connect(emitted.append)
        panel._toggle()
        assert emitted == [True]

    def test_toggle_twice_returns_to_expanded(self, app):
        panel = SectionPanel("X", collapsible=True, collapsed=False)
        panel._toggle()
        panel._toggle()
        assert not panel.is_collapsed()

    def test_set_collapsed_programmatic(self, app):
        panel = SectionPanel("X", collapsible=True, collapsed=False)
        panel.set_collapsed(True)
        assert panel.is_collapsed()
        assert panel._body_container.isHidden()

    def test_body_layout_accepts_children(self, app):
        panel = SectionPanel("X")
        panel.body_layout().addWidget(QLabel("child"))
        assert panel.body_layout().count() == 1

    def test_set_header_widget(self, app):
        panel = SectionPanel("X")
        w = QLabel("aspect")
        panel.set_header_widget(w)
        assert panel._extra_header_widget is w

    def test_non_collapsible_header_click_does_nothing(self, app):
        panel = SectionPanel("X", collapsible=False)
        emitted = []
        panel.collapse_changed.connect(emitted.append)
        panel._toggle()  # calling directly, header click not applicable
        assert emitted == []


@pytest.mark.integration
class TestViewportWellSizing:
    def test_well_height_for_width_matches_viewport(self, app):
        from fractal_studio.backend import load_backend
        from fractal_studio.theme import DARK_THEME
        from fractal_studio.ui.widgets.viewport_well import ViewportWell
        from fractal_studio.viewport import FractalViewportWidget
        from PySide6.QtWidgets import QLabel

        backend = load_backend()
        viewport = FractalViewportWidget(backend)
        hint = QLabel("hint")
        well = ViewportWell(viewport, DARK_THEME, hint)

        assert well.hasHeightForWidth()
        for w in (400, 600, 800):
            assert well.heightForWidth(w) == viewport.heightForWidth(w)

    def test_well_aspect_ratio_modes(self, app):
        from fractal_studio.backend import load_backend
        from fractal_studio.theme import DARK_THEME
        from fractal_studio.ui.widgets.viewport_well import ViewportWell
        from fractal_studio.viewport import FractalViewportWidget
        from PySide6.QtWidgets import QLabel

        backend = load_backend()
        viewport = FractalViewportWidget(backend)
        hint = QLabel("hint")
        well = ViewportWell(viewport, DARK_THEME, hint)

        for mode in ("square", "portrait", "landscape"):
            viewport.set_aspect_ratio_mode(mode)
            assert well.heightForWidth(600) == viewport.heightForWidth(600)
