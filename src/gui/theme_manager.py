from tkinter import ttk, Toplevel, Tk
import tkinter as tk
from src.core.config.defaults import THEMES

class ThemeManager:
    def __init__(self, root):
        self.root = root
        self.current_theme = "light"
        self.menubar = None

    def set_menubar(self, menubar):
        self.menubar = menubar

    def apply_theme(self, theme_name):
        if theme_name not in THEMES:
            print(f"Theme '{theme_name}' not found. Falling back to 'light'.")
            theme_name = "light"
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        # 1. Configure ttk styles
        style = ttk.Style(self.root)
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

        # Custom button styles for calendar
        style.configure('Today.TButton', background=theme.get("highlight_bg", theme["button_bg"]), foreground=theme["button_fg"])
        style.map('Today.TButton', background=[('active', theme.get("highlight_bg", theme["button_bg"]))])
        style.configure('Selected.TButton', background=theme["select_bg"], foreground=theme["select_fg"])
        style.map('Selected.TButton', background=[('active', theme["select_bg"])])

        style.configure('TCheckbutton', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TRadiobutton', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.configure('TEntry', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"], insertbackground=theme["fg"])
        style.configure('TSpinbox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])
        style.configure('TCombobox', fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])

        # Notebook specific styling
        style.configure('TNotebook', background=theme["bg"], bordercolor=theme["frame_bg"])
        style.configure('TNotebook.Tab', background=theme["frame_bg"], foreground=theme["label_fg"])
        style.map('TNotebook.Tab', background=[('selected', theme["bg"])], foreground=[('selected', theme["fg"])])

        # Treeview specific styling
        style.configure('Treeview', background=theme["listbox_bg"], foreground=theme["listbox_fg"], fieldbackground=theme["listbox_bg"])
        style.map('Treeview', background=[('selected', theme["select_bg"])], foreground=[('selected', theme["select_fg"])])
        style.configure('Treeview.Heading', background=theme["button_bg"], foreground=theme["button_fg"])

        # 2. Recursively apply theme to non-ttk widgets
        self.apply_theme_to_widget_tree(self.root, theme)
        
        # 3. Apply theme to menubar
        if self.menubar:
            self._apply_theme_to_menu(self.menubar, theme)

    def _apply_theme_to_menu(self, menu, theme):
        try:
            menu.config(
                background=theme.get("menu_bg"),
                foreground=theme.get("menu_fg"),
                activebackground=theme.get("active_menu_bg"),
                activeforeground=theme.get("active_menu_fg"),
                relief=tk.FLAT,
                borderwidth=0
            )
        except tk.TclError:
            pass # May fail on some systems

        try:
            for i in range(menu.index("end") + 1):
                if menu.type(i) == "cascade":
                    submenu_name = menu.entrycget(i, "menu")
                    if submenu_name:
                        submenu = menu.nametowidget(submenu_name)
                        self._apply_theme_to_menu(submenu, theme)
        except (tk.TclError, AttributeError):
            # This can fail on some systems or if the menu is torn off
            pass

    def apply_theme_to_widget_tree(self, widget, theme):
        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.LabelFrame)):
                 widget.config(bg=theme["bg"])
            elif isinstance(widget, (tk.Text, tk.Listbox)):
                widget.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])
            elif isinstance(widget, (tk.Button, tk.Checkbutton, tk.Radiobutton)):
                widget.config(bg=theme["button_bg"], fg=theme["button_fg"], activebackground=theme["select_bg"], activeforeground=theme["select_fg"], selectcolor=theme["frame_bg"])
            elif isinstance(widget, tk.Label):
                widget.config(bg=theme["bg"], fg=theme["label_fg"])

        except (tk.TclError, AttributeError):
            pass # Ignore errors for widgets that don't support these properties

        for child in widget.winfo_children():
            self.apply_theme_to_widget_tree(child, theme)

    def apply_theme_to_toplevel(self, toplevel_window):
        """Applies the current theme to a Toplevel window and its children."""
        theme = THEMES[self.current_theme]
        self.apply_theme_to_widget_tree(toplevel_window, theme)

    def get_current_theme(self):
        return self.current_theme