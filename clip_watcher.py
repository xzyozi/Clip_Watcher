import tkinter as tk
from src.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar # Import the menu_bar module

class Application:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close event

        self.gui = ClipWatcherGUI(master, self.stop_monitor)
        # Pass the master (root) object to ClipboardMonitor
        self.monitor = ClipboardMonitor(master, self.gui.update_clipboard_display)
        self.monitor.start()

        # Create and set the menu bar
        self.menubar = menu_bar.create_menu_bar(master, self) # Pass self (Application instance)
        master.config(menu=self.menubar)

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()
