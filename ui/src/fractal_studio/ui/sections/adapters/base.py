from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fractal_studio.backend import BackendProfile, CoreBackend
    from fractal_studio.ui.sections.state import MainWindowSectionsState
    from fractal_studio.ui.workers.render_scheduler import RenderScheduler
    from fractal_studio.viewport import FractalViewportWidget


class _BasePortsAdapter:
    def __init__(
        self,
        sections_state: MainWindowSectionsState,
        on_status: Callable[[str], None],
        backend: CoreBackend,
        backend_profile: BackendProfile,
        render_scheduler: RenderScheduler | None = None,
    ) -> None:
        self._state = sections_state
        self._on_status = on_status
        self._backend = backend
        self._backend_profile = backend_profile
        self._render_scheduler = render_scheduler

    @property
    def backend(self) -> CoreBackend:
        return self._backend

    @property
    def backend_profile(self) -> BackendProfile:
        return self._backend_profile

    @property
    def viewport(self) -> FractalViewportWidget | None:
        return self._state.viewport.viewport

    @property
    def render_scheduler(self) -> RenderScheduler | None:
        return self._render_scheduler

    def show_status(self, message: str) -> None:
        self._on_status(message)


class _FavoriteActionsMixin:
    def save_favorite(self) -> None:
        self._state.favorites.save_favorite()
