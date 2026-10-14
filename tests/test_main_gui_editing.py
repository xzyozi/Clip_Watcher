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


def test_finish_editing_does_not_overwrite_newly_selected_item() -> None:
    """Issue #163: 項目Aの編集中に項目B（ピン留め項目）をクリックしても項目Bが上書きされない。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.clipboard_text_widget = Mock()
    gui.history_component = Mock()
    gui.app = Mock()

    # 初期状態: 項目A（index 1, id 101.0）が選択されている
    gui.history_component.displayed_history = [
        ("PINNED ITEM B", True, 202.0),
        ("Item A", False, 101.0),
    ]
    gui.history_component.get_selected_indices.return_value = (1,)
    gui.clipboard_text_widget.get.return_value = "Item A"

    # ユーザーが編集を開始（フォーカスイン）
    gui.start_editing(Mock())

    # ユーザーがテキストを編集
    gui.clipboard_text_widget.get.return_value = "Item A edited"

    # ユーザーが項目B（index 0）をクリック（選択行が先行して切り替わる）
    gui.history_component.get_selected_indices.return_value = (0,)

    # FocusOut により finish_editing が発火
    gui.finish_editing(Mock())

    # 項目B (202.0) ではなく、編集していた項目A (101.0) に対してのみ更新が走ること
    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 101.0
    assert command.original_text == "Item A"
    assert command.new_text == "Item A edited"


def test_finish_editing_without_text_modification_does_not_execute_command() -> None:
    """Issue #163: テキストエリアをクリックしただけで編集していない場合、別項目をクリックしても更新されない。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.clipboard_text_widget = Mock()
    gui.history_component = Mock()
    gui.app = Mock()

    # 項目A（index 1, id 101.0）を選択中
    gui.history_component.displayed_history = [
        ("PINNED ITEM B", True, 202.0),
        ("Item A", False, 101.0),
    ]
    gui.history_component.get_selected_indices.return_value = (1,)
    gui.clipboard_text_widget.get.return_value = "Item A"

    # テキストエリアをクリック（フォーカスイン）
    gui.start_editing(Mock())

    # 内容は未変更（"Item A" のまま）
    gui.clipboard_text_widget.get.return_value = "Item A"

    # ユーザーが項目Bをクリック（選択行が切り替わる）
    gui.history_component.get_selected_indices.return_value = (0,)

    # FocusOut
    gui.finish_editing(Mock())

    # 何も編集していないのでコマンドは一切実行されないこと（項目Bも項目Aも破壊されない）
    gui.app.undo_manager.execute_command.assert_not_called()


def test_finish_editing_unselected_click_does_not_overwrite_pinned_item() -> None:
    """Issue #163: 未選択状態でテキストエリアをクリックした後にピン項目をクリックしても上書きされない。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.clipboard_text_widget = Mock()
    gui.history_component = Mock()
    gui.app = Mock()

    # 初期状態: 未選択
    gui.history_component.displayed_history = [
        ("PINNED ITEM B", True, 202.0),
    ]
    gui.history_component.get_selected_indices.return_value = ()
    gui.clipboard_text_widget.get.return_value = "Latest Clipboard Content"

    # テキストエリアにフォーカス
    gui.start_editing(Mock())

    # ユーザーがピン留め項目Bをクリック
    gui.history_component.get_selected_indices.return_value = (0,)

    # FocusOut
    gui.finish_editing(Mock())

    # 項目Bが上書きされたり余計な更新が走らないこと
    gui.app.undo_manager.execute_command.assert_not_called()
    gui.app.monitor.update_clipboard.assert_not_called()


def test_selection_changed_commits_pending_edit_before_displaying_new_item() -> None:
    """選択変更イベントが FocusOut より先に発火した場合でも、編集中内容が確定されてから新しい項目が表示される。"""
    gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
    gui.clipboard_text_widget = Mock()
    gui.history_component = Mock()
    gui.app = Mock()
    gui.format_button = Mock()

    gui.history_component.displayed_history = [
        ("PINNED ITEM B", True, 202.0),
        ("Item A", False, 101.0),
    ]
    gui.history_component.get_selected_indices.return_value = (1,)
    gui.clipboard_text_widget.get.return_value = "Item A"

    # 項目Aを編集開始
    gui.start_editing(Mock())
    gui.clipboard_text_widget.get.return_value = "Item A edited"

    # 項目Bをクリックして選択変更イベントが先行して発火
    gui.history_component.get_selected_indices.return_value = (0,)
    gui._on_history_selection_changed({"selected_indices": (0,)})

    # 項目Aの編集内容が正しく確定されていること
    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 101.0
    assert command.original_text == "Item A"
    assert command.new_text == "Item A edited"

    # 新しい選択項目Bの内容がテキストエリアにセットされたこと
    gui.clipboard_text_widget.insert.assert_called_with("end", "PINNED ITEM B")
