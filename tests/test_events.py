from __future__ import annotations

from typing import Any

from src.core.events.commands import UpdateHistoryCommand
from src.core.events.event_dispatcher import EventDispatcher
from src.utils.undo_manager import UndoManager

# ==========================================
# EventDispatcher Tests (2 Items)
# ==========================================


def test_event_dispatcher_subscribe_and_dispatch(
    event_dispatcher: EventDispatcher,
) -> None:
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


def test_event_dispatcher_variadic_listeners(event_dispatcher: EventDispatcher) -> None:
    """引数なし、複数位置引数、キーワード引数を伴うリスナーの正常呼び出しを検証します。"""
    no_arg_called = False
    multi_arg_result: tuple[int, str] | None = None
    kw_arg_result: str | None = None

    def no_arg_listener() -> None:
        nonlocal no_arg_called
        no_arg_called = True

    def multi_arg_listener(a: int, b: str) -> None:
        nonlocal multi_arg_result
        multi_arg_result = (a, b)

    def kw_arg_listener(*, name: str) -> None:
        nonlocal kw_arg_result
        kw_arg_result = name

    event_dispatcher.subscribe("NO_ARG_EVENT", no_arg_listener)
    event_dispatcher.dispatch("NO_ARG_EVENT")
    assert no_arg_called is True

    event_dispatcher.subscribe("MULTI_ARG_EVENT", multi_arg_listener)
    event_dispatcher.dispatch("MULTI_ARG_EVENT", 42, "hello")
    assert multi_arg_result == (42, "hello")

    event_dispatcher.subscribe("KW_ARG_EVENT", kw_arg_listener)
    event_dispatcher.dispatch("KW_ARG_EVENT", name="clip_watcher")
    assert kw_arg_result == "clip_watcher"


def test_event_dispatcher_safe_error_logging_with_partial_and_callable_object(
    event_dispatcher: EventDispatcher, monkeypatch: Any
) -> None:
    """functools.partialやcallableオブジェクトの例外発生時も安全にエラーログ出力が行われることを検証します。"""
    import functools

    logged_errors: list[str] = []

    def mock_log_and_show_error(
        title: str, message: str, exc_info: bool = False
    ) -> None:
        logged_errors.append(message)

    monkeypatch.setattr(
        "src.core.events.event_dispatcher.log_and_show_error", mock_log_and_show_error
    )

    # 1. functools.partial の例
    def failing_target(arg: str) -> None:
        raise ValueError("Partial target failure")

    partial_listener = functools.partial(failing_target, "test")
    event_dispatcher.subscribe("PARTIAL_FAIL_EVENT", partial_listener)
    event_dispatcher.dispatch("PARTIAL_FAIL_EVENT")

    assert len(logged_errors) == 1
    assert "ValueError: Partial target failure" in logged_errors[0]

    # 2. __name__ を持たない Callable クラスインスタンスの例
    class CustomCallableListener:
        def __call__(self) -> None:
            raise RuntimeError("Callable object failure")

    callable_listener = CustomCallableListener()
    event_dispatcher.subscribe("CALLABLE_FAIL_EVENT", callable_listener)
    event_dispatcher.dispatch("CALLABLE_FAIL_EVENT")

    assert len(logged_errors) == 2
    assert "RuntimeError: Callable object failure" in logged_errors[1]


def test_event_dispatcher_event_contracts(event_dispatcher: EventDispatcher) -> None:
    """SETTINGS_CHANGED, HISTORY_UPDATED, LANGUAGE_CHANGED などの主要イベント契約を検証します。"""
    settings_received: dict[str, Any] = {}
    history_received: list[dict[str, Any]] = []
    lang_received: str = ""

    def on_settings(payload: dict[str, Any]) -> None:
        nonlocal settings_received
        settings_received = payload

    def on_history(items: list[dict[str, Any]]) -> None:
        nonlocal history_received
        history_received = items

    def on_lang(lang: str) -> None:
        nonlocal lang_received
        lang_received = lang

    event_dispatcher.subscribe("SETTINGS_CHANGED", on_settings)
    event_dispatcher.subscribe("HISTORY_UPDATED", on_history)
    event_dispatcher.subscribe("LANGUAGE_CHANGED", on_lang)

    event_dispatcher.dispatch("SETTINGS_CHANGED", {"theme": "dark"})
    event_dispatcher.dispatch("HISTORY_UPDATED", [{"id": 1, "content": "text"}])
    event_dispatcher.dispatch("LANGUAGE_CHANGED", "ja")

    assert settings_received == {"theme": "dark"}
    assert history_received == [{"id": 1, "content": "text"}]
    assert lang_received == "ja"


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

    undo_manager.execute_command(command)  # type: ignore

    assert command.execute_called == 1
    assert command.undo_called == 0
    assert undo_manager.can_undo() is True
    assert undo_manager.can_redo() is False


def test_undo_manager_undo_redo_cycle(undo_manager: UndoManager) -> None:
    """UndoとRedoのサイクルで、スタックの状態遷移とコマンドの呼び出しを検証します。"""
    command = DummyCommand()

    undo_manager.execute_command(command)  # type: ignore
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


def test_update_history_command_execution(
    mock_monitor: Any, undo_manager: UndoManager
) -> None:
    """UpdateHistoryCommandの実行とUndoにより、レシーバ(Monitor)が正しい引数で駆動されることを検証します。"""
    item_id = 123.0
    original_text = "Before Edit"
    new_text = "After Edit"

    command = UpdateHistoryCommand(
        monitor=mock_monitor,
        item_id=item_id,
        original_text=original_text,
        new_text=new_text,
    )

    # 1. コマンド実行の検証
    undo_manager.execute_command(command)
    mock_monitor.update_history_item_by_id.assert_called_once_with(item_id, new_text)

    # 2. Undo の検証
    mock_monitor.update_history_item_by_id.reset_mock()
    undo_manager.undo()
    mock_monitor.update_history_item_by_id.assert_called_once_with(
        item_id, original_text
    )

    # 3. Redo の検証
    mock_monitor.update_history_item_by_id.reset_mock()
    undo_manager.redo()
    mock_monitor.update_history_item_by_id.assert_called_once_with(item_id, new_text)
