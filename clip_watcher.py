import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import traceback
from src.core.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar
from src.core.settings_manager import SettingsManager
from src.core.plugin_manager import PluginManager
from src.gui.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.event_handlers import main_handlers
from src.core.fixed_phrases_manager import FixedPhrasesManager
from src.utils.undo_manager import UndoManager
from src.gui.theme_manager import ThemeManager

# Define history file path
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.environ['APPDATA'], 'ClipWatcher')
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser('~'), '.clipwatcher')

os.makedirs(APP_DATA_DIR, exist_ok=True)
HISTORY_FILE_PATH = os.path.join(APP_DATA_DIR, 'history.json')


from src.core.base_application import BaseApplication

class Application(BaseApplication):
    def __init__(self, master, settings_manager, monitor, fixed_phrases_manager, plugin_manager, event_dispatcher, theme_manager):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.theme_manager = theme_manager
        self.undo_manager = UndoManager(event_dispatcher)
        self.history_sort_ascending = False
        self.calendar_visible_var = tk.BooleanVar(value=True)
        
        # Initialize event handlers first
        self.history_handlers = HistoryEventHandlers(self, event_dispatcher, self.undo_manager)
        self.file_handlers = FileEventHandlers(self, event_dispatcher)
        self.settings_handlers = SettingsEventHandlers(event_dispatcher, self.settings_manager)
        
        self.gui = ClipWatcherGUI(master, self)
        self.monitor.set_gui_update_callback(self.gui.update_clipboard_display)
        self.monitor.set_error_callback(self.show_error_message)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)
        self.theme_manager.set_menubar(self.menubar)

        self.event_dispatcher.subscribe("HISTORY_TOGGLE_SORT", self.on_toggle_history_sort)
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        
        self.master.bind("<FocusIn>", self.on_focus_in)

    def on_focus_in(self, event=None):
        self.reassert_topmost()

    def reassert_topmost(self):
        if self.settings_manager.get_setting("always_on_top", False):
            self.master.attributes("-topmost", False)
            self.master.attributes("-topmost", True)

    def on_settings_changed(self, settings):
        theme = settings.get("theme", "light")
        self.theme_manager.apply_theme(theme)
        if hasattr(self, 'theme_var'):
            self.theme_var.set(theme)
        
        always_on_top = settings.get("always_on_top", False)
        self.master.attributes("-topmost", always_on_top)
        if hasattr(self, 'always_on_top_var'):
            self.always_on_top_var.set(always_on_top)

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

    def on_toggle_history_sort(self):
        """Toggles the history sort order and refreshes the GUI."""
        self.history_sort_ascending = not self.history_sort_ascending
        
        if self.history_sort_ascending:
            self.gui.sort_button.config(text="Sort: Asc")
        else:
            self.gui.sort_button.config(text="Sort: Desc")

        self.gui.update_clipboard_display(self.monitor.last_clipboard_data, self.monitor.get_history())
        print(f"History sort order set to {'ascending' if self.history_sort_ascending else 'descending'}")

    def open_settings_window(self):
        self.create_toplevel(SettingsWindow, self.settings_manager)

    def create_toplevel(self, ToplevelClass, *args, **kwargs):
        toplevel_window = ToplevelClass(self.master, self, *args, **kwargs)
        if self.settings_manager.get_setting("always_on_top", False):
            toplevel_window.attributes("-topmost", True)
        toplevel_window.grab_set()
        return toplevel_window

    def show_error_message(self, title, message):
        messagebox.showerror(title, message)

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.monitor.save_history_to_file()
        self.master.destroy()

if __name__ == "__main__":
    try:
        from src.utils.logging_config import setup_logging
        from src.core.application_builder import ApplicationBuilder

        logger = setup_logging()
        
        logger.info("アプリケーションを開始します")
        
        root = tk.Tk()
    
        builder = ApplicationBuilder()
        app = builder.with_event_dispatcher()\
                     .with_settings()\
                     .with_theme_manager(root)\
                     .with_fixed_phrases_manager()\
                     .with_plugin_manager()\
                     .with_clipboard_monitor(root, HISTORY_FILE_PATH)\
                     .build(root)
               
        logger.info("アプリケーションの初期化が完了しました")
        
        root.mainloop()
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()
