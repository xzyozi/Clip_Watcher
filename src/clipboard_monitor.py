import time
import threading
import tkinter as tk # Import tkinter for clipboard access

class ClipboardMonitor:
    def __init__(self, tk_root):
        self.tk_root = tk_root # Store reference to the Tkinter root
        self.update_callback = None # Will be set later
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None
        self.history = []
        self.history_limit = 10 # Limit the history to 10 items

    def set_gui_update_callback(self, callback):
        self.update_callback = callback

    def _monitor_clipboard(self):
        while self._running:
            try:
                current_clipboard_data = self.tk_root.clipboard_get()

                # --- DEBUG PRINT ---
                print(f"DEBUG: Pasted from clipboard (tkinter): {current_clipboard_data[:50]}...")
                # --- END DEBUG PRINT ---

                if current_clipboard_data != self.last_clipboard_data:
                    self.last_clipboard_data = current_clipboard_data
                    # Add to history, ensuring no duplicates at the top and limit
                    if current_clipboard_data not in self.history:
                        self.history.insert(0, current_clipboard_data) # Add to the beginning
                        if len(self.history) > self.history_limit:
                            self.history.pop() # Remove the oldest item
                    else:
                        # Move existing item to the top
                        self.history.remove(current_clipboard_data)
                        self.history.insert(0, current_clipboard_data)

                    # Update GUI on the main thread if callback is set
                    if self.update_callback:
                        self.tk_root.after(0, self.update_callback, current_clipboard_data, self.history)

            except tk.TclError:
                pass # Do nothing if clipboard is empty or non-text
            except Exception as e:
                print(f"Error accessing clipboard with Tkinter: {e}") # For other unexpected errors
            time.sleep(1) # Check every 1 second

    def start(self):
        if not self._running:
            self._running = True
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
            self.monitor_thread.start()

    def stop(self):
        self._running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2) # Wait for thread to finish

    def get_history(self):
        return self.history

    def clear_history(self):
        self.history.clear()
        self.last_clipboard_data = "" # Reset last data to ensure next copy is registered

    def delete_history_item(self, index):
        if 0 <= index < len(self.history):
            del self.history[index]
            if not self.history:
                self.last_clipboard_data = ""
            elif self.last_clipboard_data not in self.history:
                pass # GUI will be updated by handle_delete_selected_history

    def delete_all_unpinned_history(self):
        print("Monitor: Deleting all unpinned history (functionality not yet implemented).")

    def import_history(self, new_history_items):
        for item in reversed(new_history_items):
            if item not in self.history:
                self.history.insert(0, item)
                if len(self.history) > self.history_limit:
                    self.history.pop()
            else:
                self.history.remove(item)
                self.history.insert(0, item)
        if self.update_callback: # Update GUI after import
            self.tk_root.after(0, self.update_callback, self.last_clipboard_data, self.history)

    def get_filtered_history(self, query):
        if not query:
            return self.history
        
        filtered = [item for item in self.history if query.lower() in item.lower()]
        return filtered