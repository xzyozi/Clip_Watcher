import tkinter as tk
from tkinter import ttk, simpledialog

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings_manager, app_instance):
        super().__init__(master)
        self.title("Settings")
        self.geometry("450x450")
        self.settings_manager = settings_manager
        self.app_instance = app_instance

        # Variables for settings
        self.theme_var = tk.StringVar(value=self.settings_manager.get_setting("theme"))
        self.history_limit_var = tk.IntVar(value=self.settings_manager.get_setting("history_limit"))
        self.always_on_top_var = tk.BooleanVar(value=self.settings_manager.get_setting("always_on_top"))
        self.excluded_apps_list = list(self.settings_manager.get_setting("excluded_apps"))

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # General Settings
        general_frame = ttk.LabelFrame(main_frame, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, pady=5)

        # Theme
        theme_label = ttk.Label(general_frame, text="Theme:")
        theme_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        theme_options = ["light", "dark"]
        theme_menu = ttk.OptionMenu(general_frame, self.theme_var, self.theme_var.get(), *theme_options)
        theme_menu.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Always on Top
        always_on_top_check = ttk.Checkbutton(general_frame, text="Always on Top", variable=self.always_on_top_var)
        always_on_top_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)


        # History Settings
        history_frame = ttk.LabelFrame(main_frame, text="History Settings", padding="10")
        history_frame.pack(fill=tk.X, pady=5)

        history_limit_label = ttk.Label(history_frame, text="History Limit:")
        history_limit_label.pack(side=tk.LEFT, padx=(0, 10))

        history_limit_spinbox = ttk.Spinbox(history_frame, from_=10, to=1000, increment=10, textvariable=self.history_limit_var, width=10)
        history_limit_spinbox.pack(side=tk.LEFT)

        # Excluded Apps Settings
        excluded_apps_frame = ttk.LabelFrame(main_frame, text="Excluded Applications", padding="10")
        excluded_apps_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.excluded_apps_listbox = tk.Listbox(excluded_apps_frame)
        for app in self.excluded_apps_list:
            self.excluded_apps_listbox.insert(tk.END, app)
        self.excluded_apps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        excluded_apps_button_frame = ttk.Frame(excluded_apps_frame)
        excluded_apps_button_frame.pack(side=tk.LEFT, padx=(10, 0))

        add_app_button = ttk.Button(excluded_apps_button_frame, text="Add", command=self._add_excluded_app)
        add_app_button.pack(fill=tk.X, pady=5)

        remove_app_button = ttk.Button(excluded_apps_button_frame, text="Remove", command=self._remove_excluded_app)
        remove_app_button.pack(fill=tk.X, pady=5)


        # Buttons
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        save_button = ttk.Button(button_frame, text="Save", command=self._save_and_close)
        save_button.pack(side=tk.RIGHT, padx=(10, 0))

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.RIGHT)

    def _add_excluded_app(self):
        new_app = simpledialog.askstring("Add Excluded App", "Enter the executable name (e.g., keepass.exe):", parent=self)
        if new_app and new_app not in self.excluded_apps_list:
            self.excluded_apps_list.append(new_app)
            self.excluded_apps_listbox.insert(tk.END, new_app)

    def _remove_excluded_app(self):
        selected_indices = self.excluded_apps_listbox.curselection()
        if selected_indices:
            for i in reversed(selected_indices):
                self.excluded_apps_listbox.delete(i)
                del self.excluded_apps_list[i]

    def _save_and_close(self):
        # Save settings
        self.settings_manager.set_setting("theme", self.theme_var.get())
        self.settings_manager.set_setting("history_limit", self.history_limit_var.get())
        self.settings_manager.set_setting("always_on_top", self.always_on_top_var.get())
        self.settings_manager.set_setting("excluded_apps", self.excluded_apps_list)
        self.settings_manager.save_settings()

        # Apply settings that require immediate action
        self.app_instance.apply_settings()

        self.destroy()