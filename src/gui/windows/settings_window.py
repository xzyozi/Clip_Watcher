from __future__ import annotations

import copy
import tkinter as tk
from tkinter import filedialog, font, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING

from src.core.config import defaults as config
from src.gui.base.base_toplevel_gui import BaseToplevelGUI
from src.utils.error_handler import log_and_show_error

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.core.config.settings_manager import SettingsManager
    from src.plugins.base_plugin import Plugin


class SettingsWindow(BaseToplevelGUI):
    def __init__(
        self,
        master: tk.Misc,
        app_instance: BaseApplication,
        settings_manager: SettingsManager,
    ) -> None:
        super().__init__(master, app_instance)
        self.title("Settings")
        self.geometry(config.SETTINGS_WINDOW_GEOMETRY)
        self.settings_manager = settings_manager
        self.app_instance = app_instance

        self.initial_settings = copy.deepcopy(self.settings_manager.settings)
        self.settings_saved = False

        # Variables for settings
        self.theme_var = tk.StringVar(value=self.settings_manager.get_setting("theme"))
        self.language_var = tk.StringVar(
            value=self.settings_manager.get_setting("language")
        )
        self.history_limit_var = tk.IntVar(
            value=self.settings_manager.get_setting("history_limit")
        )
        self.always_on_top_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("always_on_top")
        )
        self.startup_on_boot_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("startup_on_boot")
        )
        self.notifications_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("notifications_enabled")
        )
        self.notification_content_length_var = tk.IntVar(
            value=self.settings_manager.get_setting("notification_content_length")
        )
        self.notification_show_app_name_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("notification_show_app_name")
        )
        self.notification_sound_enabled_var = tk.BooleanVar(
            value=self.settings_manager.get_setting("notification_sound_enabled")
        )

        self.clipboard_content_font_family_var = tk.StringVar(
            value=self.settings_manager.get_setting("clipboard_content_font_family")
        )
        self.clipboard_content_font_size_var = tk.IntVar(
            value=self.settings_manager.get_setting("clipboard_content_font_size")
        )
        self.history_font_family_var = tk.StringVar(
            value=self.settings_manager.get_setting("history_font_family")
        )
        self.history_font_size_var = tk.IntVar(
            value=self.settings_manager.get_setting("history_font_size")
        )

        self.tool_tab_vars: dict[str, tk.BooleanVar] = {}
        gui_plugins: list[Plugin] = self.app_instance.plugin_manager.get_gui_plugins() # type: ignore
        for plugin in gui_plugins:
            tool_name = plugin.name
            setting_name = f"show_{tool_name.lower().replace(' ', '_')}_tab"
            self.tool_tab_vars[tool_name] = tk.BooleanVar(
                value=self.settings_manager.get_setting(setting_name, True)
            )

        self.settings_tab_names: list[str] = [
            "General",
            "History",
            "Notifications",
            "Font",
            "Excluded Apps",
            "Modules",
        ]
        self.settings_tab_vars: dict[str, tk.BooleanVar] = {}
        for tab_name in self.settings_tab_names:
            setting_name = f"show_{tab_name.lower().replace(' ', '_')}_settings_tab"
            self.settings_tab_vars[tab_name] = tk.BooleanVar(
                value=self.settings_manager.get_setting(setting_name)
            )

        self.excluded_apps_list: list[str] = list(
            self.settings_manager.get_setting("excluded_apps")
        )

        self._create_widgets()

    def _create_widgets(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X, fill=tk.BOTH, expand=True)

        self.tab_frames: dict[str, ttk.Frame] = {}

        general_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        history_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        notification_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        font_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        excluded_apps_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        modules_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)

        self.tab_frames["General"] = general_frame
        self.tab_frames["History"] = history_frame
        self.tab_frames["Notifications"] = notification_frame
        self.tab_frames["Font"] = font_frame
        self.tab_frames["Excluded Apps"] = excluded_apps_frame
        self.tab_frames["Modules"] = modules_frame

        for tab_name, tab_frame in self.tab_frames.items():
            self.notebook.add(tab_frame, text=tab_name)

        # Populate General Settings tab
        appearance_frame = ttk.LabelFrame(general_frame, text="Appearance", padding=config.FRAME_PADDING)
        appearance_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        theme_label = ttk.Label(appearance_frame, text="Theme:")
        theme_label.grid(row=0, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        theme_options = ["light", "dark"]
        theme_menu = ttk.OptionMenu(appearance_frame, self.theme_var, self.theme_var.get(), *theme_options)
        theme_menu.grid(row=0, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        language_label = ttk.Label(appearance_frame, text="Language:")
        language_label.grid(row=1, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        language_options = ["en", "ja"]
        language_menu = ttk.OptionMenu(appearance_frame, self.language_var, self.language_var.get(), *language_options)
        language_menu.grid(row=1, column=1, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        window_behavior_frame = ttk.LabelFrame(general_frame, text="Window Behavior", padding=config.FRAME_PADDING)
        window_behavior_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        always_on_top_check = ttk.Checkbutton(window_behavior_frame, text="Always on Top", variable=self.always_on_top_var)
        always_on_top_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        startup_frame = ttk.LabelFrame(general_frame, text="Startup", padding=config.FRAME_PADDING)
        startup_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        startup_on_boot_check = ttk.Checkbutton(startup_frame, text="Start with Windows", variable=self.startup_on_boot_var)
        startup_on_boot_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        # Populate Modules Settings tab
        main_window_tabs_frame = ttk.LabelFrame(modules_frame, text="Main Window Tabs", padding=config.FRAME_PADDING)
        main_window_tabs_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        for i, (tool_name, var) in enumerate(self.tool_tab_vars.items()):
            check = ttk.Checkbutton(main_window_tabs_frame, text=f"Show {tool_name} Tab", variable=var)
            check.grid(row=i, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)

        settings_window_tabs_frame = ttk.LabelFrame(modules_frame, text="Settings Window Tabs", padding=config.FRAME_PADDING)
        settings_window_tabs_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        # for i, (tab_name, var) in enumerate(self.settings_tab_vars.items()):
        #     check = ttk.Checkbutton(settings_window_tabs_frame, text=f"Show {tab_name} Tab", variable=var)
        #     check.grid(row=i, column=0, sticky=tk.W, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)


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

    def _save_settings_logic(self) -> None:
        self.settings_manager.set_setting("theme", self.theme_var.get())
        self.settings_manager.set_setting("language", self.language_var.get())
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

        for tool_name, var in self.tool_tab_vars.items():
            setting_name = f"show_{tool_name.lower().replace(' ', '_')}_tab"
            self.settings_manager.set_setting(setting_name, var.get())

        for tab_name, var in self.settings_tab_vars.items():
            setting_name = f"show_{tab_name.lower().replace(' ', '_')}_settings_tab"
            self.settings_manager.set_setting(setting_name, var.get())

        self.settings_manager.set_setting("excluded_apps", self.excluded_apps_list)

    def _apply_only(self) -> None:
        self._save_settings_logic()
        self.settings_manager.notify_listeners()

    def _save_and_close(self) -> None:
        self._save_settings_logic()
        self.settings_manager.save_settings()
        self.settings_saved = True
        self.destroy()

    def _update_ui_from_settings(self) -> None:
        self.theme_var.set(self.settings_manager.get_setting("theme"))
        self.language_var.set(self.settings_manager.get_setting("language"))
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

        for tool_name, var in self.tool_tab_vars.items():
            setting_name = f"show_{tool_name.lower().replace(' ', '_')}_tab"
            var.set(self.settings_manager.get_setting(setting_name))

        for tab_name, var in self.settings_tab_vars.items():
            setting_name = f"show_{tab_name.lower().replace(' ', '_')}_settings_tab"
            var.set(self.settings_manager.get_setting(setting_name))

        self.excluded_apps_list = list(self.settings_manager.get_setting("excluded_apps"))
        self.excluded_apps_listbox.delete(0, tk.END)
        for app in self.excluded_apps_list:
            self.excluded_apps_listbox.insert(tk.END, app)

        # Update visible tabs
        for tab_name, tab_frame in self.tab_frames.items():
            if self.settings_tab_vars[tab_name].get():
                if not tab_frame.winfo_ismapped():
                    self.notebook.add(tab_frame, text=tab_name)
            else:
                if tab_frame.winfo_ismapped():
                    self.notebook.hide(tab_frame)


    def _add_excluded_app(self) -> None:
        new_app: str | None = simpledialog.askstring("Add Excluded App", "Enter the executable name (e.g., keepass.exe):", parent=self)
        if new_app and new_app not in self.excluded_apps_list:
            self.excluded_apps_list.append(new_app)
            self.excluded_apps_listbox.insert(tk.END, new_app)

    def _remove_excluded_app(self) -> None:
        selected_indices = self.excluded_apps_listbox.curselection()
        if selected_indices:
            for i in reversed(selected_indices):
                self.excluded_apps_listbox.delete(i)
                del self.excluded_apps_list[i]

    def _export_settings(self) -> None:
        filepath: str | None = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Settings"
        )
        if filepath:
            self.settings_manager.save_settings_to_file(filepath)
            messagebox.showinfo("Export Successful", f"Settings exported to {filepath}")

    def _import_settings(self) -> bool:
        filepath: str | None = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Settings"
        )
        if filepath:
            if self.settings_manager.load_settings_from_file(filepath):
                self._update_ui_from_settings()
                messagebox.showinfo("Import Successful", "Settings imported successfully.")
                return True
            else:
                log_and_show_error("Import Failed", "Could not load settings from the selected file.")
        return False

    def _restore_defaults(self) -> None:
        if messagebox.askyesno("Restore Defaults", "Are you sure you want to restore all settings to their default values?"):
            self.settings_manager.settings = self.settings_manager._get_default_settings()
            self._update_ui_from_settings()

    def destroy(self) -> None:
        if not self.settings_saved:
            self.settings_manager.settings = copy.deepcopy(self.initial_settings)
            self.settings_manager.notify_listeners()

        super().destroy()
