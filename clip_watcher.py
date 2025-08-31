import tkinter as tk
from src.clipboard_monitor import ClipboardMonitor
from src.gui import ClipWatcherGUI

class Application:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close event

        self.gui = ClipWatcherGUI(master, self.stop_monitor)
        self.monitor = ClipboardMonitor(self.gui.update_clipboard_display)
        self.monitor.start()

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()