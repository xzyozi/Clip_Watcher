from src.utils.undo_manager import UndoableCommand

from .clipboard_monitor import ClipboardMonitor


class UpdateHistoryCommand(UndoableCommand):
    """A command to update a history item, which can be undone."""
    def __init__(self, monitor: ClipboardMonitor, item_id: float, original_text: str, new_text: str):
        self.monitor = monitor
        self.item_id = item_id
        self.original_text = original_text
        self.new_text = new_text

    def execute(self) -> None:
        """Executes the update, changing the history item to the new text."""
        self.monitor.update_history_item_by_id(self.item_id, self.new_text)

    def undo(self) -> None:
        """Undoes the update, reverting the history item to the original text."""
        self.monitor.update_history_item_by_id(self.item_id, self.original_text)
