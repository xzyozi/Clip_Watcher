import json
import os
from typing import Any, cast

from ..event_dispatcher import EventDispatcher
from . import defaults


class SettingsManager:
    def __init__(self, event_dispatcher: EventDispatcher, file_path: str = "settings.json") -> None:
        self.event_dispatcher = event_dispatcher
        self.file_path = file_path
        self.settings: dict[str, Any] = self._get_default_settings()

    def load_and_notify(self) -> None:
        """Loads settings from the file and notifies listeners."""
        loaded_settings = self._load_settings()
        self.settings.update(loaded_settings)
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def _load_settings(self) -> dict[str, Any]:
        if os.path.exists(self.file_path):
            with open(self.file_path, encoding="utf-8") as f:
                try:
                    return cast(dict[str, Any], json.load(f))
                except json.JSONDecodeError:
                    return {}
        return {}

    def _get_default_settings(self) -> dict[str, Any]:
        return defaults.DEFAULT_USER_SETTINGS.copy()

    def save_settings(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
        # Notify listeners that settings have changed
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value

    def notify_listeners(self) -> None:
        """Notifies listeners about the current settings."""
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def save_settings_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def load_settings_from_file(self, filepath: str) -> bool:
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                try:
                    loaded_settings = json.load(f)
                    if "theme" in loaded_settings and "history_limit" in loaded_settings:
                        self.settings.update(loaded_settings)
                        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)
                        return True
                except (json.JSONDecodeError, TypeError):
                    return False
        return False
