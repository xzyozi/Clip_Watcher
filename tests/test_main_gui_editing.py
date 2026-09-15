from __future__ import annotations

from unittest.mock import Mock

from src.gui.main_gui import ClipWatcherGUI


def test_finish_editing_uses_selected_displayed_history_item_id() -> None:
    """検索後も表示行の選択を正しい履歴IDへ結び付けて更新する。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.is_user_editing = True
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
