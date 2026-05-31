from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from dataclasses import dataclass
from typing import Literal

from fractal_studio.state import (
    FavoriteSnapshot,
    UiSettings,
    deserialize_favorites_payload,
    deserialize_settings_payload,
    serialize_favorites_payload,
    serialize_settings_payload,
)


@dataclass(frozen=True)
class SettingsLoadResult:
    settings: UiSettings
    source: Literal["current", "legacy", "default"]
    diagnostic: str = ""


class SettingsRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, settings: UiSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = serialize_settings_payload(settings)
        self._path.write_text(json.dumps(payload, indent=2))

    def load(self) -> SettingsLoadResult:
        try:
            raw = json.loads(self._path.read_text())
            settings = deserialize_settings_payload(raw)
            if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
                return SettingsLoadResult(settings=settings, source="current")
            if isinstance(raw, dict) and "version" not in raw:
                return SettingsLoadResult(settings=settings, source="legacy")
            return SettingsLoadResult(settings=settings, source="default")
        except FileNotFoundError:
            return SettingsLoadResult(settings=UiSettings(), source="default")
        except json.JSONDecodeError:
            return SettingsLoadResult(
                settings=UiSettings(),
                source="default",
                diagnostic="Ignored invalid settings file and loaded defaults.",
            )
        except (TypeError, ValueError):
            return SettingsLoadResult(
                settings=UiSettings(),
                source="default",
                diagnostic="Ignored unsupported settings payload and loaded defaults.",
            )

    def update(self, transform: Callable[[UiSettings], UiSettings]) -> UiSettings:
        current = self.load().settings
        updated = transform(current)
        self.save(updated)
        return updated


class FavoritesRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self.last_load_diagnostic = ""

    def save(self, favorites: list[FavoriteSnapshot]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = serialize_favorites_payload(favorites)
        self._path.write_text(json.dumps(payload, indent=2))

    def load(self) -> list[FavoriteSnapshot]:
        self.last_load_diagnostic = ""
        try:
            raw = json.loads(self._path.read_text())
            return deserialize_favorites_payload(raw)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            self.last_load_diagnostic = (
                "Ignored invalid favorites file and loaded an empty list."
            )
            return []
        except (TypeError, ValueError):
            self.last_load_diagnostic = (
                "Ignored unsupported favorites payload and loaded an empty list."
            )
            return []
