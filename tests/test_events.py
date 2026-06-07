from __future__ import annotations

from typing import Any

from src.core.events.commands import UpdateHistoryCommand
from src.core.events.event_dispatcher import EventDispatcher
from src.utils.undo_manager import UndoManager

# ==========================================
# EventDispatcher Tests (2 Items)
# ==========================================

def test_event_dispatcher_subscribe_and_dispatch(event_dispatcher: EventDispatcher) -> None:
    """イベントの購読と、正しいペイロードを伴う発火を検証します。"""
    received_data: dict[str, Any] = {}

    def on_event(payload: dict[str, Any]) -> None:
        nonlocal received_data
        received_data = payload

    event_dispatcher.subscribe("TEST_EVENT", on_event)
    event_dispatcher.dispatch("TEST_EVENT", {"key": "value"})

    assert received_data == {"key": "value"}


def test_event_dispatcher_unsubscribe(event_dispatcher: EventDispatcher) -> None:
    """イベントの購読解除後、コールバックが呼び出されないことを検証します。"""
    call_count = 0

    def on_event(payload: dict[str, Any]) -> None:
        nonlocal call_count
        call_count += 1

    event_dispatcher.subscribe("TEST_EVENT", on_event)
    event_dispatcher.dispatch("TEST_EVENT", {})
    assert call_count == 1

    # 購読解除
    event_dispatcher.unsubscribe("TEST_EVENT", on_event)
    event_dispatcher.dispatch("TEST_EVENT", {})

    # 呼び出し回数が 1 のままであること
    assert call_count == 1


# ==========================================
# UndoManager Tests (3 Items)
# ==========================================

class DummyCommand:
    """テスト用のシンプルな Command モック。"""
    def __init__(self) -> None:
        self.execute_called = 0
        self.undo_called = 0

    def execute(self) -> None:
        self.execute_called += 1

    def undo(self) -> None:
        self.undo_called += 1


def test_undo_manager_initial_state(undo_manager: UndoManager) -> None:
    """初期状態で Undo/Redo が共に不可能であることを検証します。"""
    assert undo_manager.can_undo() is False
    assert undo_manager.can_redo() is False


def test_undo_manager_execute_command(undo_manager: UndoManager) -> None:
    """コマンド実行時に正しく実行され、Undoスタックが積まれることを検証します。"""
    command = DummyCommand()

    undo_manager.execute_command(command) # type: ignore

    assert command.execute_called == 1
    assert command.undo_called == 0
    assert undo_manager.can_undo() is True
    assert undo_manager.can_redo() is False


def test_undo_manager_undo_redo_cycle(undo_manager: UndoManager) -> None:
    """UndoとRedoのサイクルで、スタックの状態遷移とコマンドの呼び出しを検証します。"""
    command = DummyCommand()

    undo_manager.execute_command(command) # type: ignore
    assert undo_manager.can_undo() is True
    assert undo_manager.can_redo() is False

    # 1. Undo の実行
    undo_manager.undo()
    assert command.execute_called == 1
    assert command.undo_called == 1
    assert undo_manager.can_undo() is False
    assert undo_manager.can_redo() is True

    # 2. Redo の実行
    undo_manager.redo()
    assert command.execute_called == 2
    assert command.undo_called == 1
    assert undo_manager.can_undo() is True
    assert undo_manager.can_redo() is False


# ==========================================
# UpdateHistoryCommand Tests (1 Item)
# ==========================================

def test_update_history_command_execution(mock_monitor: Any, undo_manager: UndoManager) -> None:
    """UpdateHistoryCommandの実行とUndoにより、レシーバ(Monitor)が正しい引数で駆動されることを検証します。"""
    item_id = 123.0
    original_text = "Before Edit"
    new_text = "After Edit"

    command = UpdateHistoryCommand(
        monitor=mock_monitor,
        item_id=item_id,
        original_text=original_text,
        new_text=new_text
    )

    # 1. コマンド実行の検証
    undo_manager.execute_command(command)
    mock_monitor.update_history_item_by_id.assert_called_once_with(item_id, new_text)

    # 2. Undo の検証
    mock_monitor.update_history_item_by_id.reset_mock()
    undo_manager.undo()
    mock_monitor.update_history_item_by_id.assert_called_once_with(item_id, original_text)

    # 3. Redo の検証
    mock_monitor.update_history_item_by_id.reset_mock()
    undo_manager.redo()
    mock_monitor.update_history_item_by_id.assert_called_once_with(item_id, new_text)
