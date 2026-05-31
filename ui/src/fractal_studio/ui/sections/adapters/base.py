from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fractal_studio.ui.sections.state import MainWindowSectionsState


class _BasePortsAdapter:
    def __init__(
        self,
        sections_state: MainWindowSectionsState,
        on_status: Callable[[str], None],
    ) -> None:
        self._state = sections_state
        self._on_status = on_status

    def show_status(self, message: str) -> None:
        self._on_status(message)


class _FavoriteActionsMixin:
    def save_favorite(self) -> None:
        self._state.favorites.save_favorite()
