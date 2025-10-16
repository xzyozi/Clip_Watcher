import tkinter as tk
from tkinter import ttk, font
from src.gui import context_menu
from src.core import config
from src.core.config import THEMES
from src.gui.fixed_phrases_window import FixedPhrasesFrame
from src.gui.components.history_list_component import HistoryListComponent
from src.gui.components.schedule_helper_component import ScheduleHelperComponent

from src.gui.base_frame_gui import BaseFrameGUI

class ClipWatcherGUI(BaseFrameGUI):
    def __init__(self, master, app_instance):
        super().__init__(master, app_instance)
        master.title("ClipWatcher")
        master.geometry(config.MAIN_WINDOW_GEOMETRY)

        self.history_data = []
        self._debounce_job = None

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X, fill=tk.BOTH, expand=True)

        clipboard_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(clipboard_tab_frame, text="Clipboard")

        paned_window = tk.PanedWindow(clipboard_tab_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg=THEMES[self.app.theme_manager.get_current_theme()]["frame_bg"])
        paned_window.pack(fill=tk.BOTH, expand=True)

        self.current_clipboard_frame = ttk.LabelFrame(paned_window, text="Current Clipboard Content")
        paned_window.add(self.current_clipboard_frame, height=100)

        self.redo_button = ttk.Button(self.current_clipboard_frame, text="⟳", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_REDO_LAST_ACTION"), state=tk.DISABLED)
        self.redo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.undo_button = ttk.Button(self.current_clipboard_frame, text="⟲", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"), state=tk.DISABLED)
        self.undo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.clipboard_text_scrollbar = ttk.Scrollbar(self.current_clipboard_frame, orient="vertical")
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.clipboard_text_widget = tk.Text(self.current_clipboard_frame, wrap=tk.WORD, height=5, relief=tk.FLAT, yscrollcommand=self.clipboard_text_scrollbar.set)
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar.config(command=self.clipboard_text_widget.yview)

        self.clipboard_text_widget.insert(tk.END, "Waiting for clipboard content...")
        self.clipboard_text_widget.config(state=tk.NORMAL)
        text_context_menu = context_menu.TextWidgetContextMenu(self.master, self.clipboard_text_widget)
        self.clipboard_text_widget.bind("<Button-3>", text_context_menu.show)
        self.clipboard_text_widget.bind("<KeyRelease>", self._on_text_widget_change)
        self.clipboard_text_widget.bind("<FocusOut>", self._on_text_widget_change)

        history_area_frame = ttk.Frame(paned_window)
        paned_window.add(history_area_frame)

        self.search_frame = ttk.Frame(history_area_frame)
        self.search_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)

        self.search_label = ttk.Label(self.search_frame, text="検索 (Search):")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=config.BUTTON_PADDING_X)
        self.search_entry.bind("<KeyRelease>", lambda event: self.app.event_dispatcher.dispatch("HISTORY_SEARCH", self.search_entry.get()))
        search_context_menu = context_menu.TextWidgetContextMenu(self.master, self.search_entry)
        self.search_entry.bind("<Button-3>", search_context_menu.show)

        history_container_frame = ttk.LabelFrame(history_area_frame, text="Clipboard History")
        history_container_frame.pack(fill=tk.BOTH, expand=True, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X)
        self.history_component = HistoryListComponent(history_container_frame, self.app)
        self.history_component.pack(fill=tk.BOTH, expand=True)

        self.control_frame = ttk.Frame(history_area_frame)
        self.control_frame.pack(pady=config.FRAME_PADDING)

        self.copy_history_button = ttk.Button(self.control_frame, text="Copy Selected", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", self.history_component.listbox.curselection()))
        self.copy_history_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.sort_button = ttk.Button(self.control_frame, text="Sort: Desc", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_TOGGLE_SORT"))
        self.sort_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.format_button = ttk.Button(self.control_frame, text="Format", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_FORMAT_ITEM"), state=tk.DISABLED)
        self.format_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.quit_button = ttk.Button(self.control_frame, text="Quit", command=self.app.file_handlers.handle_quit)
        self.quit_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        fixed_phrases_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(fixed_phrases_tab_frame, text="Fixed Phrases")
        self.fixed_phrases_frame = FixedPhrasesFrame(fixed_phrases_tab_frame, self.app)
        self.fixed_phrases_frame.pack(fill=tk.BOTH, expand=True)

        self.schedule_helper_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(self.schedule_helper_tab_frame, text="Calender")
        self.schedule_helper_frame = ScheduleHelperComponent(self.schedule_helper_tab_frame, self.app)
        self.schedule_helper_frame.pack(fill=tk.BOTH, expand=True)

        self.app.event_dispatcher.subscribe("UNDO_REDO_STACK_CHANGED", self._update_undo_redo_buttons)
        self.app.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_font_settings_changed)
        self.app.event_dispatcher.subscribe("HISTORY_SELECTION_CHANGED", self._on_history_selection_changed)

    def toggle_calendar_tab(self, visible_var):
        """Toggles the visibility of the Calender tab based on a tk.BooleanVar."""
        try:
            tab_exists = self.notebook.index(self.schedule_helper_tab_frame) is not None
        except tk.TclError:
            tab_exists = False

        if visible_var.get() and not tab_exists:
            self.notebook.add(self.schedule_helper_tab_frame, text="Calender")
            self.notebook.select(self.schedule_helper_tab_frame)
        elif not visible_var.get() and tab_exists:
            self.notebook.forget(self.schedule_helper_tab_frame)

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
                content, _ = self.history_data[index]
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

    def update_clipboard_display(self, current_content, history):
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
                content, _ = self.history_data[index]
                self.clipboard_text_widget.insert(tk.END, content)
        else:
            self.clipboard_text_widget.insert(tk.END, current_content)
            self.clipboard_text_widget.config(state=tk.NORMAL)

    def _on_text_widget_change(self, event):
        if self._debounce_job:
            self.master.after_cancel(self._debounce_job)
        if str(event.type) == 'FocusOut':
            self._save_edited_text()
        else:
            self._debounce_job = self.master.after(500, self._save_edited_text)

    def _save_edited_text(self):
        selected_indices = self.history_component.listbox.curselection()
        new_text = self.clipboard_text_widget.get("1.0", "end-1c")

        if not selected_indices:
            if new_text != self.app.monitor.last_clipboard_data:
                self.master.clipboard_clear()
                self.master.clipboard_append(new_text)
            return

        selected_index = selected_indices[0]
        if 0 <= selected_index < len(self.history_data):
            original_text, _ = self.history_data[selected_index]
            if new_text != original_text:
                self.app.event_dispatcher.dispatch("HISTORY_ITEM_EDITED", {'new_text': new_text, 'original_text': original_text})
