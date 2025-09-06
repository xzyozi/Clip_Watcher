import json
import os

class SettingsManager:
    def __init__(self, file_path="settings.json"):
        self.file_path = file_path
        self.settings = self._load_settings()

    def _load_settings(self):
        # Start with default settings
        default_settings = self._get_default_settings()
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                try:
                    # Update defaults with loaded settings
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
                except json.JSONDecodeError:
                    pass # Keep defaults if file is corrupt
        self.settings = default_settings
        return self.settings


    def _get_default_settings(self):
        return {
            "theme": "light",
            "history_limit": 50,
            "always_on_top": False,
            "excluded_apps": ["keepass.exe", "bitwarden.exe"]
        }

    def save_settings(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def get_setting(self, key):
        return self.settings.get(key)

    def set_setting(self, key, value):
        self.settings[key] = value