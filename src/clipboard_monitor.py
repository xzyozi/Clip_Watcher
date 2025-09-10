import time
import threading
import tkinter as tk
import psutil
import win32process
import win32gui
import json # Added
import os   # Added
from src.notification_manager import NotificationManager

class ClipboardMonitor:
    def __init__(self, tk_root, settings_manager, history_file_path, history_limit=50, excluded_apps=None):
        self.tk_root = tk_root
        self.settings_manager = settings_manager
        self.notification_manager = NotificationManager(settings_manager)
        self.update_callback = None
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None
        self.history_file_path = history_file_path # Added
        self.history = self._load_history_from_file() # Modified
        self.history_limit = history_limit
        self.excluded_apps = excluded_apps if excluded_apps is not None else []

    def set_history_limit(self, limit):
        self.history_limit = limit
        if len(self.history) > self.history_limit:
            self.history = self.history[:self.history_limit]
            self._trigger_gui_update()

    def set_excluded_apps(self, excluded_apps):
        self.excluded_apps = excluded_apps

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except Exception as e:
            # print(f"Error getting active process name: {e}")
            return None

    def set_gui_update_callback(self, callback):
        self.update_callback = callback

    def _monitor_clipboard(self):
        while self._running:
            try:
                active_process = self.get_active_process_name()
                if active_process and active_process in self.excluded_apps:
                    time.sleep(1)
                    continue

                current_clipboard_data = self.tk_root.clipboard_get()

                if current_clipboard_data != self.last_clipboard_data:
                    self.last_clipboard_data = current_clipboard_data
                    
                    existing_item_index = -1
                    for i, (content, is_pinned) in enumerate(self.history):
                        if content == current_clipboard_data:
                            existing_item_index = i
                            break

                    if existing_item_index != -1:
                        content_to_move, is_pinned_status = self.history.pop(existing_item_index)
                        self.history.insert(0, (content_to_move, is_pinned_status))
                    else:
                        self.history.insert(0, (current_clipboard_data, False))
                        if len(self.history) > self.history_limit:
                            self.history.pop()

                    self.notification_manager.play_notification_sound()
                    self._trigger_gui_update()

            except tk.TclError:
                pass
            except Exception as e:
                print(f"Error accessing clipboard with Tkinter: {e}")
            time.sleep(1)

    def _trigger_gui_update(self):
        if self.update_callback:
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
        pinned = [item for item in self.history if item[1]]
        unpinned = [item for item in self.history if not item[1]]
        return pinned + unpinned

    def clear_history(self):
        self.history.clear()
        self.last_clipboard_data = ""
        self._trigger_gui_update()

    def delete_history_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_delete = current_display_history[index]
            for i, hist_item in enumerate(self.history):
                if hist_item == item_to_delete:
                    del self.history[i]
                    break
            
            if not self.history:
                self.last_clipboard_data = ""
            self._trigger_gui_update()

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
        self.history = [item for item in self.history if item[1]]
        self._trigger_gui_update()
        print("Monitor: Deleted all unpinned history.")

    def import_history(self, new_history_items):
        for item_content in reversed(new_history_items):
            new_item = (item_content, False)
            existing_item_index = -1
            for i, (content, is_pinned) in enumerate(self.history):
                if content == item_content:
                    existing_item_index = i
                    break
            
            if existing_item_index != -1:
                content_to_move, is_pinned_status = self.history.pop(existing_item_index)
                self.history.insert(0, (content_to_move, is_pinned_status))
            else:
                self.history.insert(0, new_item)
                if len(self.history) > self.history_limit:
                    self.history.pop()
        self._trigger_gui_update()

    def get_filtered_history(self, query):
        filtered_raw = [item for item in self.history if query.lower() in item[0].lower()]
        
        pinned = [item for item in filtered_raw if item[1]]
        unpinned = [item for item in filtered_raw if not item[1]]
        return pinned + unpinned

    def _load_history_from_file(self):
        if os.path.exists(self.history_file_path):
            try:
                with open(self.history_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Ensure loaded data is in the correct format (list of lists/tuples)
                    # Convert lists to tuples for consistency if needed
                    return [(item[0], item[1]) for item in loaded_data if isinstance(item, list) and len(item) == 2]
            except (json.JSONDecodeError, FileNotFoundError):
                # Handle corrupt or missing file
                return []
        return []

    def _save_history_to_file(self):
        try:
            with open(self.history_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"Error saving history to file: {e}")