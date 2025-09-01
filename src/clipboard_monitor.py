import time
import threading
import tkinter as tk # Import tkinter for clipboard access

class ClipboardMonitor:
    def __init__(self, tk_root, update_callback):
        self.tk_root = tk_root # Store reference to the Tkinter root
        self.update_callback = update_callback
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None
        self.history = []
        self.history_limit = 10 # Limit the history to 10 items

    def _monitor_clipboard(self):
        while self._running:
            try:
                # Use Tkinter's clipboard_get()
                # This needs to be called from the main Tkinter thread.
                # Using after() to schedule it on the main thread.
                # However, the monitor_thread is a separate thread.
                # This is a common challenge when mixing threads and Tkinter.

                # The correct way to get clipboard from a non-main thread
                # is to schedule a call on the main thread and wait for its result.
                # This complicates the simple polling loop.

                # Let's try to get the clipboard content directly.
                # If it fails, it will raise TclError.
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

                    # Update GUI on the main thread
                    self.tk_root.after(0, self.update_callback, current_clipboard_data, self.history)

            except tk.TclError:
                # Clipboard might be empty or contain non-text data
                # print("DEBUG: Tkinter clipboard_get() failed (e.g., empty or non-text).")
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
            # If the deleted item was the last_clipboard_data, reset it
            if not self.history:
                self.last_clipboard_data = ""
            elif self.last_clipboard_data not in self.history:
                # If the current clipboard content is no longer in history,
                # it means it was deleted. We should update the GUI to reflect this.
                # This is a bit tricky as the monitor doesn't directly control GUI.
                # The GUI will be updated on the next clipboard change or when
                # handle_delete_selected_history calls update_clipboard_display.
                pass

    def delete_all_unpinned_history(self):
        # Placeholder for future implementation
        print("Monitor: Deleting all unpinned history (functionality not yet implemented).")
        # In a real implementation, this would iterate through history and remove unpinned items.
        # For now, it does nothing.
