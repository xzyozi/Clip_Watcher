import tkinter as tk
import copy
from tkinter import ttk, simpledialog, filedialog, messagebox, font
from src import config
from src.gui import theme_manager

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings_manager, app_instance):
        super().__init__(master)
        self.title("Settings")
        self.geometry(config.SETTINGS_WINDOW_GEOMETRY)
        self.settings_manager = settings_manager
        self.app_instance = app_instance

        self.initial_settings = copy.deepcopy(self.settings_manager.settings)
        self.settings_saved = False

        # Variables for settings
        self.theme_var = tk.StringVar(value=self.settings_manager.get_setting("theme"))
        self.history_limit_var = tk.IntVar(value=self.settings_manager.get_setting("history_limit"))
        self.always_on_top_var = tk.BooleanVar(value=self.settings_manager.get_setting("always_on_top"))
        self.startup_on_boot_var = tk.BooleanVar(value=self.settings_manager.get_setting("startup_on_boot"))
        self.notifications_enabled_var = tk.BooleanVar(value=self.settings_manager.get_setting("notifications_enabled"))
        self.notification_content_length_var = tk.IntVar(value=self.settings_manager.get_setting("notification_content_length"))
        self.notification_show_app_name_var = tk.BooleanVar(value=self.settings_manager.get_setting("notification_show_app_name"))
        self.notification_sound_enabled_var = tk.BooleanVar(value=self.settings_manager.get_setting("notification_sound_enabled"))
        
        self.clipboard_content_font_family_var = tk.StringVar(value=self.settings_manager.get_setting("clipboard_content_font_family"))
        self.clipboard_content_font_size_var = tk.IntVar(value=self.settings_manager.get_setting("clipboard_content_font_size"))
        self.history_font_family_var = tk.StringVar(value=self.settings_manager.get_setting("history_font_family"))
        self.history_font_size_var = tk.IntVar(value=self.settings_manager.get_setting("history_font_size"))

        self.excluded_apps_list = list(self.settings_manager.get_setting("excluded_apps"))

        self._create_widgets()
        self.apply_theme(self.settings_manager.get_setting("theme")) # Apply initial theme

    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X, fill=tk.BOTH, expand=True)

        general_frame = ttk.Frame(notebook, padding=config.FRAME_PADDING)
        history_frame = ttk.Frame(notebook, padding=config.FRAME_PADDING)
        notification_frame = ttk.Frame(notebook, padding=config.FRAME_PADDING)
        font_frame = ttk.Frame(notebook, padding=config.FRAME_PADDING)
        excluded_apps_frame = ttk.Frame(notebook, padding=config.FRAME_PADDING)

        notebook.add(general_frame, text="General")
        notebook.add(history_frame, text="History")
        notebook.add(notification_frame, text="Notifications")
        notebook.add(font_frame, text="Font")
        notebook.add(excluded_apps_frame, text="Excluded Apps")

        # Populate General Settings tab
        appearance_frame = ttk.LabelFrame(general_frame, text="Appearance", padding=config.FRAME_PADDING)
        appearance_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        theme_label = ttk.Label(appearance_frame, text="Theme:")
        theme_label.grid(row=0, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        theme_options = ["light", "dark"]
        theme_menu = ttk.OptionMenu(appearance_frame, self.theme_var, self.theme_var.get(), *theme_options)
        theme_menu.grid(row=0, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        window_behavior_frame = ttk.LabelFrame(general_frame, text="Window Behavior", padding=config.FRAME_PADDING)
        window_behavior_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        always_on_top_check = ttk.Checkbutton(window_behavior_frame, text="Always on Top", variable=self.always_on_top_var)
        always_on_top_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        startup_frame = ttk.LabelFrame(general_frame, text="Startup", padding=config.FRAME_PADDING)
        startup_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        startup_on_boot_check = ttk.Checkbutton(startup_frame, text="Start with Windows", variable=self.startup_on_boot_var)
        startup_on_boot_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        # History Settings
        history_options_frame = ttk.LabelFrame(history_frame, text="History Options", padding=config.FRAME_PADDING)
        history_options_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        history_limit_label = ttk.Label(history_options_frame, text="History Limit:")
        history_limit_label.pack(side=tk.LEFT, padx=(0, 10))

        history_limit_spinbox = ttk.Spinbox(history_options_frame, from_=config.HISTORY_LIMIT_MIN, to=config.HISTORY_LIMIT_MAX, increment=config.HISTORY_LIMIT_INCREMENT, textvariable=self.history_limit_var, width=10)
        history_limit_spinbox.pack(side=tk.LEFT)

        # Populate Notification Settings tab
        notification_behavior_frame = ttk.LabelFrame(notification_frame, text="Notification Behavior", padding=config.FRAME_PADDING)
        notification_behavior_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        notifications_enabled_check = ttk.Checkbutton(notification_behavior_frame, text="Enable Notifications", variable=self.notifications_enabled_var)
        notifications_enabled_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        notification_show_app_name_check = ttk.Checkbutton(notification_behavior_frame, text="Show App Name in Notification", variable=self.notification_show_app_name_var)
        notification_show_app_name_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        
        notification_sound_enabled_check = ttk.Checkbutton(notification_behavior_frame, text="Enable Notification Sound", variable=self.notification_sound_enabled_var)
        notification_sound_enabled_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        notification_content_frame = ttk.LabelFrame(notification_frame, text="Notification Content", padding=config.FRAME_PADDING)
        notification_content_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        notification_content_length_label = ttk.Label(notification_content_frame, text="Notification Content Length:")
        notification_content_length_label.grid(row=0, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        notification_content_length_spinbox = ttk.Spinbox(notification_content_frame, from_=10, to=200, increment=10, textvariable=self.notification_content_length_var, width=10)
        notification_content_length_spinbox.grid(row=0, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        # Populate Font Settings tab
        clipboard_font_frame = ttk.LabelFrame(font_frame, text="Clipboard Content Font", padding=config.FRAME_PADDING)
        clipboard_font_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        clipboard_content_font_label = ttk.Label(clipboard_font_frame, text="Clipboard Content Font:")
        clipboard_content_font_label.grid(row=0, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        
        font_families = sorted(font.families())
        clipboard_content_font_family_menu = ttk.OptionMenu(clipboard_font_frame, self.clipboard_content_font_family_var, self.clipboard_content_font_family_var.get(), *font_families)
        clipboard_content_font_family_menu.grid(row=0, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        clipboard_content_font_size_label = ttk.Label(clipboard_font_frame, text="Size:")
        clipboard_content_font_size_label.grid(row=1, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        
        clipboard_content_font_size_spinbox = ttk.Spinbox(clipboard_font_frame, from_=8, to=24, increment=1, textvariable=self.clipboard_content_font_size_var, width=5)
        clipboard_content_font_size_spinbox.grid(row=1, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        history_font_frame = ttk.LabelFrame(font_frame, text="History Font", padding=config.FRAME_PADDING)
        history_font_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        history_font_label = ttk.Label(history_font_frame, text="History Font:")
        history_font_label.grid(row=0, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        
        history_font_family_menu = ttk.OptionMenu(history_font_frame, self.history_font_family_var, self.history_font_family_var.get(), *font_families)
        history_font_family_menu.grid(row=0, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        history_font_size_label = ttk.Label(history_font_frame, text="Size:")
        history_font_size_label.grid(row=1, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        
        history_font_size_spinbox = ttk.Spinbox(history_font_frame, from_=8, to=24, increment=1, textvariable=self.history_font_size_var, width=5)
        history_font_size_spinbox.grid(row=1, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)


        # Populate Excluded Apps Settings tab
        self.excluded_apps_listbox = tk.Listbox(excluded_apps_frame)
        for app in self.excluded_apps_list:
            self.excluded_apps_listbox.insert(tk.END, app)
        self.excluded_apps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        excluded_apps_button_frame = ttk.Frame(excluded_apps_frame)
        excluded_apps_button_frame.pack(side=tk.LEFT, padx=(10, 0))

        add_app_button = ttk.Button(excluded_apps_button_frame, text="Add", command=self._add_excluded_app)
        add_app_button.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        remove_app_button = ttk.Button(excluded_apps_button_frame, text="Remove", command=self._remove_excluded_app)
        remove_app_button.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        # Import/Export/Default buttons (placed outside the notebook, at the bottom)
        io_button_frame = ttk.Frame(self)
        io_button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=config.BUTTON_PADDING_Y)

        export_button = ttk.Button(io_button_frame, text="Export Settings", command=self._export_settings)
        export_button.pack(side=tk.LEFT)

        import_button = ttk.Button(io_button_frame, text="Import Settings", command=self._import_settings)
        import_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        default_button = ttk.Button(io_button_frame, text="Restore Defaults", command=self._restore_defaults)
        default_button.pack(side=tk.LEFT)

        # Save/Cancel/Apply Buttons
        button_frame = ttk.Frame(self, padding=config.FRAME_PADDING)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        save_button = ttk.Button(button_frame, text="Save", command=self._save_and_close)
        save_button.pack(side=tk.RIGHT, padx=(10, 0))

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side=tk.RIGHT)

        apply_button = ttk.Button(button_frame, text="Apply", command=self._apply_only)
        apply_button.pack(side=tk.RIGHT)

    def _save_settings_logic(self):
        self.settings_manager.set_setting("theme", self.theme_var.get())
        self.settings_manager.set_setting("history_limit", self.history_limit_var.get())
        self.settings_manager.set_setting("always_on_top", self.always_on_top_var.get())
        self.settings_manager.set_setting("startup_on_boot", self.startup_on_boot_var.get())
        self.settings_manager.set_setting("notifications_enabled", self.notifications_enabled_var.get())
        self.settings_manager.set_setting("notification_content_length", self.notification_content_length_var.get())
        self.settings_manager.set_setting("notification_show_app_name", self.notification_show_app_name_var.get())
        self.settings_manager.set_setting("notification_sound_enabled", self.notification_sound_enabled_var.get())
        self.settings_manager.set_setting("clipboard_content_font_family", self.clipboard_content_font_family_var.get())
        self.settings_manager.set_setting("clipboard_content_font_size", self.clipboard_content_font_size_var.get())
        self.settings_manager.set_setting("history_font_family", self.history_font_family_var.get())
        self.settings_manager.set_setting("history_font_size", self.history_font_size_var.get())
        self.settings_manager.set_setting("excluded_apps", self.excluded_apps_list)

    def _apply_only(self):
        self._save_settings_logic()
        self.settings_manager.apply_settings(self.app_instance)
        self.apply_theme(self.theme_var.get())

    def _save_and_close(self):
        self._save_settings_logic()
        self.settings_manager.save_settings()
        self.settings_manager.apply_settings(self.app_instance)
        self.apply_theme(self.theme_var.get())
        self.settings_saved = True
        self.destroy()

    def _update_ui_from_settings(self):
        self.theme_var.set(self.settings_manager.get_setting("theme"))
        self.history_limit_var.set(self.settings_manager.get_setting("history_limit"))
        self.always_on_top_var.set(self.settings_manager.get_setting("always_on_top"))
        self.startup_on_boot_var.set(self.settings_manager.get_setting("startup_on_boot"))
        self.notifications_enabled_var.set(self.settings_manager.get_setting("notifications_enabled"))
        self.notification_content_length_var.set(self.settings_manager.get_setting("notification_content_length"))
        self.notification_show_app_name_var.set(self.settings_manager.get_setting("notification_show_app_name"))
        self.notification_sound_enabled_var.set(self.settings_manager.get_setting("notification_sound_enabled"))
        self.clipboard_content_font_family_var.set(self.settings_manager.get_setting("clipboard_content_font_family"))
        self.clipboard_content_font_size_var.set(self.settings_manager.get_setting("clipboard_content_font_size"))
        self.history_font_family_var.set(self.settings_manager.get_setting("history_font_family"))
        self.history_font_size_var.set(self.settings_manager.get_setting("history_font_size"))
        
        self.excluded_apps_list = list(self.settings_manager.get_setting("excluded_apps"))
        self.excluded_apps_listbox.delete(0, tk.END)
        for app in self.excluded_apps_list:
            self.excluded_apps_listbox.insert(tk.END, app)

    def apply_theme(self, theme_name):
        theme = theme_manager.apply_theme(self, theme_name)

        if hasattr(self, 'excluded_apps_listbox'):
            self.excluded_apps_listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])

        self.current_theme_name = theme_name

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

    def _export_settings(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Settings"
        )
        if filepath:
            self.settings_manager.save_settings_to_file(filepath)
            messagebox.showinfo("Export Successful", f"Settings exported to {filepath}")

    def _import_settings(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Settings"
        )
        if filepath:
            if self.settings_manager.load_settings_from_file(filepath):
                self._update_ui_from_settings()
                messagebox.showinfo("Import Successful", "Settings imported successfully.")
            else:
                messagebox.showerror("Import Failed", "Could not load settings from the selected file.")

    def _restore_defaults(self):
        if messagebox.askyesno("Restore Defaults", "Are you sure you want to restore all settings to their default values?"):
            self.settings_manager.settings = self.settings_manager._get_default_settings()
            self._update_ui_from_settings()

    def destroy(self):
        if not self.settings_saved:
            self.settings_manager.settings = copy.deepcopy(self.initial_settings)
            self.settings_manager.apply_settings(self.app_instance)
            self.apply_theme(self.settings_manager.get_setting("theme"))

        super().destroy()
