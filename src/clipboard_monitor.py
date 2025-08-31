import pyperclip
import time
import threading

class ClipboardMonitor:
    def __init__(self, update_callback):
        self.update_callback = update_callback
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None

    def _monitor_clipboard(self):
        while self._running:
            try:
                current_clipboard_data = pyperclip.paste()
                if current_clipboard_data != self.last_clipboard_data:
                    self.last_clipboard_data = current_clipboard_data
                    self.update_callback(current_clipboard_data)
            except pyperclip.PyperclipException as e:
                print(f"Error accessing clipboard: {e}") # For debugging, can be logged
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
