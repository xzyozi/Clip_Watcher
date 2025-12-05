import tkinter as tk

class ContextMenuMixin:
    """
    Adds a right-click context menu with Cut, Copy, Paste, and Select All functionality
    to tkinter Entry and Text widgets.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.cut)
        self.context_menu.add_command(label="Copy", command=self.copy)
        self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self.select_all)

        self.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Display the context menu at the cursor's position."""
        # Enable/disable menu items based on widget state
        has_selection = False
        try:
            if self.selection_get():
                has_selection = True
        except tk.TclError:
            pass # No selection

        can_paste = False
        try:
            if self.clipboard_get():
                can_paste = True
        except tk.TclError:
            pass # Nothing to paste

        self.context_menu.entryconfig("Cut", state=tk.NORMAL if has_selection else tk.DISABLED)
        self.context_menu.entryconfig("Copy", state=tk.NORMAL if has_selection else tk.DISABLED)
        self.context_menu.entryconfig("Paste", state=tk.NORMAL if can_paste else tk.DISABLED)

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def cut(self):
        self.event_generate("<<Cut>>")

    def copy(self):
        self.event_generate("<<Copy>>")

    def paste(self):
        self.event_generate("<<Paste>>")

    def select_all(self):
        """Select all text in the widget."""
        if isinstance(self, tk.Entry):
            self.selection_range(0, tk.END)
        elif isinstance(self, tk.Text):
            self.tag_add(tk.SEL, "1.0", tk.END)
        self.icursor(tk.END) # Move cursor to the end
        return "break" # Prevents other bindings from executing


class CustomEntry(ContextMenuMixin, tk.Entry):
    """
    A tkinter Entry widget with a right-click context menu.
    """
    pass

class CustomText(ContextMenuMixin, tk.Text):
    """
    A tkinter Text widget with a right-click context menu.
    """
    pass