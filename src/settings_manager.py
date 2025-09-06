import json
import os
import sys

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
            "excluded_apps": ["keepass.exe", "bitwarden.exe"],
            "startup_on_boot": False,
            "notification_sound_enabled": False
        }

    def save_settings(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def get_setting(self, key):
        return self.settings.get(key)

    def set_setting(self, key, value):
        self.settings[key] = value

    def save_settings_to_file(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def load_settings_from_file(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    loaded_settings = json.load(f)
                    # Basic validation to ensure it's a valid settings file
                    if "theme" in loaded_settings and "history_limit" in loaded_settings:
                        self.settings = loaded_settings
                        return True
                except (json.JSONDecodeError, TypeError):
                    return False
        return False

    def apply_settings(self, app_instance):
        # Apply theme
        theme = self.get_setting("theme")
        app_instance.gui.apply_theme(theme)

        # Apply history limit
        history_limit = self.get_setting("history_limit")
        app_instance.monitor.set_history_limit(history_limit)

        # Apply always on top
        always_on_top = self.get_setting("always_on_top")
        app_instance.master.attributes("-topmost", always_on_top)

        # Apply excluded apps
        excluded_apps = self.get_setting("excluded_apps")
        app_instance.monitor.set_excluded_apps(excluded_apps)

        # Apply startup on boot
        startup_on_boot = self.get_setting("startup_on_boot")
        self.manage_startup(startup_on_boot)

    def manage_startup(self, startup_enabled):
        if sys.platform == "win32":
            startup_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            startup_script_path = os.path.join(startup_folder, "ClipWatcher.bat")

            if startup_enabled:
                script_content = f'@echo off\nstart "" "{sys.executable}" "{os.path.abspath("clip_watcher.py")}"'
                with open(startup_script_path, "w") as f:
                    f.write(script_content)
            else:
                if os.path.exists(startup_script_path):
                    os.remove(startup_script_path)
