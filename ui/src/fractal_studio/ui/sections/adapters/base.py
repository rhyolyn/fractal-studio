from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fractal_studio.main_window import MainWindow


class _BasePortsAdapter:
    def __init__(self, owner: MainWindow) -> None:
        self._owner = owner
        self._state = owner._sections_state

    @property
    def backend(self):
        return self._state.backend

    @property
    def backend_profile(self):
        return self._state.backend_profile

    @property
    def viewport(self):
        return self._state.viewport

    def show_status(self, message: str) -> None:
        self._owner.statusBar().showMessage(message)


class _FavoriteActionsMixin:
    def save_favorite(self) -> None:
        self._state._favorites_state.save_favorite()
