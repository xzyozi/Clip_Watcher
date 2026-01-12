import tkinter as tk
from tkinter import ttk, font
from src.gui.base import context_menu
from src.core.config import defaults as config
from src.core.config.defaults import THEMES
from src.gui.windows.fixed_phrases_window import FixedPhrasesFrame
from src.gui.components import HistoryListComponent
# from src.core.config.tool_config import TOOL_COMPONENTS
from src.gui.custom_widgets import CustomText, CustomEntry

from src.gui.base.base_frame_gui import BaseFrameGUI

class ClipWatcherGUI(BaseFrameGUI):
    def __init__(self, master, app_instance):
        super().__init__(master, app_instance)
        master.geometry(config.MAIN_WINDOW_GEOMETRY)
        
        self.history_data = []
        self.is_user_editing = False # Flag to prevent UI updates during editing

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X, fill=tk.BOTH, expand=True)

        self.clipboard_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(self.clipboard_tab_frame, text="") # Text set in _update_widget_text

        paned_window = tk.PanedWindow(self.clipboard_tab_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg=THEMES[self.app.theme_manager.get_current_theme()]["frame_bg"])
        paned_window.pack(fill=tk.BOTH, expand=True)

        self.current_clipboard_frame = ttk.LabelFrame(paned_window, text="") # Text set in _update_widget_text
        paned_window.add(self.current_clipboard_frame, height=100)

        self.redo_button = ttk.Button(self.current_clipboard_frame, text="⟳", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_REDO_LAST_ACTION"), state=tk.DISABLED)
        self.redo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.undo_button = ttk.Button(self.current_clipboard_frame, text="⟲", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"), state=tk.DISABLED)
        self.undo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.clipboard_text_scrollbar = ttk.Scrollbar(self.current_clipboard_frame, orient="vertical")
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.clipboard_text_widget = CustomText(self.current_clipboard_frame, wrap=tk.WORD, height=5, relief=tk.FLAT, yscrollcommand=self.clipboard_text_scrollbar.set, app=self.app)
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar.config(command=self.clipboard_text_widget.yview)

        self.clipboard_text_widget.config(state=tk.NORMAL)
        # Bind focus events to control editing state
        self.clipboard_text_widget.bind("<FocusIn>", self.start_editing)
        self.clipboard_text_widget.bind("<FocusOut>", self.finish_editing)

        history_area_frame = ttk.Frame(paned_window)
        paned_window.add(history_area_frame)

        self.search_frame = ttk.Frame(history_area_frame)
        self.search_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        self.search_label = ttk.Label(self.search_frame, text="") # Text set in _update_widget_text
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = CustomEntry(self.search_frame, app=self.app)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=config.BUTTON_PADDING_X)
        self.search_entry.bind("<KeyRelease>", lambda event: self.app.event_dispatcher.dispatch("HISTORY_SEARCH", self.search_entry.get()))

        self.history_container_frame = ttk.LabelFrame(history_area_frame, text="") # Text set in _update_widget_text
        self.history_container_frame.pack(fill=tk.BOTH, expand=True, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)
        self.history_component = HistoryListComponent(self.history_container_frame, self.app)
        self.history_component.pack(fill=tk.BOTH, expand=True)

        self.control_frame = ttk.Frame(history_area_frame)
        self.control_frame.pack(pady=config.FRAME_PADDING)

        self.copy_history_button = ttk.Button(self.control_frame, text="", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", self.history_component.listbox.curselection()))
        self.copy_history_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.sort_button = ttk.Button(self.control_frame, text="", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_TOGGLE_SORT"))
        self.sort_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.format_button = ttk.Button(self.control_frame, text="", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_FORMAT_ITEM"), state=tk.DISABLED)
        self.format_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.quit_button = ttk.Button(self.control_frame, text="", command=self.app.file_handlers.handle_quit)
        self.quit_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.fixed_phrases_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(self.fixed_phrases_tab_frame, text="") # Text set in _update_widget_text
        self.fixed_phrases_frame = FixedPhrasesFrame(self.fixed_phrases_tab_frame, self.app)
        self.fixed_phrases_frame.pack(fill=tk.BOTH, expand=True)

        self.plugin_tab_frames = [] # Keep track of created frames

        self.app.event_dispatcher.subscribe("UNDO_REDO_STACK_CHANGED", self._update_undo_redo_buttons)
        self.app.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        self.app.event_dispatcher.subscribe("HISTORY_SELECTION_CHANGED", self._on_history_selection_changed)
        self.app.event_dispatcher.subscribe("LANGUAGE_CHANGED", self._update_widget_text)

        self.on_font_settings_changed(self.app.settings_manager.settings)
        self._create_plugin_tabs()
        self._update_widget_text() # Initial text setup
        self.notebook.bind("<Button-1>", self.handle_global_click, add="+")

    def handle_global_click(self, event):
        """
        Handles a click anywhere in the notebook. If the click is outside
        the main text widget while it has focus, treat it as a focus-out
        event to ensure the content is saved. This is a workaround for
        cases where the <FocusOut> event doesn't fire as expected when
        clicking on other widgets within the same window.
        """
        focused_widget = self.focus_get()

        if focused_widget == self.clipboard_text_widget and event.widget != self.clipboard_text_widget:
            self.finish_editing(event)

    def start_editing(self, event):
        """User starts editing the text area."""
        self.is_user_editing = True

    def finish_editing(self, event):
        """
        Handles the end of a user's editing session in the text widget.
        If a history item was selected, it performs an undoable in-place update.
        Otherwise, it treats the edit as a new clipboard entry.
        """
        if not self.is_user_editing:
            return

        self.is_user_editing = False
        edited_text = self.clipboard_text_widget.get("1.0", "end-1c")

        if not edited_text:
            return

        selected_indices = self.history_component.listbox.curselection()

        if selected_indices:
            index = selected_indices[0]
            
            if 0 <= index < len(self.history_data):
                original_text, _, item_id = self.history_data[index]

                if edited_text != original_text:
                    from src.core.commands import UpdateHistoryCommand
                    command = UpdateHistoryCommand(
                        monitor=self.app.monitor,
                        item_id=item_id,
                        original_text=original_text,
                        new_text=edited_text
                    )
                    self.app.undo_manager.execute_command(command)
        else:
            self.app.monitor.update_clipboard(edited_text)

    def _update_widget_text(self):
        """Updates all translatable text widgets."""
        translator = self.app.translator
        self.master.title(translator("app_title"))
        self.notebook.tab(self.clipboard_tab_frame, text=translator("clipboard_tab"))
        self.current_clipboard_frame.config(text=translator("current_clipboard_content_label"))
        
        if not self.clipboard_text_widget.get("1.0", "end-1c"):
            self.clipboard_text_widget.insert(tk.END, translator("waiting_for_clipboard_content"))

        self.search_label.config(text=translator("search_label"))
        self.history_container_frame.config(text=translator("clipboard_history_label"))
        self.copy_history_button.config(text=translator("copy_selected_button"))
        
        sort_key = "sort_asc_button" if self.app.history_sort_ascending else "sort_desc_button"
        self.sort_button.config(text=translator(sort_key))

        self.format_button.config(text=translator("format_button"))
        self.quit_button.config(text=translator("quit_button"))
        self.notebook.tab(self.fixed_phrases_tab_frame, text=translator("fixed_phrases_tab"))

    def _destroy_plugin_tabs(self):
        for frame in self.plugin_tab_frames:
            self.notebook.forget(frame)
            frame.destroy()
        self.plugin_tab_frames = []

    def _create_plugin_tabs(self):
        """Dynamically creates GUI tabs from plugins based on settings."""
        self._destroy_plugin_tabs() # Clear existing plugin tabs
        gui_plugins = self.app.plugin_manager.get_gui_plugins()
        for plugin in gui_plugins:
            setting_key = f"show_{plugin.name.lower().replace(' ', '_')}_tab"
            if self.app.settings_manager.get_setting(setting_key, True):
                try:
                    component_frame = plugin.create_gui_component(self.notebook, self.app)
                    if component_frame:
                        self.plugin_tab_frames.append(component_frame) # Track the frame
                        tab_text = self.app.translator(plugin.name)
                        self.notebook.add(component_frame, text=tab_text)
                except Exception as e:
                    print(f"Failed to create GUI component for plugin '{plugin.name}': {e}")

    def on_settings_changed(self, settings):
        self.on_font_settings_changed(settings)
        self._create_plugin_tabs() # Re-create tabs based on new settings

    def on_font_settings_changed(self, settings):
        self.apply_font_settings(
            settings.get("clipboard_content_font_family", "TkDefaultFont"),
            settings.get("clipboard_content_font_size", 10),
            settings.get("history_font_family", "TkDefaultFont"),
            settings.get("history_font_size", 10)
        )

    def _update_undo_redo_buttons(self, data):
        self.undo_button.config(state=tk.NORMAL if data['can_undo'] else tk.DISABLED)
        self.redo_button.config(state=tk.NORMAL if data['can_redo'] else tk.DISABLED)

    def _on_history_selection_changed(self, data):
        selected_indices = data["selected_indices"]
        self.clipboard_text_widget.config(state=tk.NORMAL)
        self.clipboard_text_widget.delete(1.0, tk.END)

        if selected_indices:
            self.format_button.config(state=tk.NORMAL)
            index = selected_indices[0]
            if 0 <= index < len(self.history_data):
                content, _, _ = self.history_data[index]
                self.clipboard_text_widget.insert(tk.END, content)
        else:
            self.format_button.config(state=tk.DISABLED)
            self.clipboard_text_widget.insert(tk.END, self.app.monitor.last_clipboard_data)
            self.clipboard_text_widget.config(state=tk.NORMAL)

    def apply_font_settings(self, clipboard_content_font_family, clipboard_content_font_size, history_font_family, history_font_size):
        clipboard_font = font.Font(family=clipboard_content_font_family, size=clipboard_content_font_size)
        history_font = font.Font(family=history_font_family, size=history_font_size)
        self.clipboard_text_widget.config(font=clipboard_font)
        self.history_component.apply_font(history_font)

    def update_clipboard_display(self, current_content, history, sort_ascending=False):
        if self.is_user_editing:
            return

        if sort_ascending:
            pinned = [item for item in history if item[1]]
            unpinned = [item for item in history if not item[1]]
            pinned.reverse()
            unpinned.reverse()
            history = pinned + unpinned

        self.history_data = history
        search_query = self.search_entry.get() if hasattr(self, 'search_entry') else ""
        theme_name = self.app.theme_manager.get_current_theme()
        theme = THEMES.get(theme_name, THEMES['light'])
        if search_query:
            filtered_history = self.app.monitor.get_filtered_history(search_query)
            self.history_component.update_history(filtered_history, theme)
        else:
            self.history_component.update_history(history, theme)

        selected_indices = self.history_component.listbox.curselection()
        self.clipboard_text_widget.config(state=tk.NORMAL)
        self.clipboard_text_widget.delete(1.0, tk.END)
        if selected_indices:
            index = selected_indices[0]
            if 0 <= index < len(self.history_data):
                content, _, _ = self.history_data[index]
                self.clipboard_text_widget.insert(tk.END, content)
        else:
            self.clipboard_text_widget.insert(tk.END, current_content)
            self.clipboard_text_widget.config(state=tk.NORMAL)

    def select_tool_tab(self, plugin_name):
        """Selects a notebook tab corresponding to the given plugin name."""
        for i, tab_id in enumerate(self.notebook.tabs()):
            tab_text = self.notebook.tab(tab_id, "text")
            translated_plugin_name = self.app.translator(plugin_name)
            if tab_text == translated_plugin_name:
                self.notebook.select(i)
                break
