import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import traceback
from src.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar
from src.settings_manager import SettingsManager
from src.plugin_manager import PluginManager
from src.gui.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.fixed_phrases_manager import FixedPhrasesManager
from src.utils.undo_manager import UndoManager

# Define history file path
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.environ['APPDATA'], 'ClipWatcher')
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser('~'), '.clipwatcher')

os.makedirs(APP_DATA_DIR, exist_ok=True)
HISTORY_FILE_PATH = os.path.join(APP_DATA_DIR, 'history.json')


from src.base_application import BaseApplication

class Application(BaseApplication):
    def __init__(self, master, settings_manager, monitor, fixed_phrases_manager, plugin_manager, event_dispatcher):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.undo_manager = UndoManager(event_dispatcher)
        self.history_sort_ascending = False
        
        # Initialize event handlers first
        self.history_handlers = HistoryEventHandlers(self, event_dispatcher, self.undo_manager)
        self.file_handlers = FileEventHandlers(self, event_dispatcher)
        self.settings_handlers = SettingsEventHandlers(event_dispatcher)
        
        self.gui = ClipWatcherGUI(master, self)
        self.monitor.set_gui_update_callback(self.gui.update_clipboard_display)
        self.monitor.set_error_callback(self.show_error_message)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)

        self.event_dispatcher.subscribe("HISTORY_TOGGLE_SORT", self.on_toggle_history_sort)

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
        settings_window = SettingsWindow(self.master, self.settings_manager, self)
        settings_window.grab_set()

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
        from src.application_builder import ApplicationBuilder

        logger = setup_logging()
        
        logger.info("アプリケーションを開始します")
        
        root = tk.Tk()
    
        builder = ApplicationBuilder()
        app = builder.with_event_dispatcher()\
                     .with_settings()\
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