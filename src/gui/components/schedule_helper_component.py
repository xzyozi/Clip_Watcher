import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime

from src.gui.base_frame_gui import BaseFrameGUI
from src.gui import context_menu

class ScheduleHelperComponent(BaseFrameGUI):
    """
    A GUI component to help create date and time related text.
    """
    def __init__(self, master, app_instance):
        super().__init__(master, app_instance)
        self.logger.info("Initializing ScheduleHelperComponent.")
        self._create_widgets()

    def _create_widgets(self):
        # Main frame is divided into top (controls) and bottom (text editor)
        main_paned_window = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame for Calendar and Time selection ---
        controls_frame = ttk.Frame(main_paned_window, padding=5)
        main_paned_window.add(controls_frame, height=250) # Initial height

        # --- Bottom Frame for Text Editing ---
        editor_frame = ttk.LabelFrame(main_paned_window, text="Generated Text")
        main_paned_window.add(editor_frame)

        # Re-use the text widget implementation from MainGUI
        self.text_scrollbar = ttk.Scrollbar(editor_frame, orient="vertical")
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_widget = tk.Text(editor_frame, wrap=tk.WORD, relief=tk.FLAT, yscrollcommand=self.text_scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_scrollbar.config(command=self.text_widget.yview)

        # Apply context menu
        text_context_menu = context_menu.TextWidgetContextMenu(self.master, self.text_widget)
        self.text_widget.bind("<Button-3>", text_context_menu.show)

        self.logger.info("ScheduleHelperComponent widgets created.")

