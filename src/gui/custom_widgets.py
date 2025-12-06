import tkinter as tk

class ContextMenuMixin:
    """
    Adds a right-click context menu with Cut, Copy, Paste, and Select All functionality
    to tkinter Entry and Text widgets.
    """
    def __init__(self, *args, **kwargs):
        app = kwargs.pop('app', None)
        if not app or not hasattr(app, 'translator'):
            raise ValueError("ContextMenuMixin requires an 'app' instance with a 'translator' attribute passed during initialization.")
        self.translator = app.translator

        super().__init__(*args, **kwargs)
        
        self.context_menu = tk.Menu(self, tearoff=0)
        self._build_menu()

        self.bind("<Button-3>", self.show_context_menu)

    def _build_menu(self):
        """Builds the menu with translated labels."""
        self.context_menu.add_command(label=self.translator('cut'), command=self.cut)
        self.context_menu.add_command(label=self.translator('copy'), command=self.copy)
        self.context_menu.add_command(label=self.translator('paste'), command=self.paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.translator('select_all'), command=self.select_all)

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

        self.context_menu.entryconfig(self.translator('cut'), state=tk.NORMAL if has_selection else tk.DISABLED)
        self.context_menu.entryconfig(self.translator('copy'), state=tk.NORMAL if has_selection else tk.DISABLED)
        self.context_menu.entryconfig(self.translator('paste'), state=tk.NORMAL if can_paste else tk.DISABLED)

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
    Requires 'app' instance to be passed for translation.
    e.g., CustomEntry(parent, app=app_instance)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CustomText(ContextMenuMixin, tk.Text):
    """
    A tkinter Text widget with a right-click context menu.
    Requires 'app' instance to be passed for translation.
    e.g., CustomText(parent, app=app_instance)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
