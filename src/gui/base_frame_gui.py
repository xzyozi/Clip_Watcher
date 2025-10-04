import tkinter as tk
from tkinter import ttk
from src.core import config
from src.core.config import THEMES
from src.gui import theme_manager

class BaseFrameGUI(tk.Frame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self):
        pass