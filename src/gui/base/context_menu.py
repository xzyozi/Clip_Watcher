import tkinter as tk
from abc import ABC, abstractmethod

class BaseContextMenu(ABC):
    """Base class for context menus."""
    def __init__(self, master, app):
        self.menu = tk.Menu(master, tearoff=0)
        self.app = app
        self.translator = app.translator
        self.build_menu()
        # Rebuild the menu if the language changes
        self.app.event_dispatcher.subscribe("LANGUAGE_CHANGED", self._rebuild_menu)

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

class HistoryContextMenu(BaseContextMenu):
    """Context menu for the history listbox."""
    def __init__(self, master, app_instance):
        self.listbox = None  # Defer initialization
        super().__init__(master, app_instance)

    def build_menu(self):
        # This menu is dynamic, its content is built just before showing.
        # So, we don't need to pre-build it here or rebuild on language change.
        # The _build_dynamic_menu method is called in show() and uses the translator.
        pass

    def _rebuild_menu(self, *args):
        # This menu is built dynamically in show(), so no action is needed here.
        pass

    def _get_listbox(self):
        if not self.listbox:
            self.listbox = self.app.gui.history_component.listbox
        return self.listbox

    def _build_dynamic_menu(self):
        self.menu.delete(0, tk.END)
        listbox = self._get_listbox()

        has_selection = False
        selected_index = None
        try:
            selected_index = listbox.curselection()[0]
            has_selection = True
        except IndexError:
            pass

        self.menu.add_command(label=self.translator("copy_selected"),
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", listbox.curselection()))

        self.menu.add_command(label=self.translator("open_as_quick_task"),
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_CREATE_QUICK_TASK", listbox.curselection()),
                                 state="normal" if has_selection else "disabled")

        format_state = "normal" if has_selection else "disabled"
        self.menu.add_command(label=self.translator("format"),
                                 command=self.app.history_handlers.format_selected_item,
                                 state=format_state)

        self.menu.add_command(label=self.translator("delete_selected"),
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_DELETE_SELECTED", listbox.curselection()))

        self.menu.add_separator()

        undo_state = "normal" if self.app.undo_manager.can_undo() else "disabled"
        self.menu.add_command(label=self.translator("undo"),
                                 command=lambda: self.app.event_dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"),
                                 state=undo_state)

        self.menu.add_separator()

        pin_unpin_label = self.translator("pin_unpin")
        pin_unpin_state = "disabled"
        if has_selection:
            # Ensure history data is available before accessing
            history_data = self.app.monitor.get_history()
            if selected_index < len(history_data):
                item_tuple = history_data[selected_index]
                is_pinned = item_tuple[1]
                pin_unpin_label = self.translator("unpin") if is_pinned else self.translator("pin")
                pin_unpin_state = "normal"

        self.menu.add_command(label=pin_unpin_label,
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_PIN_UNPIN", selected_index),
                                 state=pin_unpin_state)

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
        super().__init__(master, app)

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
