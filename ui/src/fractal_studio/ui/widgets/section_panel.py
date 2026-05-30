from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fractal_studio.theme import ThemeSpec


class _SectionHeader(QWidget):
    """Header row for SectionPanel. Emits clicked when pressed anywhere."""

    clicked = Signal()

    def __init__(self, collapsible: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._collapsible = collapsible
        if collapsible:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._collapsible:
            self.clicked.emit()
        super().mousePressEvent(event)


class SectionPanel(QWidget):
    collapse_changed = Signal(bool)

    def __init__(
        self,
        title: str,
        *,
        collapsible: bool = False,
        collapsed: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._collapsible = collapsible
        self._collapsed = collapsed if collapsible else False
        self._extra_header_widget: QWidget | None = None
        self._build_ui(title)
        self._apply_collapse()
        self.show()

    # --- public API ---

    def body_layout(self) -> QVBoxLayout:
        return self._body_container.layout()  # type: ignore[return-value]

    def set_tag(self, text: str) -> None:
        self._tag_label.setText(text)
        self._tag_label.setVisible(bool(text))

    def set_header_widget(self, widget: QWidget) -> None:
        """Place an arbitrary widget right-aligned in the header, before the chevron."""
        self._extra_header_widget = widget
        self._header_layout.insertWidget(
            self._header_layout.count() - 1,  # insert before toggle button
            widget,
        )

    def set_collapsed(self, collapsed: bool) -> None:
        if not self._collapsible:
            return
        self._collapsed = collapsed
        self._apply_collapse()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_theme(self, spec: ThemeSpec) -> None:  # noqa: ARG002
        pass  # colours applied via QSS — no per-instance work needed

    # --- private ---

    def _build_ui(self, title: str) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header(title))
        outer.addWidget(self._build_body())
        self.setLayout(outer)

    def _build_header(self, title: str) -> _SectionHeader:
        self._header = _SectionHeader(self._collapsible)
        self._header.setObjectName("sectionHeader")
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self._collapsible:
            self._header.clicked.connect(self._toggle)

        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(14, 9, 14, 9)
        self._header_layout.setSpacing(8)

        self._title_label = QLabel(title.upper())
        self._title_label.setObjectName("sectionTitle")
        self._header_layout.addWidget(self._title_label)

        self._tag_label = QLabel()
        self._tag_label.setObjectName("sectionTag")
        self._tag_label.setVisible(False)
        self._header_layout.addWidget(self._tag_label)

        self._header_layout.addStretch()

        self._toggle_btn = QToolButton()
        self._toggle_btn.setObjectName("sectionToggle")
        self._toggle_btn.setAutoRaise(True)
        self._toggle_btn.setVisible(self._collapsible)
        self._toggle_btn.clicked.connect(self._toggle)
        self._header_layout.addWidget(self._toggle_btn)

        self._header.setLayout(self._header_layout)
        return self._header

    def _build_body(self) -> QWidget:
        self._body_container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        self._body_container.setLayout(layout)
        return self._body_container

    def _toggle(self) -> None:
        if not self._collapsible:
            return
        self._collapsed = not self._collapsed
        self._apply_collapse()
        self.collapse_changed.emit(self._collapsed)

    def _apply_collapse(self) -> None:
        self._body_container.setVisible(not self._collapsed)
        self._toggle_btn.setText("▸" if self._collapsed else "▾")
