import tkinter as tk
from abc import ABC, abstractmethod
from typing import Optional, NamedTuple
from src.core.event_dispatcher import EventDispatcher
from src.utils.i18n import Translator

# --- State Management (as per review suggestion 2.2) ---

class MenuState(NamedTuple):
    """Represents the state of the history menu at a given moment."""
    has_selection: bool
    selected_indices: tuple[int, ...]
    first_selected_index: Optional[int]
    is_pinned: bool
    can_undo: bool

class HistoryMenuStateProvider:
    """
    Provides the state for the history context menu by decoupling state
    calculation from the UI.
    """
    def __init__(self, app):
        self.app = app

    def get_menu_state(self, listbox: tk.Listbox) -> MenuState:
        """Calculates and returns the current state of the menu."""
        selected_indices = listbox.curselection()
        has_selection = bool(selected_indices)
        first_selected_index = selected_indices[0] if has_selection else None

        is_pinned = False
        if has_selection:
            history_data = self.app.monitor.get_history()
            if first_selected_index < len(history_data):
                _, is_pinned = history_data[first_selected_index]

        can_undo = self.app.undo_manager.can_undo()

        return MenuState(
            has_selection=has_selection,
            selected_indices=selected_indices,
            first_selected_index=first_selected_index,
            is_pinned=is_pinned,
            can_undo=can_undo,
        )

# --- Base Classes ---

class BaseContextMenu(ABC):
    """Base class for context menus."""
    def __init__(self, master, translator: Optional[Translator] = None, dispatcher: Optional[EventDispatcher] = None):
        self.master = master
        self.menu = tk.Menu(master, tearoff=0)
        self.translator = translator
        self.dispatcher = dispatcher
        self.build_menu()
        
        if self.dispatcher:
            self.dispatcher.subscribe("LANGUAGE_CHANGED", self._rebuild_menu)

    @abstractmethod
    def build_menu(self):
        """Build the menu items. Must be implemented by subclasses."""
        pass

    def _rebuild_menu(self, *args):
        """Clears and rebuilds the menu, typically for language changes."""
        self.menu.delete(0, tk.END)
        self.build_menu()

    def show(self, event):
        """Show the context menu at the event's position."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

# --- Concrete Implementations ---

class HistoryContextMenu(BaseContextMenu):
    """Context menu for the history listbox, with state management separated."""
    def __init__(self, master, app_instance):
        self.app = app_instance
        self.listbox = None
        self.state_provider = HistoryMenuStateProvider(app_instance)
        super().__init__(master, app_instance.translator, app_instance.event_dispatcher)

    def build_menu(self):
        # Dynamic menu, built just before showing.
        pass

    def _rebuild_menu(self, *args):
        # Dynamic menu, no action needed here.
        pass

    def _get_listbox(self):
        if not self.listbox:
            self.listbox = self.app.gui.history_component.listbox
        return self.listbox

    def _build_dynamic_menu(self):
        """Builds the menu based on the current application state."""
        self.menu.delete(0, tk.END)
        listbox = self._get_listbox()
        state = self.state_provider.get_menu_state(listbox)
        self._add_menu_items(state)

    def _add_menu_items(self, state: MenuState):
        """Adds items to the menu based on the provided state."""
        self.menu.add_command(
            label=self.translator("copy_selected"),
            command=lambda: self.dispatcher.dispatch("HISTORY_COPY_SELECTED", state.selected_indices)
        )
        self.menu.add_command(
            label=self.translator("open_as_quick_task"),
            command=lambda: self.dispatcher.dispatch("HISTORY_CREATE_QUICK_TASK", state.selected_indices),
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("format"),
            command=self.app.history_handlers.format_selected_item,
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("delete_selected"),
            command=lambda: self.dispatcher.dispatch("HISTORY_DELETE_SELECTED", state.selected_indices)
        )
        self.menu.add_separator()
        self.menu.add_command(
            label=self.translator("undo"),
            command=lambda: self.dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"),
            state="normal" if state.can_undo else "disabled"
        )
        self.menu.add_separator()
        
        pin_unpin_label = self.translator("unpin") if state.is_pinned else self.translator("pin")
        self.menu.add_command(
            label=pin_unpin_label,
            command=lambda: self.dispatcher.dispatch("HISTORY_PIN_UNPIN", state.first_selected_index),
            state="normal" if state.has_selection else "disabled"
        )

    def show(self, event):
        listbox = self._get_listbox()
        try:
            item_index = listbox.nearest(event.y)
            if not listbox.selection_includes(item_index):
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(item_index)
                listbox.activate(item_index)
        except tk.TclError:
            pass  # Listbox is empty

        self._build_dynamic_menu()
        super().show(event)


class PhraseListContextMenu(BaseContextMenu):
    """Context menu for the phrase listbox."""
    def __init__(self, master, app, phrase_list_component, phrase_edit_component):
        self.list_component = phrase_list_component
        self.edit_component = phrase_edit_component
        super().__init__(master, app.translator, app.event_dispatcher)

    def build_menu(self):
        self.menu.add_command(label=self.translator("copy"), command=self.edit_component._copy_phrase)
        self.menu.add_command(label=self.translator("add"), command=self.edit_component._add_phrase)
        self.menu.add_command(label=self.translator("edit"), command=self.edit_component._edit_phrase)
        self.menu.add_command(label=self.translator("delete"), command=self.edit_component._delete_phrase)

    def show(self, event):
        try:
            item_index = self.list_component.phrase_listbox.nearest(event.y)
            if not self.list_component.phrase_listbox.selection_includes(item_index):
                self.list_component.phrase_listbox.selection_clear(0, tk.END)
                self.list_component.phrase_listbox.selection_set(item_index)
                self.list_component.phrase_listbox.activate(item_index)
        except tk.TclError:
            pass  # Listbox is empty
        super().show(event)
