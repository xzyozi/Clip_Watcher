from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.gui.base.context_menu import HistoryContextMenu


class HistoryListComponent(tk.Frame):
    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master)
        self.app = app_instance
        self.displayed_history: list[tuple[str, bool, float]] = []  # Will store the full (content, is_pinned, timestamp) tuples

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self) -> None:
        self.listbox = tk.Listbox(self, height=10, selectmode=tk.EXTENDED)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_events(self) -> None:
        self.listbox.bind("<<ListboxSelect>>", self._on_history_select)
        self.listbox.bind("<Double-Button-1>", self._on_double_click)
        from src.gui.base import context_menu
        history_context_menu: HistoryContextMenu = context_menu.HistoryContextMenu(self.master, self.app) # type: ignore
        self.listbox.bind("<Button-3>", history_context_menu.show)

    def _on_double_click(self, event: tk.Event) -> None:
        """Handler for double-click events to copy an item."""
        selected_indices: tuple[int, ...] = self.listbox.curselection()
        if not selected_indices:
            return

        # On double-click, we typically act on the first selected item.
        item_ids: list[float] = self.get_ids_for_indices(selected_indices[:1])
        if item_ids:
            # The event now passes a list of IDs, even if it's just one.
            self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", item_ids) # type: ignore

    def _on_history_select(self, event: tk.Event) -> None:
        # This event is now handled by the parent (main_gui) to update the text widget
        self.app.event_dispatcher.dispatch("HISTORY_SELECTION_CHANGED", { # type: ignore
            "selected_indices": self.listbox.curselection()
        })

    def get_ids_for_indices(self, indices: tuple[int, ...]) -> list[float]:
        """Translates listbox indices to unique history item IDs."""
        return [self.displayed_history[i][2] for i in indices if 0 <= i < len(self.displayed_history)]

    def update_history(self, history: list[tuple[str, bool, float]], theme: dict[str, str]) -> None:
        self.displayed_history = history  # Store the full data

        selected_indices = self.listbox.curselection()
        scroll_pos = self.listbox.yview()

        self.listbox.delete(0, tk.END)

        pinned_bg_color = theme["pinned_bg"]

        for i, (content, is_pinned, _timestamp) in enumerate(history):
            display_text = content.replace('\n', ' ').replace('\r', '')
            prefix = "📌 " if is_pinned else ""
            # The displayed number is still based on visual order (1-based index)
            self.listbox.insert(tk.END, f"{prefix}{i+1}. {display_text[:100]}...")
            if is_pinned:
                self.listbox.itemconfig(i, {'bg': pinned_bg_color})

        for index in selected_indices:
            if index < self.listbox.size():
                self.listbox.selection_set(index)
        self.listbox.yview_moveto(scroll_pos[0])

    def apply_theme(self, theme: dict[str, str]) -> None:
        self.listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])
        self.update_history(self.displayed_history, theme) # Re-apply pinned colors

    def apply_font(self, font: tk.font.Font) -> None:
        self.listbox.config(font=font)
