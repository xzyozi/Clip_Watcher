import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
from src.gui.main_gui import ClipWatcherGUI
from src.core.base_application import BaseApplication
from src.gui import menu_bar
from src.gui.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.utils.undo_manager import UndoManager
from src.core.tool_manager import ToolManager
from src.gui.components.hash_calculator_component import HashCalculatorComponent
from src.gui.components.unit_converter_component import UnitConverterComponent
from src.gui.components.schedule_helper_component import ScheduleHelperComponent

class MainApplication(BaseApplication):
    def __init__(self, master, settings_manager, monitor, fixed_phrases_manager, plugin_manager, event_dispatcher, theme_manager, tool_manager):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.theme_manager = theme_manager
        self.tool_manager = tool_manager # Use the passed tool_manager
        self.undo_manager = UndoManager(event_dispatcher)
        self.history_sort_ascending = False

        self.history_handlers = HistoryEventHandlers(self, event_dispatcher, self.undo_manager)
        self.file_handlers = FileEventHandlers(self, event_dispatcher)
        self.settings_handlers = SettingsEventHandlers(event_dispatcher, self.settings_manager)
        
        self.gui = ClipWatcherGUI(master, self)
        self._register_tools()
        self.gui.create_tool_tabs() # Add this line
        
        self.monitor.set_gui_update_callback(self.update_gui)
        self.monitor.set_error_callback(self.show_error_message)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)
        self.theme_manager.set_menubar(self.menubar)

        self.event_dispatcher.subscribe("HISTORY_TOGGLE_SORT", self.on_toggle_history_sort)
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        
        self.master.bind("<FocusIn>", self.on_focus_in)

    def _register_tools(self):
        # Register tools that can be opened as tabs in the main GUI
        self.tool_manager.register_tool("Calendar", lambda: self.gui.show_tool_tab("Calendar"))
        self.tool_manager.register_tool("Hash Calculator", lambda: self.gui.show_tool_tab("Hash Calculator"))
        self.tool_manager.register_tool("Unit Converter", lambda: self.gui.show_tool_tab("Unit Converter"))

    def update_gui(self, current_content, history):
        """Wrapper to pass sort order to the GUI."""
        self.gui.update_clipboard_display(current_content, history, self.history_sort_ascending)

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
                    # Use __file__ to get the absolute path of the script.
                    # This is more robust than relying on the current working directory.
                    script_path = os.path.abspath(__file__)
                    script_content = f'@echo off\nstart "" "{sys.executable}" "{script_path}"'
                    with open(startup_script_path, "w") as f:
                        f.write(script_content)
                else:
                    if os.path.exists(startup_script_path):
                        os.remove(startup_script_path)
            except Exception as e:
                self.show_error_message("Startup Error", f"Failed to manage startup script: {e}")

    def on_toggle_history_sort(self):
        """Toggles the history sort order and refreshes the GUI."""
        self.history_sort_ascending = not self.history_sort_ascending
        
        if self.history_sort_ascending:
            self.gui.sort_button.config(text="Sort: Asc")
        else:
            self.gui.sort_button.config(text="Sort: Desc")

        self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())
        print(f"History sort order set to {'ascending' if self.history_sort_ascending else 'descending'}")

    def open_settings_window(self):
        self.create_toplevel(SettingsWindow, self.settings_manager)

    def create_toplevel(self, ToplevelClass, *args, **kwargs):
        toplevel_window = ToplevelClass(self.master, self, *args, **kwargs)
        
        # ToplevelClass might have a wait_window(), so the window could be destroyed
        # by the time we get here. Check if it still exists.
        if toplevel_window.winfo_exists():
            if self.settings_manager.get_setting("always_on_top", False):
                toplevel_window.attributes("-topmost", True)
            toplevel_window.transient(self.master)
            
        return toplevel_window

    def show_error_message(self, title, message):
        messagebox.showerror(title, message)

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.monitor.save_history_to_file()
        self.master.destroy()
