import tkinter as tk

class ClipWatcherGUI:
    def __init__(self, master, clipboard_monitor_callback):
        self.master = master
        master.title("ClipWatcher")
        master.geometry("500x300")

        self.clipboard_monitor_callback = clipboard_monitor_callback

        # Main frame for better organization
        self.main_frame = tk.Frame(master, padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Current Clipboard Content Section
        self.current_clipboard_frame = tk.LabelFrame(self.main_frame, text="Current Clipboard Content", padx=5, pady=5)
        self.current_clipboard_frame.pack(fill=tk.X, pady=5)

        self.clipboard_content_var = tk.StringVar()
        self.clipboard_content_var.set("Waiting for clipboard content...")

        self.clipboard_label = tk.Label(self.current_clipboard_frame, textvariable=self.clipboard_content_var, wraplength=450, justify="left")
        self.clipboard_label.pack(fill=tk.X, expand=True)

        # Control Buttons
        self.control_frame = tk.Frame(self.main_frame)
        self.control_frame.pack(pady=10)

        self.quit_button = tk.Button(self.control_frame, text="Quit", command=self.on_quit)
        self.quit_button.pack(side=tk.RIGHT, padx=5)

    def update_clipboard_display(self, content):
        self.clipboard_content_var.set(f"Clipboard Content:\n{content}")

    def on_quit(self):
        # This callback will be set by the main application to stop the monitor
        if self.clipboard_monitor_callback:
            self.clipboard_monitor_callback()
        self.master.quit()
