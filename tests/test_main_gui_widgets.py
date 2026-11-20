"""ClipWatcherGUI を実 Tk で構築して行う画面レベルのテスト。

アプリ本体（設定・履歴サービス・プラグイン管理など）はモックに置き換え、
ウィジェットの構築、表示更新、選択変更、プラグインタブの生成を検証する。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.events.event_dispatcher import EventDispatcher
from src.db.database_manager import DatabaseManager
from src.gui.main_gui import ClipWatcherGUI

HISTORY = [
    ("pinned item", True, 3.0),
    ("second", False, 2.0),
    ("first", False, 1.0),
]


def _plugin(name: str, frame_factory: Any) -> MagicMock:
    plugin = MagicMock()
    plugin.name = name
    plugin.create_gui_component.side_effect = frame_factory
    return plugin


@pytest.fixture
def app(tmp_path: Path) -> MagicMock:
    app = MagicMock()
    app.translator = lambda key: key
    app.event_dispatcher = EventDispatcher()
    app.db_manager = DatabaseManager(db_path=str(tmp_path / "gui.db"))
    app.theme_manager = MagicMock(
        spec=["get_current_theme", "apply_theme_to_widget_tree"]
    )
    app.theme_manager.get_current_theme.return_value = "light"
    app.settings_manager.settings = {}
    app.settings_manager.get_setting.return_value = True
    app.plugin_manager.get_gui_plugins.return_value = []
    app.history_sort_ascending = False
    app.history_service.last_clipboard_data = ""
    app.history_service.get_filtered_history.return_value = []
    app.get_pinned_hotkey_bindings.return_value = {}
    app.icon_manager = None
    return app


@pytest.fixture
def gui(tk_root: tk.Tk, app: MagicMock) -> Generator[ClipWatcherGUI, None, None]:
    master = tk.Toplevel(tk_root)
    widget = ClipWatcherGUI(master, app)
    widget.pack()
    master.update_idletasks()
    yield widget
    master.destroy()


def _text(gui: ClipWatcherGUI) -> str:
    return gui.clipboard_text_widget.get("1.0", "end-1c")


def _select_row(gui: ClipWatcherGUI, index: int) -> None:
    tree = gui.history_component.tree
    tree.selection_set(tree.get_children()[index])
    gui.update_idletasks()


# --- 構築と表示 ---


def test_gui_builds_clipboard_and_meta_tabs(gui: ClipWatcherGUI) -> None:
    assert len(gui.notebook.tabs()) == 2
    assert gui.notebook.tab(gui.clipboard_tab_frame, "text") == "clipboard_tab"
    assert gui.notebook.tab(gui.meta_management_tab_frame, "text") == (
        "meta_management_tab"
    )
    assert str(gui.format_button.cget("state")) == "disabled"
    assert gui.sort_button.cget("text") == "sort_desc_button"


def test_gui_shows_waiting_message_when_clipboard_is_empty(
    gui: ClipWatcherGUI,
) -> None:
    assert _text(gui) == "waiting_for_clipboard_content"
    assert gui._text_source_item_id is None
    assert gui._text_source_text == "waiting_for_clipboard_content"


def test_gui_shows_current_clipboard_text_when_available(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    app.history_service.last_clipboard_data = "from clipboard"
    app.history_sort_ascending = True
    master = tk.Toplevel(tk_root)
    try:
        widget = ClipWatcherGUI(master, app)
        assert _text(widget) == "from clipboard"
        assert widget.sort_button.cget("text") == "sort_asc_button"
    finally:
        master.destroy()


def test_gui_button_commands_dispatch_events(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    received: list[tuple[str, Any]] = []
    for name in (
        "HISTORY_COPY_SELECTED",
        "HISTORY_TOGGLE_SORT",
        "HISTORY_FORMAT_ITEM",
        "REQUEST_UNDO_LAST_ACTION",
        "REQUEST_REDO_LAST_ACTION",
    ):
        app.event_dispatcher.subscribe(
            name, lambda *args, _n=name: received.append((_n, args))
        )
    gui.update_clipboard_display("", HISTORY)
    _select_row(gui, 1)

    gui.copy_history_button.invoke()
    gui.sort_button.invoke()
    gui.format_button.config(state=tk.NORMAL)
    gui.format_button.invoke()
    gui.undo_button.config(state=tk.NORMAL)
    gui.undo_button.invoke()
    gui.redo_button.config(state=tk.NORMAL)
    gui.redo_button.invoke()

    names = [name for name, _ in received]
    assert names == [
        "HISTORY_COPY_SELECTED",
        "HISTORY_TOGGLE_SORT",
        "HISTORY_FORMAT_ITEM",
        "REQUEST_UNDO_LAST_ACTION",
        "REQUEST_REDO_LAST_ACTION",
    ]
    assert received[0][1] == ([2.0],)


def test_gui_quit_button_uses_file_handler(app: MagicMock, gui: ClipWatcherGUI) -> None:
    gui.quit_button.invoke()
    app.file_handlers.handle_quit.assert_called_once()


def test_gui_search_entry_dispatches_query_on_key_release(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    queries: list[str] = []
    app.event_dispatcher.subscribe("HISTORY_SEARCH", queries.append)
    gui.search_entry.insert(0, "abc")
    gui.search_entry.focus_force()
    gui.update()
    if gui.focus_get() is not gui.search_entry:
        pytest.skip("この環境ではキー入力のフォーカスを確保できません")
    gui.search_entry.event_generate("<KeyRelease>")
    assert queries == ["abc"]


def test_undo_redo_buttons_follow_stack_state(gui: ClipWatcherGUI) -> None:
    gui._update_undo_redo_buttons({"can_undo": True, "can_redo": False})
    assert str(gui.undo_button.cget("state")) == "normal"
    assert str(gui.redo_button.cget("state")) == "disabled"


# --- プラグインタブ ---


def test_plugin_tabs_are_created_for_enabled_plugins(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    plugin = _plugin("Calendar Tool", lambda notebook, _app: tk.Frame(notebook))
    app.plugin_manager.get_gui_plugins.return_value = [plugin]

    gui._create_plugin_tabs()

    assert len(gui.plugin_tab_frames) == 1
    assert len(gui.notebook.tabs()) == 3
    app.settings_manager.get_setting.assert_any_call("show_calendar_tool_tab", True)


def test_plugin_tabs_are_rebuilt_on_settings_change(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    plugin = _plugin("Tool", lambda notebook, _app: tk.Frame(notebook))
    app.plugin_manager.get_gui_plugins.return_value = [plugin]
    gui.on_settings_changed({})
    gui.on_settings_changed({})  # 古いタブは破棄されて重複しない
    assert len(gui.plugin_tab_frames) == 1
    assert len(gui.notebook.tabs()) == 3


def test_disabled_plugin_does_not_get_a_tab(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    plugin = _plugin("Tool", lambda notebook, _app: tk.Frame(notebook))
    app.plugin_manager.get_gui_plugins.return_value = [plugin]
    app.settings_manager.get_setting.return_value = False
    gui._create_plugin_tabs()
    assert gui.plugin_tab_frames == []
    plugin.create_gui_component.assert_not_called()


def test_plugin_tab_creation_survives_plugin_errors(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    def broken(notebook: Any, _app: Any) -> Any:
        raise RuntimeError("plugin failed")

    plugins = [
        _plugin("Broken", broken),
        _plugin("Empty", lambda notebook, _app: None),
        _plugin("Good", lambda notebook, _app: tk.Frame(notebook)),
    ]
    app.plugin_manager.get_gui_plugins.return_value = plugins
    gui._create_plugin_tabs()
    assert len(gui.plugin_tab_frames) == 1


def test_select_tool_tab_selects_matching_tab(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    plugin = _plugin("Tool", lambda notebook, _app: tk.Frame(notebook))
    app.plugin_manager.get_gui_plugins.return_value = [plugin]
    gui._create_plugin_tabs()

    gui.select_tool_tab("Tool")
    selected = gui.notebook.index(gui.notebook.select())
    assert gui.notebook.tab(selected, "text") == "Tool"

    gui.select_tool_tab("Unknown")  # 該当なしは何もしない
    assert gui.notebook.index(gui.notebook.select()) == selected


# --- フォント ---


def test_font_settings_are_applied_with_safe_fallbacks(
    gui: ClipWatcherGUI, caplog: pytest.LogCaptureFixture
) -> None:
    gui.on_font_settings_changed(
        {
            "clipboard_content_font_family": "No Such Font Family",
            "clipboard_content_font_size": 14,
            "history_font_family": "TkDefaultFont",
            "history_font_size": 12,
        }
    )
    assert "No Such Font Family" in caplog.text  # 存在しない名前は安全な代替へ
    assert gui.history_component.current_font is not None


# --- 履歴表示の更新 ---


def test_update_display_lists_history_and_keeps_current_text(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("clip now", HISTORY)
    assert len(gui.history_component.tree.get_children()) == 3
    assert gui.history_data == HISTORY
    assert _text(gui) == "clip now"


def test_update_display_ascending_sort_reverses_each_group(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("", HISTORY, sort_ascending=True)
    assert [item[0] for item in gui.history_component.displayed_history] == [
        "pinned item",
        "first",
        "second",
    ]


def test_update_display_uses_search_results_when_query_present(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    app.history_service.get_filtered_history.return_value = [HISTORY[1]]
    gui.search_entry.insert(0, "sec")
    gui.update_clipboard_display("", HISTORY)
    assert [item[0] for item in gui.history_component.displayed_history] == ["second"]


def test_update_display_is_skipped_while_user_is_editing(gui: ClipWatcherGUI) -> None:
    gui.is_user_editing = True
    gui.update_clipboard_display("ignored", HISTORY)
    assert gui.history_component.displayed_history == []


def test_update_display_shows_selected_item_text(gui: ClipWatcherGUI) -> None:
    gui.update_clipboard_display("clip now", HISTORY)
    _select_row(gui, 1)
    gui.update_clipboard_display("clip now", HISTORY)
    assert _text(gui) == "second"
    assert gui._text_source_item_id == 2.0


def test_update_display_does_not_overwrite_text_being_selected(
    gui: ClipWatcherGUI,
) -> None:
    gui._set_text_area("user is copying this", None)
    with patch.object(gui.clipboard_text_widget, "tag_ranges", return_value=("1.0",)):
        gui.update_clipboard_display("new clipboard", HISTORY)
    assert _text(gui) == "user is copying this"


def test_update_display_keeps_waiting_placeholder_when_nothing_to_show(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("", [])
    assert _text(gui) == "waiting_for_clipboard_content"


# --- 選択変更 ---


def test_selection_change_shows_item_and_enables_format_button(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("", HISTORY)
    gui._on_history_selection_changed({"selected_indices": (2,)})
    assert _text(gui) == "first"
    assert str(gui.format_button.cget("state")) == "normal"


def test_selection_change_with_out_of_range_index_clears_text(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("", HISTORY)
    gui._on_history_selection_changed({"selected_indices": (99,)})
    assert _text(gui) == ""


def test_selection_cleared_falls_back_to_last_clipboard_data(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    app.history_service.last_clipboard_data = "latest"
    gui._on_history_selection_changed({"selected_indices": ()})
    assert _text(gui) == "latest"
    assert str(gui.format_button.cget("state")) == "disabled"


def test_selection_change_commits_pending_edit_first(gui: ClipWatcherGUI) -> None:
    gui.is_user_editing = True
    with patch.object(gui, "finish_editing") as finish:
        gui._on_history_selection_changed({"selected_indices": ()})
    finish.assert_called_once()


# --- 編集の開始・確定 ---


def test_start_editing_without_known_source_uses_selected_item(
    gui: ClipWatcherGUI,
) -> None:
    gui.update_clipboard_display("", HISTORY)
    _select_row(gui, 1)
    gui._text_source_text = None
    gui.start_editing()
    assert gui.is_user_editing is True
    assert (gui.editing_item_id, gui.editing_original_text) == (2.0, "second")


def test_start_editing_without_selection_uses_current_text(
    gui: ClipWatcherGUI,
) -> None:
    gui._text_source_text = None
    gui.start_editing()
    assert gui.editing_item_id is None
    assert gui.editing_original_text == _text(gui)


def test_finish_editing_unselected_text_updates_clipboard(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    gui._set_text_area("original", None)
    gui.start_editing()
    gui.clipboard_text_widget.insert(tk.END, " edited")
    gui.finish_editing()
    app.monitor.update_clipboard.assert_called_once_with("original edited")


def test_finish_editing_ignores_empty_and_unchanged_text(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    gui.finish_editing()  # 編集中でなければ何もしない

    gui._set_text_area("same", 5.0)
    gui.start_editing()
    gui.finish_editing()  # 変更なし
    app.undo_manager.execute_command.assert_not_called()

    gui._set_text_area("", None)
    gui.start_editing()
    gui.finish_editing()  # 空文字は保存しない
    app.monitor.update_clipboard.assert_not_called()


def test_finish_editing_falls_back_to_selection_without_known_source(
    app: MagicMock, gui: ClipWatcherGUI
) -> None:
    gui.update_clipboard_display("", HISTORY)
    _select_row(gui, 1)
    gui._set_text_area("second edited", None)
    gui._text_source_text = None
    gui._text_source_item_id = None
    gui.is_user_editing = True
    gui.finish_editing()
    command = app.undo_manager.execute_command.call_args.args[0]
    assert (command.item_id, command.original_text) == (2.0, "second")


def test_global_click_outside_text_area_finishes_editing(gui: ClipWatcherGUI) -> None:
    event = SimpleNamespace(widget=gui.search_entry)
    with (
        patch.object(gui, "focus_get", return_value=gui.clipboard_text_widget),
        patch.object(gui, "finish_editing") as finish,
    ):
        gui.handle_global_click(event)  # type: ignore[arg-type]
    finish.assert_called_once()

    with (
        patch.object(gui, "focus_get", return_value=gui.search_entry),
        patch.object(gui, "finish_editing") as finish,
    ):
        gui.handle_global_click(event)  # type: ignore[arg-type]
    finish.assert_not_called()
