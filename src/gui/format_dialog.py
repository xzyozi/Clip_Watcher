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

        self.geometry("350x300") # Adjusted height for buttons
        self.transient(master)
        self.grab_set()

        self._create_widgets()
        
        # Apply theme
        theme = theme_manager.apply_theme(self, self.settings_manager.get_setting("theme"))
        # No listbox to style, but other ttk widgets will be themed

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(main_frame, text="Choose a plugin to apply:")
        label.pack(pady=5)

        # Frame for plugin buttons
        plugin_button_frame = ttk.Frame(main_frame)
        plugin_button_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.plugins = self.plugin_manager.get_available_plugins()
        for plugin in self.plugins:
            button = ttk.Button(plugin_button_frame, text=plugin.name, 
                                command=lambda p=plugin: self._on_plugin_select(p))
            button.pack(fill=tk.X, pady=2) # Pack buttons vertically

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT)

    def _on_plugin_select(self, plugin):
        self.selected_plugin = plugin
        self.destroy()

    def _on_cancel(self):
        self.selected_plugin = None
        self.destroy()
