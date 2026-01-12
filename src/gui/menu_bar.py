import tkinter as tk
from src.event_handlers import main_handlers as event_handlers
import logging

logger = logging.getLogger(__name__)

def create_menu_bar(master, app_instance):
    translator = app_instance.translator
    menubar = tk.Menu(master)

    # File Menu
    file_menu = tk.Menu(menubar, tearoff=0, postcommand=app_instance.reassert_topmost)
    file_menu.add_command(label=translator("settings_menu_item"), command=app_instance.open_settings_window)
    file_menu.add_command(label=translator("export_history_menu_item"), command=app_instance.file_handlers.handle_export_history)
    file_menu.add_command(label=translator("import_history_menu_item"), command=app_instance.file_handlers.handle_import_history)
    file_menu.add_separator()
    file_menu.add_command(label=translator("exit_menu_item"), command=app_instance.file_handlers.handle_quit)
    menubar.add_cascade(label=translator("file_menu"), menu=file_menu)

    # Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0, postcommand=app_instance.reassert_topmost)
    edit_menu.add_command(label=translator("find_menu_item"), command=lambda: logger.info("Find clicked"))
    edit_menu.add_command(label=translator("copy_merged_menu_item"), command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_COPY_MERGED", app_instance.gui.history_component.listbox.curselection()))
    edit_menu.add_separator()
    edit_menu.add_command(label=translator("delete_selected_menu_item"), command=app_instance.history_handlers.handle_delete_selected_history)
    edit_menu.add_command(label=translator("delete_all_unpinned_menu_item"), command=app_instance.history_handlers.handle_delete_all_unpinned_history)
    edit_menu.add_command(label=translator("clear_all_history_menu_item"), command=app_instance.history_handlers.handle_clear_all_history)
    menubar.add_cascade(label=translator("edit_menu"), menu=edit_menu)

    # View Menu
    view_menu = tk.Menu(menubar, tearoff=0, postcommand=app_instance.reassert_topmost)
    app_instance.always_on_top_var = tk.BooleanVar(value=app_instance.settings_manager.get_setting("always_on_top"))
    view_menu.add_checkbutton(label=translator("always_on_top_menu_item"),
                              command=lambda: app_instance.event_dispatcher.dispatch("SETTINGS_ALWAYS_ON_TOP", app_instance.always_on_top_var.get()),
                              variable=app_instance.always_on_top_var)
    
    app_instance.theme_var = tk.StringVar(value=app_instance.settings_manager.get_setting("theme"))
    theme_menu = tk.Menu(view_menu, tearoff=0)
    theme_menu.add_radiobutton(label=translator("light_theme_menu_item"), variable=app_instance.theme_var, value="light",
                               command=lambda: app_instance.settings_handlers.handle_set_theme("light", save=False))
    theme_menu.add_radiobutton(label=translator("dark_theme_menu_item"), variable=app_instance.theme_var, value="dark",
                               command=lambda: app_instance.settings_handlers.handle_set_theme("dark", save=False))
    theme_menu.add_radiobutton(label=translator("system_theme_menu_item"), variable=app_instance.theme_var, value="system",
                               command=lambda: logger.info("Follow System theme clicked (not yet implemented)"))
    view_menu.add_cascade(label=translator("theme_menu"), menu=theme_menu)
    
    view_menu.add_separator()
    
    filter_menu = tk.Menu(view_menu, tearoff=0)
    filter_menu.add_command(label=translator("show_all_menu_item"), command=lambda: logger.info("Show All clicked"))
    filter_menu.add_command(label=translator("show_text_only_menu_item"), command=lambda: logger.info("Show Text Only clicked"))
    filter_menu.add_command(label=translator("show_images_only_menu_item"), command=lambda: logger.info("Show Images Only clicked"))
    view_menu.add_cascade(label=translator("filter_menu"), menu=filter_menu)
    
    menubar.add_cascade(label=translator("view_menu"), menu=view_menu)

    # Tools Menu
    tools_menu = tk.Menu(menubar, tearoff=0)
    gui_plugins = app_instance.plugin_manager.get_gui_plugins()
    for plugin in gui_plugins:
        # The command should switch to the plugin's tab in the GUI
        command = lambda p=plugin: app_instance.gui.select_tool_tab(p.name)
        tools_menu.add_command(label=translator(plugin.name), command=command)
    menubar.add_cascade(label=translator("tools_menu"), menu=tools_menu)

    # Help Menu
    help_menu = tk.Menu(menubar, tearoff=0, postcommand=app_instance.reassert_topmost)
    help_menu.add_command(label=translator("how_to_use_menu_item"), command=event_handlers.handle_how_to_use)
    help_menu.add_command(label=translator("about_menu_item"), command=event_handlers.handle_about)
    menubar.add_cascade(label=translator("help_menu"), menu=help_menu)

    return menubar
