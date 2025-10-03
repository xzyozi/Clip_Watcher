import os
import sys
from src.event_dispatcher import EventDispatcher

class SettingsEventHandlers:
    def __init__(self, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    def on_settings_changed(self, settings):
        startup_enabled = settings.get("startup_on_boot", False)
        self._manage_startup(startup_enabled)

    def _manage_startup(self, startup_enabled):
        if sys.platform == "win32":
            startup_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            startup_script_path = os.path.join(startup_folder, "ClipWatcher.bat")

            try:
                if startup_enabled:
                    script_content = f'@echo off\nstart "" "{sys.executable}" "{os.path.abspath("clip_watcher.py")}"'
                    with open(startup_script_path, "w") as f:
                        f.write(script_content)
                else:
                    if os.path.exists(startup_script_path):
                        os.remove(startup_script_path)
            except Exception as e:
                # Handle potential errors, e.g., permissions
                print(f"Failed to manage startup script: {e}")
