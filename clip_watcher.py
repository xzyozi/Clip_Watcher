import tkinter as tk
import os
import sys
from src.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar
from src.settings_manager import SettingsManager
from src.gui.settings_window import SettingsWindow

class Application:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = SettingsManager()
        
        self.monitor = ClipboardMonitor(
            master,
            self.settings_manager.get_setting("history_limit"),
            self.settings_manager.get_setting("excluded_apps")
        )
        self.gui = ClipWatcherGUI(master, self.stop_monitor, self.monitor)
        self.monitor.set_gui_update_callback(self.gui.update_clipboard_display)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)

        self.apply_settings()

    def apply_settings(self):
        # Apply theme
        theme = self.settings_manager.get_setting("theme")
        self.gui.apply_theme(theme)

        # Apply history limit
        history_limit = self.settings_manager.get_setting("history_limit")
        self.monitor.set_history_limit(history_limit)

        # Apply always on top
        always_on_top = self.settings_manager.get_setting("always_on_top")
        self.master.attributes("-topmost", always_on_top)

        # Apply excluded apps
        excluded_apps = self.settings_manager.get_setting("excluded_apps")
        self.monitor.set_excluded_apps(excluded_apps)

        # Apply startup on boot
        startup_on_boot = self.settings_manager.get_setting("startup_on_boot")
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

    def open_settings_window(self):
        settings_window = SettingsWindow(self.master, self.settings_manager, self)
        settings_window.grab_set()

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()