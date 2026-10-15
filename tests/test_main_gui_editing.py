from __future__ import annotations

from unittest.mock import Mock

from src.gui.main_gui import ClipWatcherGUI


def test_finish_editing_uses_selected_displayed_history_item_id() -> None:
    """検索後も表示行の選択を正しい履歴IDへ結び付けて更新する。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.is_user_editing = True
    gui._text_source_item_id = 202.0
    gui._text_source_text = "search result"
    gui.clipboard_text_widget = Mock()
    gui.clipboard_text_widget.get.return_value = "edited text"
    gui.history_component = Mock()
    gui.history_component.get_selected_indices.return_value = (0,)
    gui.history_component.displayed_history = [
        ("search result", False, 202.0),
    ]
    gui.history_data = [
        ("different full-history item", False, 101.0),
        ("search result", False, 202.0),
    ]
    gui.app = Mock()

    gui.finish_editing(Mock())

    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 202.0
    assert command.original_text == "search result"
    assert command.new_text == "edited text"


def _build_gui(
    *,
    widget_text: str,
    selected_indices: tuple[int, ...],
    displayed_history: list[tuple[str, bool, float]],
    source_item_id: float | None,
    source_text: str | None,
) -> ClipWatcherGUI:
    """テキストエリアの由来（編集対象の履歴ID・基準テキスト）を持つGUIを組み立てる。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.is_user_editing = True
    gui._text_source_item_id = source_item_id
    gui._text_source_text = source_text
    gui.clipboard_text_widget = Mock()
    gui.clipboard_text_widget.get.return_value = widget_text
    gui.history_component = Mock()
    gui.history_component.get_selected_indices.return_value = selected_indices
    gui.history_component.displayed_history = displayed_history
    gui.format_button = Mock()
    gui.app = Mock()
    gui.app.monitor.last_clipboard_data = "latest clipboard"
    return gui


def test_focus_out_without_edit_does_not_overwrite_newly_selected_pinned_item() -> None:
    """Issue #163: 未編集のFocusOutで、後から選択されたピン項目を上書きしない。

    テキストエリアにはAの内容が残ったまま、選択だけがピン項目Pへ移った状態
    （選択変更イベントよりFocusOutが先に処理されるタイミング）を再現する。
    """
    history = [
        ("pinned content", True, 1.0),
        ("item A", False, 2.0),
    ]
    gui = _build_gui(
        widget_text="item A",  # ユーザー未編集。Aの内容のまま
        selected_indices=(0,),  # 選択は既にピン項目Pへ移動
        displayed_history=history,
        source_item_id=2.0,
        source_text="item A",
    )

    gui.finish_editing(Mock())

    gui.app.undo_manager.execute_command.assert_not_called()
    gui.app.monitor.update_clipboard.assert_not_called()


def test_edit_is_committed_to_original_item_not_newly_selected_pinned_item() -> None:
    """Issue #163: 編集中に別行(ピン項目)を選んでも、編集内容は元の項目へ保存する。"""
    history = [
        ("pinned content", True, 1.0),
        ("item A", False, 2.0),
    ]
    gui = _build_gui(
        widget_text="item A edited",
        selected_indices=(0,),  # 選択は既にピン項目Pへ移動
        displayed_history=history,
        source_item_id=2.0,
        source_text="item A",
    )

    gui.finish_editing(Mock())

    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 2.0
    assert command.original_text == "item A"
    assert command.new_text == "item A edited"


def test_selection_change_commits_pending_edit_before_replacing_text() -> None:
    """Issue #163: 選択変更でテキストエリアを置換する前に、編集中の内容を確定する。"""
    history = [
        ("pinned content", True, 1.0),
        ("item A", False, 2.0),
    ]
    gui = _build_gui(
        widget_text="item A edited",
        selected_indices=(0,),
        displayed_history=history,
        source_item_id=2.0,
        source_text="item A",
    )

    gui._on_history_selection_changed({"selected_indices": (0,)})

    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 2.0
    assert command.new_text == "item A edited"
    # 置換後のテキストエリアはピン項目の由来として記録し直される
    assert gui._text_source_item_id == 1.0
    assert gui._text_source_text == "pinned content"


def test_focus_out_without_edit_on_clipboard_text_does_not_reinsert_entry() -> None:
    """選択なし・未編集のFocusOutでは、現在のクリップボードを履歴へ再投入しない。"""
    gui = _build_gui(
        widget_text="latest clipboard",
        selected_indices=(),
        displayed_history=[("latest clipboard", False, 5.0)],
        source_item_id=None,
        source_text="latest clipboard",
    )

    gui.finish_editing(Mock())

    gui.app.monitor.update_clipboard.assert_not_called()
