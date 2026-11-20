"""FileEventHandlers / HistoryEventHandlers / BaseEventHandler の単体テスト。

実際の EventDispatcher を使い、イベント経由で各ハンドラを呼び出す。
アプリ本体・GUI・ダイアログはモックに置き換え、ブロッキングする UI は起動しない。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.events.event_dispatcher import EventDispatcher
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.history_handlers import HistoryEventHandlers

HISTORY = [
    ("alpha", False, 1.0),
    ("beta", True, 2.0),
    ("gamma", False, 3.0),
]

HANDLERS = "src.event_handlers.history_handlers"


# --- FileEventHandlers ---


@pytest.fixture
def file_handlers() -> tuple[FileEventHandlers, MagicMock, EventDispatcher]:
    app = MagicMock()
    dispatcher = EventDispatcher()
    return FileEventHandlers(app, dispatcher), app, dispatcher


def test_file_quit_event_closes_application(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher],
) -> None:
    _, app, dispatcher = file_handlers
    dispatcher.dispatch("FILE_QUIT")
    app.on_closing.assert_called_once()


def test_export_history_writes_items_separated_by_marker(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher], tmp_path: Path
) -> None:
    handlers, app, _ = file_handlers
    app.history_service.get_history.return_value = HISTORY
    target = tmp_path / "out.txt"
    with (
        patch(
            "src.event_handlers.file_handlers.filedialog.asksaveasfilename",
            return_value=str(target),
        ),
        patch("src.event_handlers.file_handlers.messagebox") as box,
    ):
        handlers.handle_export_history()
    assert target.read_text(encoding="utf-8") == "alpha\n---beta\n---gamma\n---"
    box.showinfo.assert_called_once()


def test_export_history_does_nothing_when_dialog_is_cancelled(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher],
) -> None:
    handlers, app, _ = file_handlers
    with (
        patch(
            "src.event_handlers.file_handlers.filedialog.asksaveasfilename",
            return_value="",
        ),
        patch("src.event_handlers.file_handlers.messagebox") as box,
    ):
        handlers.handle_export_history()
    app.history_service.get_history.assert_not_called()
    box.showinfo.assert_not_called()


def test_export_history_reports_errors(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher], tmp_path: Path
) -> None:
    handlers, app, _ = file_handlers
    app.history_service.get_history.side_effect = RuntimeError("db down")
    with (
        patch(
            "src.event_handlers.file_handlers.filedialog.asksaveasfilename",
            return_value=str(tmp_path / "out.txt"),
        ),
        patch("src.event_handlers.file_handlers.messagebox") as box,
    ):
        handlers.handle_export_history()
    box.showerror.assert_called_once()


def test_import_history_splits_on_marker_and_drops_blank_items(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher], tmp_path: Path
) -> None:
    handlers, app, _ = file_handlers
    source = tmp_path / "in.txt"
    source.write_text("first\n---\n  second  \n---\n\n---", encoding="utf-8")
    with (
        patch(
            "src.event_handlers.file_handlers.filedialog.askopenfilename",
            return_value=str(source),
        ),
        patch("src.event_handlers.file_handlers.messagebox") as box,
    ):
        handlers.handle_import_history()
    app.history_service.import_history.assert_called_once_with(["first", "second"])
    box.showinfo.assert_called_once()


def test_import_history_does_nothing_when_dialog_is_cancelled(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher],
) -> None:
    handlers, app, _ = file_handlers
    with patch(
        "src.event_handlers.file_handlers.filedialog.askopenfilename", return_value=""
    ):
        handlers.handle_import_history()
    app.history_service.import_history.assert_not_called()


def test_import_history_reports_missing_file(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher], tmp_path: Path
) -> None:
    handlers, app, _ = file_handlers
    with (
        patch(
            "src.event_handlers.file_handlers.filedialog.askopenfilename",
            return_value=str(tmp_path / "missing.txt"),
        ),
        patch("src.event_handlers.file_handlers.messagebox") as box,
    ):
        handlers.handle_import_history()
    box.showerror.assert_called_once()
    app.history_service.import_history.assert_not_called()


def test_base_handler_cleanup_unsubscribes_everything(
    file_handlers: tuple[FileEventHandlers, MagicMock, EventDispatcher],
) -> None:
    handlers, app, dispatcher = file_handlers
    assert len(handlers._subscriptions) == 3
    handlers.cleanup()
    assert handlers._subscriptions == []
    dispatcher.dispatch("FILE_QUIT")
    app.on_closing.assert_not_called()


# --- HistoryEventHandlers ---


@pytest.fixture
def history_handlers() -> tuple[HistoryEventHandlers, MagicMock, MagicMock]:
    app = MagicMock()
    app.settings_manager.get_setting.return_value = False
    app.history_service.get_history.return_value = HISTORY
    app.remove_pinned_hotkey_binding.return_value = True
    app.clear_pinned_hotkey_bindings.return_value = True
    undo = MagicMock()
    handlers = HistoryEventHandlers(app, EventDispatcher(), undo)
    return handlers, app, undo


def test_history_events_are_routed_to_handlers(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    handlers.dispatcher.dispatch("HISTORY_COPY_SELECTED", [3.0])
    app.master.clipboard_append.assert_called_once_with("gamma")

    handlers.dispatcher.dispatch("REQUEST_UNDO_LAST_ACTION")
    undo.undo.assert_called_once()
    handlers.dispatcher.dispatch("REQUEST_REDO_LAST_ACTION")
    undo.redo.assert_called_once()


def test_copy_selected_ignores_empty_and_unknown_ids(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.handle_copy_selected_history([])
    handlers.handle_copy_selected_history([999.0])
    app.master.clipboard_append.assert_not_called()


def test_copy_selected_swallows_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.history_service.get_history.side_effect = RuntimeError("boom")
    handlers.handle_copy_selected_history([1.0])  # 例外を送出しない
    app.master.clipboard_append.assert_not_called()


def test_copy_warning_flag_without_settings_manager_is_disabled() -> None:
    app = MagicMock()
    app.settings_manager = None
    handlers = HistoryEventHandlers(app, EventDispatcher(), MagicMock())
    assert handlers._copy_warning_enabled() is False


def test_confirm_copy_allows_content_without_risks(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.settings_manager.get_setting.return_value = True
    with patch(f"{HANDLERS}.messagebox.askyesno") as ask:
        assert handlers._confirm_copy_if_risky("just text") is True
    ask.assert_not_called()


def test_confirm_copy_truncates_long_preview_for_risky_content(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.settings_manager.get_setting.return_value = True
    content = "sudo rm -rf /\n" + "x" * 600
    with patch(f"{HANDLERS}.messagebox.askyesno", return_value=True) as ask:
        assert handlers._confirm_copy_if_risky(content) is True
    assert "..." in ask.call_args.args[1]


def test_clear_all_history_clears_service_and_display(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.dispatcher.dispatch("HISTORY_CLEAR_ALL")
    app.history_service.clear_history.assert_called_once()
    app.gui.update_clipboard_display.assert_called_once_with("", [])


def test_clear_all_history_is_aborted_when_hotkeys_cannot_be_released(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.clear_pinned_hotkey_bindings.return_value = False
    handlers.handle_clear_all_history()
    app.history_service.clear_history.assert_not_called()


def test_delete_selected_removes_every_id(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.dispatcher.dispatch("HISTORY_DELETE_SELECTED", [1.0, 3.0])
    deleted = [
        c.args[0] for c in app.history_service.delete_history_item_by_id.call_args_list
    ]
    assert deleted == [1.0, 3.0]


def test_delete_selected_skips_items_whose_hotkey_cannot_be_released(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.remove_pinned_hotkey_binding.side_effect = [False, True]
    handlers.handle_delete_selected_history([1.0, 2.0])
    app.history_service.delete_history_item_by_id.assert_called_once_with(2.0)


def test_delete_selected_handles_empty_selection_and_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.handle_delete_selected_history([])
    app.history_service.delete_history_item_by_id.assert_not_called()

    app.remove_pinned_hotkey_binding.side_effect = RuntimeError("boom")
    handlers.handle_delete_selected_history([1.0])  # 例外を送出しない


@pytest.mark.parametrize("confirmed", [True, False])
def test_delete_all_unpinned_asks_for_confirmation(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
    confirmed: bool,
) -> None:
    handlers, app, _ = history_handlers
    with (
        patch(f"{HANDLERS}.messagebox.askyesno", return_value=confirmed),
        patch(f"{HANDLERS}.messagebox.showinfo") as info,
    ):
        handlers.handle_delete_all_unpinned_history()
    info.assert_called_once()
    assert app.history_service.delete_all_unpinned_history.called is confirmed


def test_pin_unpin_pins_unpinned_item(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.dispatcher.dispatch("HISTORY_PIN_UNPIN", 1.0)
    app.history_service.pin_item_by_id.assert_called_once_with(1.0)


def test_pin_unpin_unpins_pinned_item_after_releasing_hotkey(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.handle_pin_unpin_history(2.0)
    app.remove_pinned_hotkey_binding.assert_called_once_with(2)
    app.history_service.unpin_item_by_id.assert_called_once_with(2.0)


def test_pin_unpin_is_aborted_when_hotkey_cannot_be_released(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.remove_pinned_hotkey_binding.return_value = False
    handlers.handle_pin_unpin_history(2.0)
    app.history_service.unpin_item_by_id.assert_not_called()


def test_pin_unpin_ignores_missing_selection_and_unknown_items(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.handle_pin_unpin_history(None)
    handlers.handle_pin_unpin_history(999.0)
    app.history_service.pin_item_by_id.assert_not_called()
    app.history_service.unpin_item_by_id.assert_not_called()


def test_pin_unpin_swallows_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.history_service.get_history.side_effect = RuntimeError("boom")
    handlers.handle_pin_unpin_history(1.0)  # 例外を送出しない


def test_merged_copy_handles_empty_unknown_and_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.handle_copy_selected_as_merged([])
    handlers.handle_copy_selected_as_merged([999.0])
    app.master.clipboard_append.assert_not_called()

    app.history_service.get_history.side_effect = RuntimeError("boom")
    handlers.handle_copy_selected_as_merged([1.0])  # 例外を送出しない


def test_merged_copy_joins_in_given_order(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    handlers.dispatcher.dispatch("HISTORY_COPY_MERGED", [3.0, 1.0])
    app.master.clipboard_append.assert_called_once_with("gamma\nalpha")


def test_search_with_query_shows_filtered_history(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.history_service.get_filtered_history.return_value = [HISTORY[0]]
    app.history_service.last_clipboard_data = "alpha"
    handlers.dispatcher.dispatch("HISTORY_SEARCH", "alp")
    app.gui.update_clipboard_display.assert_called_once_with("alpha", [HISTORY[0]])


def test_search_with_empty_query_shows_full_history(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    app.history_service.last_clipboard_data = "alpha"
    handlers.handle_search_history("")
    app.gui.update_clipboard_display.assert_called_once_with("alpha", HISTORY)


def test_create_quick_task_opens_dialog_for_known_items(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    with patch("src.gui.windows.quick_task_dialog.QuickTaskDialog") as dialog:
        handlers.handle_create_quick_task([1.0, 999.0, 3.0])
    dialog.assert_called_once_with(
        app.master, app, app.settings_manager, ["alpha", "gamma"]
    )


def test_create_quick_task_ignores_empty_and_unknown_ids(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, _, _ = history_handlers
    with patch("src.gui.windows.quick_task_dialog.QuickTaskDialog") as dialog:
        handlers.handle_create_quick_task([])
        handlers.handle_create_quick_task([999.0])
    dialog.assert_not_called()


def _select(app: MagicMock, indices: tuple[int, ...], ids: list[float]) -> MagicMock:
    component = app.gui.history_component
    component.get_selected_indices.return_value = indices
    component.get_ids_for_indices.return_value = ids
    component.displayed_history = HISTORY
    return component


def test_history_item_edited_executes_update_command(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    _select(app, (0,), [1.0])
    handlers.dispatcher.dispatch(
        "HISTORY_ITEM_EDITED", {"new_text": "new", "original_text": "alpha"}
    )
    command = undo.execute_command.call_args.args[0]
    assert (command.item_id, command.original_text, command.new_text) == (
        1.0,
        "alpha",
        "new",
    )


def test_history_item_edited_without_selection_does_nothing(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    _select(app, (), [])
    handlers.handle_history_item_edited({"new_text": "n", "original_text": "o"})
    undo.execute_command.assert_not_called()


def test_history_item_edited_tolerates_incomplete_event_data(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    _select(app, (0,), [1.0])
    handlers.handle_history_item_edited({"new_text": "only new"})  # KeyError
    undo.execute_command.assert_not_called()


def test_history_item_edited_reports_unexpected_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    _select(app, (0,), [1.0])
    undo.execute_command.side_effect = RuntimeError("boom")
    with patch(f"{HANDLERS}.log_and_show_error") as report:
        handlers.handle_history_item_edited({"new_text": "n", "original_text": "o"})
    report.assert_called_once()


def test_apply_plugin_updates_selected_item_when_text_changes(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    _select(app, (0,), [1.0])
    plugin = MagicMock()
    plugin.process.return_value = "ALPHA"
    handlers.apply_plugin_to_selected_item(plugin)
    command = undo.execute_command.call_args.args[0]
    assert (command.item_id, command.new_text) == (1.0, "ALPHA")


def test_apply_plugin_skips_unchanged_text_and_missing_selection(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, undo = history_handlers
    plugin = MagicMock()
    plugin.process.side_effect = lambda text: text

    _select(app, (), [])
    handlers.apply_plugin_to_selected_item(plugin)
    _select(app, (0,), [1.0])
    handlers.apply_plugin_to_selected_item(plugin)
    _select(app, (10,), [])  # 範囲外
    handlers.apply_plugin_to_selected_item(plugin)
    undo.execute_command.assert_not_called()


def test_apply_plugin_reports_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    _select(app, (0,), [1.0])
    plugin = MagicMock()
    plugin.process.side_effect = RuntimeError("bad plugin")
    with patch(f"{HANDLERS}.log_and_show_error") as report:
        handlers.apply_plugin_to_selected_item(plugin)
    report.assert_called_once()


def test_format_selected_item_applies_chosen_plugin(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    _select(app, (0,), [1.0])
    chosen = MagicMock()
    app.create_toplevel.return_value.selected_plugin = chosen
    with patch.object(handlers, "apply_plugin_to_selected_item") as apply:
        handlers.format_selected_item()
    apply.assert_called_once_with(chosen)


def test_format_selected_item_without_selection_or_choice_does_nothing(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    with patch.object(handlers, "apply_plugin_to_selected_item") as apply:
        _select(app, (), [])
        handlers.format_selected_item()
        app.create_toplevel.assert_not_called()

        _select(app, (0,), [1.0])
        app.create_toplevel.return_value.selected_plugin = None
        handlers.format_selected_item()
    apply.assert_not_called()


@pytest.mark.parametrize("error", [IndexError("no item"), RuntimeError("boom")])
def test_format_selected_item_reports_errors(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
    error: Exception,
) -> None:
    handlers, app, _ = history_handlers
    _select(app, (0,), [1.0])
    app.create_toplevel.side_effect = error
    with patch(f"{HANDLERS}.log_and_show_error") as report:
        handlers.format_selected_item()
    report.assert_called_once()


def test_apply_plugin_index_error_is_reported(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    handlers, app, _ = history_handlers
    component = _select(app, (0,), [1.0])
    component.get_selected_indices.side_effect = IndexError("gone")
    with patch(f"{HANDLERS}.log_and_show_error") as report:
        handlers.apply_plugin_to_selected_item(MagicMock())
    report.assert_called_once()


def test_handlers_accept_arbitrary_event_payloads_via_dispatcher(
    history_handlers: tuple[HistoryEventHandlers, MagicMock, MagicMock],
) -> None:
    """全イベント名が登録済みであること（未登録だと例外が出る実装ではないため件数で確認）。"""
    handlers, _, _ = history_handlers
    names = {name for name, _ in handlers._subscriptions}
    assert {
        "HISTORY_COPY_SELECTED",
        "HISTORY_CLEAR_ALL",
        "HISTORY_DELETE_SELECTED",
        "HISTORY_DELETE_ALL_UNPINNED",
        "HISTORY_PIN_UNPIN",
        "HISTORY_COPY_MERGED",
        "HISTORY_FORMAT_ITEM",
        "HISTORY_SEARCH",
        "HISTORY_CREATE_QUICK_TASK",
        "HISTORY_ITEM_EDITED",
        "REQUEST_UNDO_LAST_ACTION",
        "REQUEST_REDO_LAST_ACTION",
    } <= names
