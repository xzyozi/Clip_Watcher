import tkinter as tk
from tkinter import ttk, font
from src.gui import context_menu
from src import config
from src.config import THEMES
from src.gui.fixed_phrases_window import FixedPhrasesFrame
from src.gui.components.history_list_component import HistoryListComponent

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

        self.current_clipboard_frame = tk.LabelFrame(clipboard_tab_frame, text="Current Clipboard Content", padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        self.current_clipboard_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        self.redo_button = tk.Button(self.current_clipboard_frame, text="⟳", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_REDO_LAST_ACTION"), state=tk.DISABLED)
        self.redo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.undo_button = tk.Button(self.current_clipboard_frame, text="⟲", command=lambda: self.app.event_dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"), state=tk.DISABLED)
        self.undo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.clipboard_text_widget = tk.Text(self.current_clipboard_frame, wrap=tk.WORD, height=5)
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar = tk.Scrollbar(self.current_clipboard_frame, orient="vertical", command=self.clipboard_text_widget.yview)
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.clipboard_text_widget.config(yscrollcommand=self.clipboard_text_scrollbar.set)

        self.clipboard_text_widget.insert(tk.END, "Waiting for clipboard content...")
        self.clipboard_text_widget.config(state=tk.DISABLED)
        self.clipboard_text_widget.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.clipboard_text_widget))
        self.clipboard_text_widget.bind("<KeyRelease>", self._on_text_widget_change)
        self.clipboard_text_widget.bind("<FocusOut>", self._on_text_widget_change)

        self.search_frame = tk.Frame(clipboard_tab_frame, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        self.search_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        self.search_label = tk.Label(self.search_frame, text="検索 (Search):")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=config.BUTTON_PADDING_X)
        self.search_entry.bind("<KeyRelease>", lambda event: self.app.event_dispatcher.dispatch("HISTORY_SEARCH", self.search_entry.get()))
        self.search_entry.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.search_entry))

        history_container_frame = tk.LabelFrame(clipboard_tab_frame, text="Clipboard History", padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        history_container_frame.pack(fill=tk.BOTH, expand=True, pady=config.BUTTON_PADDING_Y)
        self.history_component = HistoryListComponent(history_container_frame, self.app)
        self.history_component.pack(fill=tk.BOTH, expand=True)

        self.control_frame = tk.Frame(clipboard_tab_frame)
        self.control_frame.pack(pady=config.FRAME_PADDING)

        self.copy_history_button = tk.Button(self.control_frame, text="Copy Selected", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", self.history_component.listbox.curselection()))
        self.copy_history_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.sort_button = tk.Button(self.control_frame, text="Sort: Desc", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_TOGGLE_SORT"))
        self.sort_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.format_button = tk.Button(self.control_frame, text="Format", command=lambda: self.app.event_dispatcher.dispatch("HISTORY_FORMAT_ITEM"), state=tk.DISABLED)
        self.format_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.quit_button = tk.Button(self.control_frame, text="Quit", command=self.app.file_handlers.handle_quit)
        self.quit_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        fixed_phrases_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(fixed_phrases_tab_frame, text="Fixed Phrases")
        self.fixed_phrases_frame = FixedPhrasesFrame(fixed_phrases_tab_frame, self.app)
        self.fixed_phrases_frame.pack(fill=tk.BOTH, expand=True)

        self.app.event_dispatcher.subscribe("UNDO_REDO_STACK_CHANGED", self._update_undo_redo_buttons)
        self.app.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        self.app.event_dispatcher.subscribe("HISTORY_SELECTION_CHANGED", self._on_history_selection_changed)

    def on_settings_changed(self, settings):
        self.apply_theme(settings.get("theme", "light"))
        self.apply_font_settings(
            settings.get("clipboard_content_font_family", "TkDefaultFont"),
            settings.get("clipboard_content_font_size", 10),
            settings.get("history_font_family", "TkDefaultFont"),
            settings.get("history_font_size", 10)
        )
        self.app.master.attributes("-topmost", settings.get("always_on_top", False))

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
            self.clipboard_text_widget.config(state=tk.DISABLED)

    def apply_theme(self, theme_name):
        super().apply_theme(theme_name)
        theme = THEMES.get(theme_name, THEMES['light'])
        self.current_clipboard_frame.config(bg=theme["frame_bg"], fg=theme["label_fg"])
        self.clipboard_text_widget.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], insertbackground=theme["fg"])
        self.search_frame.config(bg=theme["bg"])
        self.search_label.config(bg=theme["bg"], fg=theme["label_fg"])
        self.search_entry.config(bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["fg"])
        self.history_component.apply_theme(theme)
        self.control_frame.config(bg=theme["bg"])
        self.copy_history_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.sort_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.format_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.undo_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.redo_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.quit_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        if hasattr(self, 'fixed_phrases_frame'):
            self.fixed_phrases_frame.config(bg=theme["frame_bg"])
            if hasattr(self.fixed_phrases_frame, 'list_component'):
                self.fixed_phrases_frame.list_component.config(bg=theme["frame_bg"])
                if hasattr(self.fixed_phrases_frame.list_component, 'phrase_listbox'):
                    self.fixed_phrases_frame.list_component.phrase_listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])
            if hasattr(self.fixed_phrases_frame, 'edit_component'):
                self.fixed_phrases_frame.edit_component.config(bg=theme["frame_bg"])
                for child in self.fixed_phrases_frame.edit_component.winfo_children():
                    if isinstance(child, tk.Frame):
                        child.config(bg=theme["frame_bg"])
                        for button in child.winfo_children():
                            if isinstance(button, tk.Button):
                                button.config(bg=theme["button_bg"], fg=theme["button_fg"], activebackground=theme["select_bg"], activeforeground=theme["select_fg"])
                for child in self.fixed_phrases_frame.edit_component.winfo_children():
                    if isinstance(child, tk.Button):
                        child.config(bg=theme["button_bg"], fg=theme["button_fg"])

    def apply_font_settings(self, clipboard_content_font_family, clipboard_content_font_size, history_font_family, history_font_size):
        clipboard_font = font.Font(family=clipboard_content_font_family, size=clipboard_content_font_size)
        history_font = font.Font(family=history_font_family, size=history_font_size)
        self.clipboard_text_widget.config(font=clipboard_font)
        self.history_component.apply_font(history_font)

    def update_clipboard_display(self, current_content, history):
        self.history_data = history
        search_query = self.search_entry.get() if hasattr(self, 'search_entry') else ""
        if search_query:
            filtered_history = self.app.monitor.get_filtered_history(search_query)
            self.history_component.update_history(filtered_history)
        else:
            self.history_component.update_history(history)

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
            self.clipboard_text_widget.config(state=tk.DISABLED)

    def _on_text_widget_change(self, event):
        if self._debounce_job:
            self.master.after_cancel(self._debounce_job)
        if str(event.type) == 'FocusOut':
            self._save_edited_text()
        else:
            self._debounce_job = self.master.after(500, self._save_edited_text)

    def _save_edited_text(self):
        selected_indices = self.history_component.listbox.curselection()
        if not selected_indices:
            return
        selected_index = selected_indices[0]
        new_text = self.clipboard_text_widget.get("1.0", "end-1c")
        if 0 <= selected_index < len(self.history_data):
            original_text, _ = self.history_data[selected_index]
            if new_text != original_text:
                self.app.event_dispatcher.dispatch("HISTORY_ITEM_EDITED", {'new_text': new_text, 'original_text': original_text})