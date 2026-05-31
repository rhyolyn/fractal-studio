from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from fractal_studio.persistence import SettingsRepository
from fractal_studio.state import UiSettings


@pytest.mark.unit
def test_update_returns_transformed_settings(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    result = repo.update(lambda s: dataclasses.replace(s, theme="dark"))
    assert result.theme == "dark"


@pytest.mark.unit
def test_update_persists_to_disk(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    repo.update(lambda s: dataclasses.replace(s, theme="sepia"))
    reloaded = repo.load().settings
    assert reloaded.theme == "sepia"


@pytest.mark.unit
def test_update_preserves_other_fields(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    repo.update(lambda s: dataclasses.replace(s, sidebar_collapsed={"params": True}))
    repo.update(lambda s: dataclasses.replace(s, theme="dark"))
    final = repo.load().settings
    assert final.theme == "dark"
    assert final.sidebar_collapsed == {"params": True}


@pytest.mark.unit
def test_update_receives_current_stored_state(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    repo.update(lambda s: dataclasses.replace(s, theme="sepia"))
    seen: list[UiSettings] = []
    repo.update(lambda s: seen.append(s) or s)
    assert seen[0].theme == "sepia"
