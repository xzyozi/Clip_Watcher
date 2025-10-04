from tkinter import ttk, Toplevel, Tk
import tkinter as tk
from src.core.config import THEMES

class ThemeManager:
    def __init__(self, root):
        self.root = root
        self.current_theme = "light"

    def apply_theme(self, theme_name):
        """
        Apply the specified theme to all windows of the application.
        """
        if theme_name not in THEMES:
            print(f"Theme '{theme_name}' not found. Falling back to 'light'.")
            theme_name = "light"
        self.current_theme = theme_name
        
        # Apply theme to the root window
        self.apply_theme_to_widget(self.root, theme_name)

    def apply_theme_to_widget(self, widget, theme_name):
        """
        Recursively apply the theme to a widget and all its children.
        """
        theme = THEMES[theme_name]
        
        # Apply to the widget itself
        try:
            widget.config(bg=theme["bg"], fg=theme["fg"])
        except tk.TclError:
            try:
                widget.config(bg=theme["bg"])
            except tk.TclError:
                pass # Ignore errors for widgets that don't support -bg

        # Special handling for ttk widgets
        style = ttk.Style(widget)
        if theme_name == 'dark':
            style.theme_use('clam')
        else:
            style.theme_use('default')
            
        style.configure('.', background=theme["bg"], foreground=theme["fg"])
        style.configure('TFrame', background=theme["frame_bg"])
        style.configure('TLabel', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TLabelFrame', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TButton', background=theme["button_bg"], foreground=theme["button_fg"])
        style.map('TButton', background=[('active', theme["button_bg"])])
        style.configure('TCheckbutton', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TRadiobutton', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TEntry', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"], insertbackground=theme["fg"])
        style.configure('TSpinbox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])
        style.configure('TCombobox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])

        # Notebook specific styling
        style.configure('TNotebook', background=theme["bg"], bordercolor=theme["frame_bg"])
        style.configure('TNotebook.Tab', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.map('TNotebook.Tab', background=[('selected', theme["bg"])], foreground=[('selected', theme["fg"])])

        # Apply to all children recursively
        for child in widget.winfo_children():
            self.apply_theme_to_widget(child, theme_name)

    def get_current_theme(self):
        return self.current_theme
