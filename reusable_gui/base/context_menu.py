from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NamedTuple, Callable

if TYPE_CHECKING:
    from reusable_gui.interfaces import GUIContextProto, EventDispatcherProto, TranslatorProto


# --- State Management ---

class MenuState(NamedTuple):
    """Represents the state of the history menu at a given moment."""
    has_selection: bool
    selected_indices: tuple[int, ...]
    selected_ids: list[float]
    first_selected_id: float | None
    is_pinned: bool
    can_undo: bool


# --- Base Classes ---

class BaseContextMenu(ABC):
    """Base class for context menus."""
    def __init__(self, master: tk.Misc, translator: TranslatorProto, dispatcher: EventDispatcherProto | None = None) -> None:
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
    """Context menu for the history listbox, decoupled from specific handlers."""
    def __init__(
        self,
        master: tk.Misc,
        app_instance: GUIContextProto,
        listbox: tk.Listbox,
        get_state_cb: Callable[[], MenuState],
        action_cb: Callable[[str, Any], None]
    ) -> None:
        self.app = app_instance
        self.listbox = listbox
        self.get_state_cb = get_state_cb
        self.action_cb = action_cb
        super().__init__(master, app_instance.translator, app_instance.event_dispatcher)

    def build_menu(self) -> None:
        # Dynamic menu, built just before showing.
        pass

    def _rebuild_menu(self, *args: Any) -> None:
        # Dynamic menu, no action needed here.
        pass

    def _build_dynamic_menu(self) -> None:
        """Builds the menu based on the current state."""
        self.menu.delete(0, tk.END)
        state = self.get_state_cb()
        self._add_menu_items(state)

    def _add_menu_items(self, state: MenuState) -> None:
        """Adds items to the menu based on the provided state."""
        self.menu.add_command(
            label=self.translator("copy_selected"),
            command=lambda: self.action_cb("copy", state.selected_ids),
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("open_as_quick_task"),
            command=lambda: self.action_cb("quick_task", state.selected_ids),
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("format"),
            command=lambda: self.action_cb("format", state.selected_ids),
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_command(
            label=self.translator("delete_selected"),
            command=lambda: self.action_cb("delete", state.selected_ids),
            state="normal" if state.has_selection else "disabled"
        )
        self.menu.add_separator()
        self.menu.add_command(
            label=self.translator("undo"),
            command=lambda: self.action_cb("undo", None),
            state="normal" if state.can_undo else "disabled"
        )
        self.menu.add_separator()

        pin_unpin_label: str = self.translator("unpin") if state.is_pinned else self.translator("pin")
        self.menu.add_command(
            label=pin_unpin_label,
            command=lambda: self.action_cb("pin_unpin", state.first_selected_id),
            state="normal" if state.has_selection else "disabled"
        )

    def show(self, event: tk.Event) -> None:
        try:
            item_index = self.listbox.nearest(event.y)
            if not self.listbox.selection_includes(item_index):
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(item_index)
                self.listbox.activate(item_index)
        except tk.TclError:
            pass  # Listbox is empty

        self._build_dynamic_menu()
        super().show(event)


class PhraseListContextMenu(BaseContextMenu):
    """Context menu for the phrase listbox, using callbacks to execute actions."""
    def __init__(
        self,
        master: tk.Misc,
        app: GUIContextProto,
        listbox: tk.Listbox,
        copy_cb: Callable[[], None],
        add_cb: Callable[[], None],
        edit_cb: Callable[[], None],
        delete_cb: Callable[[], None]
    ) -> None:
        self.listbox = listbox
        self.copy_cb = copy_cb
        self.add_cb = add_cb
        self.edit_cb = edit_cb
        self.delete_cb = delete_cb
        super().__init__(master, app.translator, app.event_dispatcher)

    def build_menu(self) -> None:
        self.menu.add_command(label=self.translator("copy"), command=self.copy_cb)
        self.menu.add_command(label=self.translator("add"), command=self.add_cb)
        self.menu.add_command(label=self.translator("edit"), command=self.edit_cb)
        self.menu.add_command(label=self.translator("delete"), command=self.delete_cb)

    def show(self, event: tk.Event) -> None:
        try:
            item_index = self.listbox.nearest(event.y)
            if not self.listbox.selection_includes(item_index):
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(item_index)
                self.listbox.activate(item_index)
        except tk.TclError:
            pass  # Listbox is empty
        super().show(event)
