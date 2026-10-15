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
    gui.is_user_editing = False
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


def test_focus_in_after_selection_moved_to_pinned_item_does_not_overwrite_it() -> None:
    """Issue #163: テキストエリアはAの内容のまま選択だけがピン項目Pへ先に移った状態で
    フォーカスが出入りしても、Pを保存先にして上書きしない。
    """
    history = [
        ("pinned content", True, 1.0),
        ("item A", False, 2.0),
    ]
    gui = _build_gui(
        widget_text="item A",
        selected_indices=(0,),  # 選択は既にピン項目Pへ移動
        displayed_history=history,
        source_item_id=2.0,
        source_text="item A",
    )

    gui.start_editing(Mock())
    gui.finish_editing(Mock())

    gui.app.undo_manager.execute_command.assert_not_called()
    gui.app.monitor.update_clipboard.assert_not_called()


def test_edit_is_committed_to_text_source_item_not_newly_selected_pinned_item() -> None:
    """Issue #163: 編集中に選択が別行(ピン項目)へ移っても、編集内容は由来の項目へ保存する。"""
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
    gui.is_user_editing = True

    gui.finish_editing(Mock())

    gui.app.undo_manager.execute_command.assert_called_once()
    command = gui.app.undo_manager.execute_command.call_args.args[0]
    assert command.item_id == 2.0
    assert command.original_text == "item A"
    assert command.new_text == "item A edited"


def test_selection_change_records_new_text_source() -> None:
    """選択変更でテキストエリアを置換した後は、新しい項目を由来として記録する。"""
    history = [
        ("pinned content", True, 1.0),
        ("item A", False, 2.0),
    ]
    gui = _build_gui(
        widget_text="item A",
        selected_indices=(0,),
        displayed_history=history,
        source_item_id=2.0,
        source_text="item A",
    )

    gui._on_history_selection_changed({"selected_indices": (0,)})

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

    gui.start_editing(Mock())
    gui.finish_editing(Mock())

    gui.app.monitor.update_clipboard.assert_not_called()
