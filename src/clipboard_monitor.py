import time
import threading
import tkinter as tk # Import tkinter for clipboard access

class ClipboardMonitor:
    def __init__(self, tk_root):
        self.tk_root = tk_root
        self.update_callback = None
        self.last_clipboard_data = "" # Stores only the content string
        self._running = False
        self.monitor_thread = None
        self.history = [] # Stores (content, is_pinned) tuples
        self.history_limit = 10

    def set_gui_update_callback(self, callback):
        self.update_callback = callback

    def _monitor_clipboard(self):
        while self._running:
            try:
                current_clipboard_data = self.tk_root.clipboard_get()

                print(f"DEBUG: Pasted from clipboard (tkinter): {current_clipboard_data[:50]}...")

                if current_clipboard_data != self.last_clipboard_data:
                    self.last_clipboard_data = current_clipboard_data
                    
                    # Find if the item already exists in history
                    existing_item_index = -1
                    for i, (content, is_pinned) in enumerate(self.history):
                        if content == current_clipboard_data:
                            existing_item_index = i
                            break

                    if existing_item_index != -1:
                        # Item exists, move it to top, preserving pinned status
                        content_to_move, is_pinned_status = self.history.pop(existing_item_index)
                        self.history.insert(0, (content_to_move, is_pinned_status))
                    else:
                        # New item, add to top as unpinned
                        self.history.insert(0, (current_clipboard_data, False))
                        if len(self.history) > self.history_limit:
                            self.history.pop()

                    self._trigger_gui_update()

            except tk.TclError:
                pass
            except Exception as e:
                print(f"Error accessing clipboard with Tkinter: {e}")
            time.sleep(1)

    def _trigger_gui_update(self):
        # This method ensures GUI update is called on the main thread
        if self.update_callback:
            # Pass the current clipboard content and the sorted history
            self.tk_root.after(0, self.update_callback, self.last_clipboard_data, self.get_history())

    def start(self):
        if not self._running:
            self._running = True
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
            self.monitor_thread.start()

    def stop(self):
        self._running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

    def get_history(self):
        # Return history with pinned items first
        pinned = [item for item in self.history if item[1]]
        unpinned = [item for item in self.history if not item[1]]
        return pinned + unpinned

    def clear_history(self):
        self.history.clear()
        self.last_clipboard_data = ""
        self._trigger_gui_update() # Update GUI after clearing

    def delete_history_item(self, index):
        # Get the actual item from the current history order (which is sorted by pinned status)
        # This requires re-indexing based on the displayed list.
        # A safer way is to pass the actual content to delete, or re-sort history before deleting.
        # For now, let's assume index refers to the index in the *currently displayed* history.
        # We need to find the actual index in self.history.
        
        # Re-sort history to get the current display order
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_delete = current_display_history[index]
            # Find and remove from the actual history list
            for i, hist_item in enumerate(self.history):
                if hist_item == item_to_delete:
                    del self.history[i]
                    break
            
            if not self.history:
                self.last_clipboard_data = ""
            self._trigger_gui_update() # Update GUI after deleting

    def pin_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_pin = current_display_history[index]
            for i, (content, is_pinned) in enumerate(self.history):
                if (content, is_pinned) == item_to_pin:
                    self.history[i] = (content, True)
                    break
            self._trigger_gui_update()

    def unpin_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_unpin = current_display_history[index]
            for i, (content, is_pinned) in enumerate(self.history):
                if (content, is_pinned) == item_to_unpin:
                    self.history[i] = (content, False)
                    break
            self._trigger_gui_update()

    def delete_all_unpinned_history(self):
        self.history = [item for item in self.history if item[1]] # Keep only pinned items
        self._trigger_gui_update()
        print("Monitor: Deleted all unpinned history.")

    def import_history(self, new_history_items):
        for item_content in reversed(new_history_items): # Add in original order
            # When importing, assume they are unpinned initially
            new_item = (item_content, False)
            # Check if content already exists, if so, update its pinned status if needed
            existing_item_index = -1
            for i, (content, is_pinned) in enumerate(self.history):
                if content == item_content:
                    existing_item_index = i
                    break
            
            if existing_item_index != -1:
                # Item exists, move to top, preserving its pinned status
                content_to_move, is_pinned_status = self.history.pop(existing_item_index)
                self.history.insert(0, (content_to_move, is_pinned_status))
            else:
                # New item, add to top as unpinned
                self.history.insert(0, new_item)
                if len(self.history) > self.history_limit:
                    self.history.pop()
        self._trigger_gui_update()

    def get_filtered_history(self, query):
        # Filter the full history (content, is_pinned) tuples
        filtered_raw = [item for item in self.history if query.lower() in item[0].lower()]
        
        # Sort filtered history with pinned items first
        pinned = [item for item in filtered_raw if item[1]]
        unpinned = [item for item in filtered_raw if not item[1]]
        return pinned + unpinned
