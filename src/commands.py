from src.utils.undo_manager import UndoableCommand
from src.clipboard_monitor import ClipboardMonitor

class UpdateHistoryCommand(UndoableCommand):
    """A command to update a history item, which can be undone."""
    def __init__(self, monitor: ClipboardMonitor, index: int, original_text: str, new_text: str):
        self.monitor = monitor
        self.index = index
        self.original_text = original_text
        self.new_text = new_text

    def execute(self):
        """Executes the update, changing the history item to the new text."""
        self.monitor.update_history_item(self.index, self.new_text)

    def undo(self):
        """Undoes the update, reverting the history item to the original text."""
        self.monitor.update_history_item(self.index, self.original_text)
