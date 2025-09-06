import tkinter as tk
import os
import sys
from src.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar
from src.settings_manager import SettingsManager
from src.gui.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers

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

        self.history_handlers = HistoryEventHandlers(self)
        self.file_handlers = FileEventHandlers(self)
        self.settings_handlers = SettingsEventHandlers(self)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)

        self.settings_manager.apply_settings(self)

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
