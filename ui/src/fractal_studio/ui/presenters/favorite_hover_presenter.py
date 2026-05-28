from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QWidget

from fractal_studio.theme import get_theme


class FavoriteHoverPresenter:
    def show_for_row(self, row: QWidget, hover_panel: QLabel, favorite: dict) -> None:
        hover_panel.setText(self.build_stats_html(row, favorite))
        hover_panel.adjustSize()

        window = row.window()
        global_pos = row.mapToGlobal(QPoint(row.width(), 0))
        local = window.mapFromGlobal(global_pos)
        panel_width = hover_panel.sizeHint().width()
        panel_height = hover_panel.sizeHint().height()

        x = local.x() + 4
        if x + panel_width > window.width():
            x = local.x() - row.width() - panel_width - 8
        y = max(0, min(local.y(), window.height() - panel_height))

        hover_panel.move(x, y)
        hover_panel.show()
        hover_panel.raise_()

    def hide(self, hover_panel: QLabel) -> None:
        hover_panel.hide()

    def build_stats_html(self, row: QWidget, favorite: dict) -> str:
        theme = getattr(row.window(), "_theme_spec", get_theme("light"))

        def make_row(label: str, value: str) -> str:
            return (
                f"<tr>"
                f'<td style="color:{theme.stats_label};padding-right:8px;">{label}</td>'
                f'<td style="color:{theme.stats_value};">{value}</td>'
                f"</tr>"
            )

        fp = favorite.get("formula_params") or {}
        fp_type = fp.get("type", "standard") if isinstance(fp, dict) else "standard"

        rows = [
            make_row("Formula", favorite["formula"]),
            make_row(
                "Center", f"{favorite['center_x']:.6f}, {favorite['center_y']:.6f}"
            ),
            make_row("Scale", f"{favorite['scale']:.8f}"),
            make_row("Iterations", str(favorite["max_iterations"])),
            make_row("Mode", favorite["coloring_mode"]),
            make_row("Julia", "Yes" if favorite["is_julia"] else "No"),
        ]
        if favorite["is_julia"] and fp_type == "julia":
            rows.append(
                make_row(
                    "Julia c",
                    f"{fp.get('cx', 0.0):.4f}+{fp.get('cy', 0.0):.4f}i",
                )
            )
        rows.append(make_row("Power", str(favorite["power"])))
        if favorite["formula"].lower() in ("phoenix",) and fp_type == "phoenix":
            rows.append(
                make_row(
                    "Phoenix",
                    f"{fp.get('real', 0.0):.4f}+{fp.get('imag', 0.0):.4f}i",
                )
            )
        if favorite["coloring_mode"].lower().startswith("orbit_trap") and fp_type == "newton":
            rows.append(
                make_row(
                    "Trap pt",
                    f"{fp.get('trap_x', 0.0):.3f}, {fp.get('trap_y', 0.0):.3f}",
                )
            )

        return (
            '<table style="font-size:11px;font-family:monospace;white-space:nowrap;">'
            + "".join(rows)
            + "</table>"
        )
