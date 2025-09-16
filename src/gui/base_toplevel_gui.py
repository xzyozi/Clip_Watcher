import tkinter as tk
from tkinter import ttk
from src import config
from src.config import THEMES
from src.gui import theme_manager

class BaseToplevelGUI(tk.Toplevel):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance
        self.current_theme_name = self.app.settings_manager.get_setting("theme")
        self.apply_theme(self.current_theme_name)

    def apply_theme(self, theme_name):
        theme = theme_manager.apply_theme(self.master, theme_name)
        # Apply theme to this toplevel itself
        self.config(bg=theme["bg"])
        self.current_theme_name = theme_name

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self):
        pass
