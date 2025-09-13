import tkinter as tk
from tkinter import ttk
from src.gui import theme_manager

class FormatDialog(tk.Toplevel):
    def __init__(self, master, plugin_manager, settings_manager):
        super().__init__(master)
        self.title("Select Formatter")
        self.plugin_manager = plugin_manager
        self.settings_manager = settings_manager
        self.selected_plugin = None

        self.geometry("350x250")
        self.transient(master)
        self.grab_set()

        self._create_widgets()
        
        theme = theme_manager.apply_theme(self, self.settings_manager.get_setting("theme"))
        self.plugin_listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(main_frame, text="Choose a plugin to apply:")
        label.pack(pady=5)

        self.plugin_listbox = tk.Listbox(main_frame, exportselection=False)
        self.plugin_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        self.plugins = self.plugin_manager.get_available_plugins()
        for plugin in self.plugins:
            self.plugin_listbox.insert(tk.END, f"{plugin.name}")

        self.plugin_listbox.bind("<Double-Button-1>", self._on_ok)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok)
        ok_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT)

    def _on_ok(self, event=None):
        selected_indices = self.plugin_listbox.curselection()
        if selected_indices:
            self.selected_plugin = self.plugins[selected_indices[0]]
        else:
            self.selected_plugin = None
        self.destroy()

    def _on_cancel(self, event=None):
        self.selected_plugin = None
        self.destroy()