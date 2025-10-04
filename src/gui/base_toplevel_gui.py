import tkinter as tk
from tkinter import ttk
from src.core import config
from src.core.config import THEMES
from src.gui import theme_manager

class BaseToplevelGUI(tk.Toplevel):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance
        self.app.theme_manager.apply_theme_to_widget(self, self.app.theme_manager.get_current_theme())

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self):
        pass