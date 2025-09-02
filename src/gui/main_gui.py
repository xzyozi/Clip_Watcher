import tkinter as tk
from src.event_handlers import main_handlers as event_handlers
from src.gui import context_menu # Import the context_menu module

class ClipWatcherGUI:
    def __init__(self, master, clipboard_monitor_callback, monitor_instance): # Added monitor_instance
        self.master = master
        master.title("ClipWatcher")
        master.geometry("600x500") # Increased size to accommodate history

        self.clipboard_monitor_callback = clipboard_monitor_callback
        self.monitor_instance = monitor_instance # Store monitor instance
        self.history_data = [] # To store the full history content

        # Main frame for better organization
        self.main_frame = tk.Frame(master, padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Current Clipboard Content Section
        self.current_clipboard_frame = tk.LabelFrame(self.main_frame, text="Current Clipboard Content", padx=5, pady=5)
        self.current_clipboard_frame.pack(fill=tk.X, pady=5)

        # Replace Label with Text widget for scrollability
        self.clipboard_text_widget = tk.Text(self.current_clipboard_frame, wrap=tk.WORD, height=5) # height to control initial size
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar = tk.Scrollbar(self.current_clipboard_frame, orient="vertical", command=self.clipboard_text_widget.yview)
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.clipboard_text_widget.config(yscrollcommand=self.clipboard_text_scrollbar.set)

        # Initial content
        self.clipboard_text_widget.insert(tk.END, "Waiting for clipboard content...")
        self.clipboard_text_widget.config(state=tk.DISABLED) # Make it read-only
        # Bind right-click to show context menu for clipboard_text_widget
        self.clipboard_text_widget.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.clipboard_text_widget))


        # Search Section
        self.search_frame = tk.Frame(self.main_frame, padx=5, pady=5)
        self.search_frame.pack(fill=tk.X, pady=5)

        self.search_label = tk.Label(self.search_frame, text="検索 (Search):")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Bind KeyRelease event for real-time filtering
        # Use self.monitor_instance instead of self.master.monitor
        self.search_entry.bind("<KeyRelease>", lambda event: event_handlers.handle_search_history(self.search_entry.get(), self.monitor_instance, self))
        # Bind right-click to show context menu for entry
        self.search_entry.bind("<Button-3>", lambda event: context_menu.show_text_widget_context_menu(event, self.search_entry))


        # Clipboard History Section
        self.history_frame = tk.LabelFrame(self.main_frame, text="Clipboard History", padx=5, pady=5)
        self.history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.history_listbox = tk.Listbox(self.history_frame, height=10)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.history_scrollbar = tk.Scrollbar(self.history_frame, orient="vertical", command=self.history_listbox.yview)
        self.history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.config(yscrollcommand=self.history_scrollbar.set)

        # Bind double-click to copy, calling event_handlers
        self.history_listbox.bind("<Double-Button-1>", lambda event: event_handlers.handle_copy_selected_history(self, self.history_data, self.history_listbox.curselection()[0]))
        # Bind right-click to show context menu
        self.history_listbox.bind("<Button-3>", lambda event: context_menu.show_history_context_menu(event, self, self.monitor_instance))


        # Control Buttons
        self.control_frame = tk.Frame(self.main_frame)
        self.control_frame.pack(pady=10)

        # Command for copy button, calling event_handlers
        self.copy_history_button = tk.Button(self.control_frame, text="Copy Selected to Clipboard", command=lambda: event_handlers.handle_copy_selected_history(self, self.history_data, self.history_listbox.curselection()[0]))
        self.copy_history_button.pack(side=tk.LEFT, padx=5)

        # Command for quit button, calling event_handlers
        self.quit_button = tk.Button(self.control_frame, text="Quit", command=lambda: event_handlers.handle_quit(self.clipboard_monitor_callback, self.master))
        self.quit_button.pack(side=tk.RIGHT, padx=5)

    def update_clipboard_display(self, current_content, history):
        self.clipboard_text_widget.config(state=tk.NORMAL) # Enable editing to update
        self.clipboard_text_widget.delete(1.0, tk.END) # Clear existing content
        self.clipboard_text_widget.insert(tk.END, current_content)
        self.clipboard_text_widget.config(state=tk.DISABLED) # Make it read-only again

        self.history_data = history # Store the full history
        # When updating, also apply current search filter if any
        search_query = self.search_entry.get() if hasattr(self, 'search_entry') else ""
        if search_query:
            # Re-filter history based on current search query using monitor_instance
            filtered_history = self.monitor_instance.get_filtered_history(search_query)
            self.update_history_display(filtered_history)
        else:
            self.update_history_display(history)

    def update_history_display(self, history_to_display): # Renamed parameter for clarity
        self.history_listbox.delete(0, tk.END) # Clear existing items
        for i, item in enumerate(history_to_display):
            display_text = item.replace('\n', ' ').replace('\r', '') # Single line for display
            self.history_listbox.insert(tk.END, f"{i+1}. {display_text[:100]}...") # Show first 100 chars
