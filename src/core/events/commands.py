from __future__ import annotations

from typing import TYPE_CHECKING

from src.utils.undo_manager import UndoableCommand

if TYPE_CHECKING:
    from src.services.history_service import HistoryService


class UpdateHistoryCommand(UndoableCommand):
    """A command to update a history item, which can be undone."""

    def __init__(
        self,
        history_service: HistoryService,
        item_id: float,
        original_text: str,
        new_text: str,
    ):
        self.history_service = history_service
        self.item_id = item_id
        self.original_text = original_text
        self.new_text = new_text

    def execute(self) -> None:
        """Executes the update, changing the history item to the new text."""
        self.history_service.update_history_item_by_id(self.item_id, self.new_text)

    def undo(self) -> None:
        """Undoes the update, reverting the history item to the original text."""
        self.history_service.update_history_item_by_id(self.item_id, self.original_text)
