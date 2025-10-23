import json
import os
from .event_dispatcher import EventDispatcher

class SettingsManager:
    def __init__(self, event_dispatcher: EventDispatcher, file_path="settings.json"):
        self.event_dispatcher = event_dispatcher
        self.file_path = file_path
        self.settings = self._get_default_settings()

    def load_and_notify(self):
        """Loads settings from the file and notifies listeners."""
        loaded_settings = self._load_settings()
        self.settings.update(loaded_settings)
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def _load_settings(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _get_default_settings(self):
        return {
            "theme": "light",
            "history_limit": 50,
            "always_on_top": False,
            "excluded_apps": ["keepass.exe", "bitwarden.exe"],
            "startup_on_boot": False,
            "notification_sound_enabled": False,
            "clipboard_content_font_family": "TkDefaultFont",
            "clipboard_content_font_size": 10,
            "history_font_family": "TkDefaultFont",
            "history_font_size": 10,
            "show_calendar_tab": True, # This is for main window tabs
            "show_hash_calculator_tab": False, # This is for main window tabs
            "show_unit_converter_tab": False, # This is for main window tabs
            "show_general_settings_tab": True,
            "show_history_settings_tab": True,
            "show_notifications_settings_tab": True,
            "show_font_settings_tab": True,
            "show_excluded_apps_settings_tab": True,
            "show_modules_settings_tab": True
        }

    def save_settings(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
        # Notify listeners that settings have changed
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def notify_listeners(self):
        """Notifies listeners about the current settings."""
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def save_settings_to_file(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def load_settings_from_file(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    loaded_settings = json.load(f)
                    if "theme" in loaded_settings and "history_limit" in loaded_settings:
                        self.settings.update(loaded_settings)
                        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)
                        return True
                except (json.JSONDecodeError, TypeError):
                    return False
        return False