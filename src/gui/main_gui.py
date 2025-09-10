import tkinter as tk
from tkinter import ttk, font
from src.gui import context_menu
from src import config
from src.config import THEMES
from src.gui.fixed_phrases_window import FixedPhrasesFrame # Import the refactored frame

class ClipWatcherGUI:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance
        master.title("ClipWatcher")
        master.geometry(config.MAIN_WINDOW_GEOMETRY)

        self.history_data = []

        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=config.FRAME_PADDING, padx=config.FRAME_PADDING, fill=tk.BOTH, expand=True)

        # Create Clipboard tab
        clipboard_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(clipboard_tab_frame, text="Clipboard")

        self.current_clipboard_frame = tk.LabelFrame(clipboard_tab_frame, text="Current Clipboard Content", padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        self.current_clipboard_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        self.clipboard_text_widget = tk.Text(self.current_clipboard_frame, wrap=tk.WORD, height=5)
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar = tk.Scrollbar(self.current_clipboard_frame, orient="vertical", command=self.clipboard_text_widget.yview)
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.clipboard_text_widget.config(yscrollcommand=self.clipboard_text_scrollbar.set)

        self.clipboard_text_widget.insert(tk.END, "Waiting for clipboard content...")
        self.clipboard_text_widget.config(state=tk.DISABLED)
        self.clipboard_text_widget.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.clipboard_text_widget))

        self.search_frame = tk.Frame(clipboard_tab_frame, padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        self.search_frame.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)

        self.search_label = tk.Label(self.search_frame, text="検索 (Search):")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=config.BUTTON_PADDING_X)
        self.search_entry.bind("<KeyRelease>", lambda event: self.app.history_handlers.handle_search_history(self.search_entry.get()))
        self.search_entry.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.search_entry))

        self.history_frame = tk.LabelFrame(clipboard_tab_frame, text="Clipboard History", padx=config.BUTTON_PADDING_X, pady=config.BUTTON_PADDING_Y)
        self.history_frame.pack(fill=tk.BOTH, expand=True, pady=config.BUTTON_PADDING_Y)

        self.history_listbox = tk.Listbox(self.history_frame, height=10, selectmode=tk.EXTENDED)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.history_scrollbar = tk.Scrollbar(self.history_frame, orient="vertical", command=self.history_listbox.yview)
        self.history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.config(yscrollcommand=self.history_scrollbar.set)

        self.history_listbox.bind("<Double-Button-1>", lambda event: self.app.history_handlers.handle_copy_selected_history())
        self.history_listbox.bind("<Button-3>", lambda event: context_menu.show_history_context_menu(event, self.app))

        self.control_frame = tk.Frame(clipboard_tab_frame)
        self.control_frame.pack(pady=config.FRAME_PADDING)

        self.copy_history_button = tk.Button(self.control_frame, text="Copy Selected to Clipboard", command=self.app.history_handlers.handle_copy_selected_history)
        self.copy_history_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.quit_button = tk.Button(self.control_frame, text="Quit", command=self.app.file_handlers.handle_quit)
        self.quit_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        # Create Fixed Phrases tab
        fixed_phrases_tab_frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
        self.notebook.add(fixed_phrases_tab_frame, text="Fixed Phrases")
        self.fixed_phrases_frame = FixedPhrasesFrame(fixed_phrases_tab_frame, self.app.fixed_phrases_manager)
        self.fixed_phrases_frame.pack(fill=tk.BOTH, expand=True)

    def apply_theme(self, theme_name):
        theme = THEMES.get(theme_name, THEMES["light"])
        self.master.config(bg=theme["bg"])
        
        # Apply theme to notebook and its tabs
        style = ttk.Style()
        style.theme_use('default') # Reset to default to ensure consistent styling before applying custom
        style.configure('TNotebook', background=theme["bg"], bordercolor=theme["frame_bg"])
        style.configure('TNotebook.Tab', background=theme["frame_bg"], foreground=theme["label_fg"], lightcolor=theme["frame_bg"], darkcolor=theme["frame_bg"])
        style.map('TNotebook.Tab', background=[('selected', theme["bg"])], foreground=[('selected', theme["fg"])])
        style.configure('TNotebook.Client', background=theme["frame_bg"])

        # Apply theme to specific widgets within tabs
        # These widgets are now children of the tab frames, not main_frame
        self.current_clipboard_frame.config(bg=theme["frame_bg"], fg=theme["label_fg"])
        self.clipboard_text_widget.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"], insertbackground=theme["fg"])
        self.search_frame.config(bg=theme["bg"])
        self.search_label.config(bg=theme["bg"], fg=theme["label_fg"])
        self.search_entry.config(bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["fg"])
        self.history_frame.config(bg=theme["frame_bg"], fg=theme["label_fg"])
        self.history_listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"],
                                    selectbackground=theme["select_bg"], selectforeground=theme["select_fg"])
        self.control_frame.config(bg=theme["bg"])
        self.copy_history_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
        self.quit_button.config(bg=theme["button_bg"], fg=theme["button_fg"])

        # Apply theme to FixedPhrasesFrame if it exists
        if hasattr(self, 'fixed_phrases_frame'):
            # FixedPhrasesFrame itself is a tk.Frame, so its background can be set directly
            self.fixed_phrases_frame.config(bg=theme["frame_bg"])
            # Its internal widgets (listbox, buttons) also need to be themed.
            # Looking at FixedPhrasesFrame, it uses tk.Listbox and tk.Button, so they need explicit config.
            self.fixed_phrases_frame.phrase_listbox.config(bg=theme["listbox_bg"], fg=theme["listbox_fg"])
            self.fixed_phrases_frame.add_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
            self.fixed_phrases_frame.edit_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
            self.fixed_phrases_frame.delete_button.config(bg=theme["button_bg"], fg=theme["button_fg"])
            # The button_frame inside FixedPhrasesFrame is tk.Frame, so it needs config too.
            self.fixed_phrases_frame.winfo_children()[1].config(bg=theme["frame_bg"])

        self.current_theme_name = theme_name
        self.update_history_display(self.app.monitor.get_filtered_history(self.search_entry.get()))

    def apply_font_settings(self, clipboard_content_font_family, clipboard_content_font_size, history_font_family, history_font_size):
        clipboard_font = font.Font(family=clipboard_content_font_family, size=clipboard_content_font_size)
        history_font = font.Font(family=history_font_family, size=history_font_size)

        self.clipboard_text_widget.config(font=clipboard_font)
        self.history_listbox.config(font=history_font)

    def update_clipboard_display(self, current_content, history):
        self.clipboard_text_widget.config(state=tk.NORMAL)
        self.clipboard_text_widget.delete(1.0, tk.END)
        self.clipboard_text_widget.insert(tk.END, current_content)
        self.clipboard_text_widget.config(state=tk.DISABLED)

        self.history_data = history
        search_query = self.search_entry.get() if hasattr(self, 'search_entry') else ""
        if search_query:
            filtered_history = self.app.monitor.get_filtered_history(search_query)
            self.update_history_display(filtered_history)
        else:
            self.update_history_display(history)

    def update_history_display(self, history_to_display):
        self.history_listbox.delete(0, tk.END)
        
        current_theme = THEMES.get(getattr(self, 'current_theme_name', 'light'), THEMES['light'])
        pinned_bg_color = current_theme["pinned_bg"]

        for i, item_tuple in enumerate(history_to_display):
            content, is_pinned = item_tuple
            display_text = content.replace('\n', ' ').replace('\r', '')
            
            prefix = "📌 " if is_pinned else ""
            self.history_listbox.insert(tk.END, f"{prefix}{i+1}. {display_text[:100]}...")
            
            if is_pinned:
                self.history_listbox.itemconfig(i, {'bg': pinned_bg_color})