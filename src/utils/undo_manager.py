from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.events.event_dispatcher import EventDispatcher

DEFAULT_MAX_UNDO_HISTORY: int = 100


class UndoableCommand(ABC):
    """An interface for a command that can be undone."""

    @abstractmethod
    def execute(self) -> None:
        """Executes the command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undoes the command."""
        pass


class UndoManager:
    """Manages undo and redo operations using command objects."""

    def __init__(
        self,
        event_dispatcher: EventDispatcher,
        max_history: int = DEFAULT_MAX_UNDO_HISTORY,
    ) -> None:
        if max_history <= 0:
            raise ValueError(f"max_history must be greater than 0, got {max_history}")
        self.max_history = max_history
        self.undo_stack: deque[UndoableCommand] = deque(maxlen=max_history)
        self.redo_stack: deque[UndoableCommand] = deque(maxlen=max_history)
        self.event_dispatcher = event_dispatcher

    def execute_command(self, command: UndoableCommand) -> None:
        """Executes a command and adds it to the undo stack."""
        command.execute()
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self._dispatch_update()

    def undo(self) -> None:
        """Undoes the last command."""
        if not self.can_undo():
            return
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        self._dispatch_update()

    def redo(self) -> None:
        """Redoes the last undone command."""
        if not self.can_redo():
            return
        command = self.redo_stack.pop()
        command.execute()
        self.undo_stack.append(command)
        self._dispatch_update()

    def can_undo(self) -> bool:
        """Checks if there are any actions to undo."""
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        """Checks if there are any actions to redo."""
        return bool(self.redo_stack)

    def _dispatch_update(self) -> None:
        """Dispatches an event to notify UI about stack changes."""
        self.event_dispatcher.dispatch(
            "UNDO_REDO_STACK_CHANGED",
            {"can_undo": self.can_undo(), "can_redo": self.can_redo()},
        )
