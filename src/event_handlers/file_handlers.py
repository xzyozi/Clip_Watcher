import tkinter as tk
from tkinter import filedialog, messagebox
from src.event_dispatcher import EventDispatcher

class FileEventHandlers:
    def __init__(self, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher

        # Subscribe to events
        self.event_dispatcher.subscribe("FILE_QUIT", self.handle_quit)
        self.event_dispatcher.subscribe("FILE_EXPORT_HISTORY", self.handle_export_history)
        self.event_dispatcher.subscribe("FILE_IMPORT_HISTORY", self.handle_import_history)

    def handle_quit(self):
        self.event_dispatcher.dispatch("REQUEST_QUIT")

    def handle_export_history(self):
        self.event_dispatcher.dispatch("REQUEST_EXPORT_HISTORY")

    def handle_import_history(self):
        self.event_dispatcher.dispatch("REQUEST_IMPORT_HISTORY")