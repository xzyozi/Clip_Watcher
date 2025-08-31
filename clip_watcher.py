import tkinter as tk
import pyperclip
import threading
import time

class ClipWatcher:
    def __init__(self, master):
        self.master = master
        master.title("ClipWatcher")

        self.clipboard_content = tk.StringVar()
        self.clipboard_content.set("Waiting for clipboard content...")

        self.label = tk.Label(master, textvariable=self.clipboard_content, wraplength=400, justify="left")
        self.label.pack(padx=10, pady=10)

        self.quit_button = tk.Button(master, text="Quit", command=master.quit)
        self.quit_button.pack(pady=5)

        self.last_clipboard_data = ""
        self.check_clipboard()

    def check_clipboard(self):
        try:
            current_clipboard_data = pyperclip.paste()
            if current_clipboard_data != self.last_clipboard_data:
                self.last_clipboard_data = current_clipboard_data
                self.clipboard_content.set(f"Clipboard Content:\n{current_clipboard_data}")
        except pyperclip.PyperclipException as e:
            self.clipboard_content.set(f"Error accessing clipboard: {e}")
        
        # Schedule the next check after 1000ms (1 second)
        self.master.after(1000, self.check_clipboard)

if __name__ == "__main__":
    root = tk.Tk()
    app = ClipWatcher(root)
    root.mainloop()
