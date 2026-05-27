from __future__ import annotations

from collections.abc import Callable

from fractal_studio.persistence import SettingsLoadResult


class SettingsWorkflowService:
    def backend_state_message(self, backend_loaded: bool, backend_available: bool) -> str:
        if backend_loaded and backend_available:
            return "Rust extension loaded."
        return "Rust extension not loaded. Build fractal_core to enable the editor."

    def startup_message(self, load_result: SettingsLoadResult) -> str:
        if load_result.source == "legacy":
            return "Loaded legacy settings file."
        return ""

    def status_message(self, backend_loaded: bool, settings_source: str = "default") -> str:
        source = "Rust backend" if backend_loaded else "scaffold defaults"
        message = f"Fractal Studio ready with {source}."
        if settings_source == "legacy":
            return f"{message} Loaded legacy settings file."
        return message

    def append_diagnostics(self, message: str, diagnostics: list[str]) -> str:
        parts = [d.strip() for d in diagnostics if d and d.strip()]
        if not parts:
            return message
        return f"{message} {' '.join(parts)}"

    def apply_theme_name(
        self,
        theme_name: str,
        persist: bool,
        current_theme: str,
        apply_theme_to_app: Callable[[str], None],
        persist_theme: Callable[[str], None],
    ) -> str:
        if theme_name != current_theme:
            apply_theme_to_app(theme_name)
        if persist:
            persist_theme(theme_name)
        return theme_name