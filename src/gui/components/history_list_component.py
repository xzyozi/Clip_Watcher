import tkinter as tk
from tkinter import ttk
from src.core.config import THEMES

class HistoryListComponent(tk.Frame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.history_data = []

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        self.listbox = tk.Listbox(self, height=10, selectmode=tk.EXTENDED)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_events(self):
        self.listbox.bind("<<ListboxSelect>>", self._on_history_select)
        self.listbox.bind("<Double-Button-1>", lambda e: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", self.listbox.curselection()))
        from src.gui import context_menu
        history_context_menu = context_menu.HistoryContextMenu(self.master, self.app)
        self.listbox.bind("<Button-3>", history_context_menu.show)

    def _on_history_select(self, event):
        # This event is now handled by the parent (main_gui) to update the text widget
        self.app.event_dispatcher.dispatch("HISTORY_SELECTION_CHANGED", {
            "selected_indices": self.listbox.curselection()
        })

    def update_history(self, history, theme):
        self.history_data = history
        
        selected_indices = self.listbox.curselection()
        scroll_pos = self.listbox.yview()

        self.listbox.delete(0, tk.END)
        
        pinned_bg_color = theme["pinned_bg"]

        for i, item_tuple in enumerate(history):
            content, is_pinned = item_tuple
            display_text = content.replace('\n', ' ').replace('\r', '')
            prefix = "📌 " if is_pinned else ""
            self.listbox.insert(tk.END, f"{prefix}{i+1}. {display_text[:100]}...")
            if is_pinned:
                self.listbox.itemconfig(i, {'bg': pinned_bg_color})

        for index in selected_indices:
            self.listbox.selection_set(index)
        self.listbox.yview_moveto(scroll_pos[0])

    def apply_theme(self, theme):
        self.listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])
        self.update_history(self.history_data, theme) # Re-apply pinned colors

    def apply_font(self, font):
        self.listbox.config(font=font)
