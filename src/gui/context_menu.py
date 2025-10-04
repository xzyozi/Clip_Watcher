import tkinter as tk
from abc import ABC, abstractmethod

class BaseContextMenu(ABC):
    """Base class for context menus."""
    def __init__(self, master):
        self.menu = tk.Menu(master, tearoff=0)
        self.build_menu()

    @abstractmethod
    def build_menu(self):
        """Build the menu items. Must be implemented by subclasses."""
        pass

    def show(self, event):
        """Show the context menu at the event's position."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

class TextWidgetContextMenu(BaseContextMenu):
    """Context menu for text widgets (Text, Entry)."""
    def __init__(self, master, text_widget):
        self.text_widget = text_widget
        super().__init__(master)

    def build_menu(self):
        self.menu.add_command(label="切り取り (Cut)", command=lambda: self.text_widget.event_generate("<<Cut>>"))
        self.menu.add_command(label="コピー (Copy)", command=lambda: self.text_widget.event_generate("<<Copy>>"))
        self.menu.add_command(label="貼り付け (Paste)", command=lambda: self.text_widget.event_generate("<<Paste>>"))
        self.menu.add_separator()
        self.menu.add_command(label="すべて選択 (Select All)", command=lambda: self.text_widget.tag_add(tk.SEL, "1.0", tk.END))

class HistoryContextMenu(BaseContextMenu):
    """Context menu for the history listbox."""
    def __init__(self, master, app_instance):
        self.app = app_instance
        self.listbox = None  # Defer initialization
        super().__init__(master)

    def build_menu(self):
        # This menu is dynamic, so we clear and build it every time.
        # The build_menu in __init__ will build the initial state.
        # The show method will rebuild it before showing.
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

        self.menu.add_command(label="選択項目をコピー (Copy Selected)",
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", listbox.curselection()))

        self.menu.add_command(label="クイックタスクとして開く (Open as Quick Task)",
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_CREATE_QUICK_TASK", listbox.curselection()),
                                 state="normal" if has_selection else "disabled")

        format_state = "normal" if has_selection else "disabled"
        self.menu.add_command(label="フォーマット (Format)",
                                 command=self.app.history_handlers.format_selected_item,
                                 state=format_state)

        self.menu.add_command(label="選択項目を削除 (Delete Selected)",
                                 command=lambda: self.app.event_dispatcher.dispatch("HISTORY_DELETE_SELECTED", listbox.curselection()))

        self.menu.add_separator()

        undo_state = "normal" if self.app.undo_manager.can_undo() else "disabled"
        self.menu.add_command(label="元に戻す (Undo)",
                                 command=lambda: self.app.event_dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION"),
                                 state=undo_state)

        self.menu.add_separator()

        pin_unpin_label = "ピン留め/ピン解除 (Pin/Unpin)"
        pin_unpin_state = "disabled"
        if has_selection:
            item_tuple = self.app.monitor.get_history()[selected_index]
            is_pinned = item_tuple[1]
            pin_unpin_label = "ピン解除 (Unpin)" if is_pinned else "ピン留め (Pin)"
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
    def __init__(self, master, phrase_list_component, phrase_edit_component):
        self.list_component = phrase_list_component
        self.edit_component = phrase_edit_component
        super().__init__(master)

    def build_menu(self):
        self.menu.add_command(label="コピー (Copy)", command=self.edit_component._copy_phrase)
        self.menu.add_command(label="追加 (Add)", command=self.edit_component._add_phrase)
        self.menu.add_command(label="編集 (Edit)", command=self.edit_component._edit_phrase)
        self.menu.add_command(label="削除 (Delete)", command=self.edit_component._delete_phrase)

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
