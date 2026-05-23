from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.core.event_dispatcher import EventDispatcher
    from src.gui.components.history_list_component import HistoryListComponent
    from src.gui.components.phrase_edit_component import PhraseEditComponent
    from src.gui.components.phrase_list_component import PhraseListComponent
    from src.utils.i18n import Translator


# --- State Management (as per review suggestion 2.2) ---

class MenuState(NamedTuple):
    """Represents the state of the history menu at a given moment."""
    has_selection: bool
    selected_indices: tuple[int, ...]
    selected_ids: list[float]
    first_selected_id: float | None
    is_pinned: bool
    can_undo: bool

class HistoryMenuStateProvider:
    """
    Provides the state for the history context menu by decoupling state
    calculation from the UI.
    """
    def __init__(self, app: BaseApplication) -> None:
        self.app = app

    def get_menu_state(self, listbox: tk.Listbox) -> MenuState:
        """Calculates and returns the current state of the menu."""
        history_component: HistoryListComponent = self.app.gui.history_component # type: ignore
        selected_indices: tuple[int, ...] = listbox.curselection()
        has_selection: bool = bool(selected_indices)

        selected_ids: list[float] = history_component.get_ids_for_indices(list(selected_indices)) # type: ignore
        first_selected_id: float | None = selected_ids[0] if selected_ids else None

        is_pinned: bool = False
        if has_selection:
            # Use the already available displayed_history in the component
            history_data: list[tuple[str, bool, float]] = history_component.displayed_history # type: ignore
            first_selected_index = selected_indices[0]
            if first_selected_index < len(history_data):
                # Tuple is (content, is_pinned, timestamp)
                is_pinned = history_data[first_selected_index][1]

        can_undo: bool = self.app.undo_manager.can_undo() # type: ignore

        return MenuState(
            has_selection=has_selection,
            selected_indices=selected_indices,
            selected_ids=selected_ids,
            first_selected_id=first_selected_id,
            is_pinned=is_pinned,
            can_undo=can_undo,
        )

# --- Base Classes ---

class BaseContextMenu(ABC):
    """Base class for context menus."""
    def __init__(self, master: tk.Misc, translator: Translator | None = None, dispatcher: EventDispatcher | None = None) -> None:
        self.master = master
        self.menu = tk.Menu(master, tearoff=0)
        self.translator = translator
        self.dispatcher = dispatcher
        self.build_menu()

        if self.dispatcher:
            self.dispatcher.subscribe("LANGUAGE_CHANGED", self._rebuild_menu)

    @abstractmethod
    def build_menu(self) -> None:
        """Build the menu items. Must be implemented by subclasses."""
        pass

    def _rebuild_menu(self, *args: Any) -> None:
        """Clears and rebuilds the menu, typically for language changes."""
        self.menu.delete(0, tk.END)
        self.build_menu()

    def show(self, event: tk.Event) -> None:
        """Show the context menu at the event's position."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

# --- Concrete Implementations ---

class HistoryContextMenu(BaseContextMenu):
    """Context menu for the history listbox, with state management separated."""
    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        self.app = app_instance
        self.listbox: tk.Listbox | None = None
        self.state_provider = HistoryMenuStateProvider(app_instance)
        super().__init__(master, app_instance.translator, app_instance.event_dispatcher) # type: ignore

    def build_menu(self) -> None:
        # Dynamic menu, built just before showing.
        pass

    def _rebuild_menu(self, *args: Any) -> None:
        # Dynamic menu, no action needed here.
        pass

    def _get_listbox(self) -> tk.Listbox:
        if not self.listbox:
            self.listbox = self.app.gui.history_component.listbox # type: ignore
        return self.listbox

    def _build_dynamic_menu(self) -> None:
        """Builds the menu based on the current application state."""
        self.menu.delete(0, tk.END)
        listbox = self._get_listbox()
        state = self.state_provider.get_menu_state(listbox)
        self._add_menu_items(state)

    def _add_menu_items(self, state: MenuState) -> None:
        """Adds items to the menu based on the provided state."""
        self.menu.add_command(
            label=self.translator("copy_selected"), # type: ignore
            command=lambda: self.dispatcher.dispatch("HISTORY_COPY_SELECTED", state.selected_ids), # type: ignore
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("open_as_quick_task"), # type: ignore
            command=lambda: self.dispatcher.dispatch("HISTORY_CREATE_QUICK_TASK", state.selected_ids), # type: ignore
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("format"), # type: ignore
            command=self.app.history_handlers.format_selected_item, # type: ignore
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("delete_selected"), # type: ignore
            command=lambda: self.dispatcher.dispatch("HISTORY_DELETE_SELECTED", state.selected_ids), # type: ignore
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_separator()
        self.menu.add_command(
            label=self.translator("undo"), # type: ignore
            command=lambda: self.dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"), # type: ignore
            state="normal" if state.can_undo else "disabled"
        )
        self.menu.add_separator()

        pin_unpin_label: str = self.translator("unpin") if state.is_pinned else self.translator("pin") # type: ignore
        self.menu.add_command(
            label=pin_unpin_label,
            command=lambda: self.dispatcher.dispatch("HISTORY_PIN_UNPIN", state.first_selected_id), # type: ignore
            state="normal" if state.has_selection else "disabled"
        )

    def show(self, event: tk.Event) -> None:
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
    def __init__(self, master: tk.Misc, app: BaseApplication, phrase_list_component: PhraseListComponent, phrase_edit_component: PhraseEditComponent) -> None:
        self.list_component = phrase_list_component
        self.edit_component = phrase_edit_component
        super().__init__(master, app.translator, app.event_dispatcher) # type: ignore

    def build_menu(self) -> None:
        self.menu.add_command(label=self.translator("copy"), command=self.edit_component._copy_phrase) # type: ignore
        self.menu.add_command(label=self.translator("add"), command=self.edit_component._add_phrase) # type: ignore
        self.menu.add_command(label=self.translator("edit"), command=self.edit_component._edit_phrase) # type: ignore
        self.menu.add_command(label=self.translator("delete"), command=self.edit_component._delete_phrase) # type: ignore

    def show(self, event: tk.Event) -> None:
        try:
            item_index = self.list_component.phrase_listbox.nearest(event.y)
            if not self.list_component.phrase_listbox.selection_includes(item_index):
                self.list_component.phrase_listbox.selection_clear(0, tk.END)
                self.list_component.phrase_listbox.selection_set(item_index)
                self.list_component.phrase_listbox.activate(item_index)
        except tk.TclError:
            pass  # Listbox is empty
        super().show(event)
