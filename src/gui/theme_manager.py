from tkinter import ttk
from src.config import THEMES

def apply_theme(window, theme_name):
    """Applies a theme to a window and its ttk widgets."""
    theme = THEMES.get(theme_name, THEMES["light"])
    
    # Apply to the Toplevel window itself
    window.config(bg=theme["bg"])
    
    style = ttk.Style(window)
    style.theme_use('default')
    
    # Configure general styles for ttk widgets
    style.configure('.', background=theme["bg"], foreground=theme["fg"])
    style.configure('TFrame', background=theme["frame_bg"])
    style.configure('TLabelFrame', background=theme["frame_bg"], foreground=theme["label_fg"])
    style.configure('TLabel', background=theme["frame_bg"], foreground=theme["label_fg"])
    style.configure('TButton', background=theme["button_bg"], foreground=theme["button_fg"])
    style.map('TButton', background=[('active', theme["button_bg"])])
    style.configure('TCheckbutton', background=theme["frame_bg"], foreground=theme["label_fg"])
    style.configure('TRadiobutton', background=theme["frame_bg"], foreground=theme["label_fg"])
    style.configure('TEntry', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"], insertbackground=theme["fg"])
    style.configure('TSpinbox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"], insertbackground=theme["fg"])
    style.configure('TCombobox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"], insertbackground=theme["fg"])

    # Notebook specific styling
    style.configure('TNotebook', background=theme["bg"], bordercolor=theme["frame_bg"])
    style.configure('TNotebook.Tab', background=theme["frame_bg"], foreground=theme["label_fg"], lightcolor=theme["frame_bg"], darkcolor=theme["frame_bg"])
    style.map('TNotebook.Tab', background=[('selected', theme["bg"])], foreground=[('selected', theme["fg"])])
    style.configure('TNotebook.Client', background=theme["frame_bg"])

    # For non-ttk widgets, they need to be configured manually.
    # This function will return the theme dictionary so the caller can handle them.
    return theme
