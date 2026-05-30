from __future__ import annotations

from typing import Any

from src.core.event_dispatcher import EventDispatcher
from src.core.history_service import HistoryService


def test_initial_history_is_empty(history_service: HistoryService) -> None:
    """初期化時点で履歴が空であることを検証します。"""
    assert len(history_service.history) == 0
    assert history_service.last_clipboard_data == ""


def test_add_history_item(history_service: HistoryService, event_dispatcher: EventDispatcher) -> None:
    """新しい履歴項目を追加した際の、状態更新とイベント通知を検証します。"""
    event_data: dict[str, Any] = {}

    def on_updated(data: dict[str, Any]) -> None:
        nonlocal event_data
        event_data = data

    event_dispatcher.subscribe("HISTORY_UPDATED", on_updated)

    # 項目追加
    history_service.add_history_item("Hello World")

    # 内部状態の検証
    assert len(history_service.history) == 1
    assert history_service.last_clipboard_data == "Hello World"
    assert history_service.history[0][0] == "Hello World"
    assert history_service.history[0][1] is False  # 初期状態はピン留め無し

    # イベント通知の検証
    assert event_data != {}
    assert event_data["last_content"] == "Hello World"
    assert len(event_data["history"]) == 1
    assert event_data["history"][0][0] == "Hello World"


def test_add_duplicate_item(history_service: HistoryService) -> None:
    """連続した重複テキストの追加が無視されることを検証します。"""
    history_service.add_history_item("Unique Item")
    assert len(history_service.history) == 1

    # 重複する項目を追加
    history_service.add_history_item("Unique Item")
    # 追加がスキップされていること
    assert len(history_service.history) == 1


def test_cleanup_limit(history_service: HistoryService) -> None:
    """最大件数（このテストでは5件）を超えた際に古い履歴が自動削除されることを検証します。"""
    for i in range(7):
        history_service.add_history_item(f"Item {i}")

    # 上限値5件に収まっていること
    assert len(history_service.history) == 5
    # 最新の5件（Item 2 〜 Item 6）が保持され、古い順に並んでいる（最新が先頭）
    assert history_service.history[0][0] == "Item 6"
    assert history_service.history[4][0] == "Item 2"


def test_update_history_item(history_service: HistoryService) -> None:
    """履歴項目の内容変更が正しくDBおよびメモリに反映されることを検証します。"""
    history_service.add_history_item("Original Text")
    item_id = history_service.history[0][2]

    # コンテンツの変更
    history_service.update_history_item_by_id(item_id, "Updated Text")

    assert history_service.history[0][0] == "Updated Text"
    assert history_service.last_clipboard_data == "Updated Text"


def test_delete_history_item(history_service: HistoryService) -> None:
    """履歴項目の削除が正しく機能することを検証します。"""
    history_service.add_history_item("Item A")
    history_service.add_history_item("Item B")
    assert len(history_service.history) == 2

    target_id = history_service.history[0][2]  # 最新の Item B
    history_service.delete_history_item_by_id(target_id)

    # 1件削除され、Item A だけが残る
    assert len(history_service.history) == 1
    assert history_service.history[0][0] == "Item A"
    assert history_service.last_clipboard_data == "Item A"


def test_pin_unpin_item(history_service: HistoryService) -> None:
    """項目のピン留めおよびピン留め解除により、表示順序が正しく入れ替わることを検証します。"""
    history_service.add_history_item("Normal 1")
    history_service.add_history_item("Normal 2")
    assert len(history_service.history) == 2

    # 通常、最新の "Normal 2" が先頭 (インデックス0)
    assert history_service.history[0][0] == "Normal 2"

    # "Normal 1" の ID を取得してピン留め
    target_id = history_service.history[1][2]
    history_service.pin_item_by_id(target_id)

    # get_history() はピン留めアイテムを先頭にして並べ替える
    ordered_history = history_service.get_history()
    assert ordered_history[0][0] == "Normal 1"
    assert ordered_history[0][1] is True  # ピン留めフラグが True になっていること
    assert ordered_history[1][0] == "Normal 2"

    # ピン留めを解除
    history_service.unpin_item_by_id(target_id)
    ordered_history_after = history_service.get_history()
    assert ordered_history_after[0][0] == "Normal 2"  # 通常の順序に戻る
    assert ordered_history_after[0][1] is False
    assert ordered_history_after[1][1] is False


def test_clear_history(history_service: HistoryService) -> None:
    """全履歴削除が正しく機能することを検証します。"""
    history_service.add_history_item("Item 1")
    history_service.add_history_item("Item 2")
    assert len(history_service.history) == 2

    history_service.clear_history()
    assert len(history_service.history) == 0
    assert history_service.last_clipboard_data == ""


def test_delete_all_unpinned_history(history_service: HistoryService) -> None:
    """ピン留めされていない項目のみが一括削除され、ピン留めされた項目が残ることを検証します。"""
    history_service.add_history_item("Normal 1")
    history_service.add_history_item("To be pinned")
    history_service.add_history_item("Normal 2")

    pin_id = history_service.history[1][2]  # "To be pinned"
    history_service.pin_item_by_id(pin_id)

    assert len(history_service.history) == 3

    # ピン留めされていないものを一括削除
    history_service.delete_all_unpinned_history()

    # ピン留めしたアイテムだけが残る
    assert len(history_service.history) == 1
    assert history_service.history[0][0] == "To be pinned"
    assert history_service.history[0][1] is True


def test_import_history(history_service: HistoryService) -> None:
    """テキストリストを一括インポートした際に、DBへ正しく追加され最大上限でクリーンアップされることを検証します。"""
    import_data = ["Imported A", "Imported B", "Imported C", "Imported D", "Imported E", "Imported F"]

    # 6件インポートするが上限は5件
    history_service.import_history(import_data)

    # 5件に収まっており、並び順が最新（リストの後ろ側）から順にインサートされていること
    assert len(history_service.history) == 5
    assert history_service.history[0][0] == "Imported F"
    assert history_service.history[4][0] == "Imported B"


def test_get_filtered_history(history_service: HistoryService) -> None:
    """部分一致の検索フィルタリングが正しく機能することを検証します。"""
    history_service.add_history_item("Apple")
    history_service.add_history_item("Banana")
    history_service.add_history_item("Pineapple")

    # "apple" で検索（ケースインセンシティブかどうかはDAOの実装に依存するが、部分一致は動作する）
    filtered = history_service.get_filtered_history("apple")

    # Apple と Pineapple の 2件がマッチする
    # ※ sqliteのLIKE検索はデフォルトで大文字小文字を区別しません
    assert len(filtered) == 2
    matched_contents = [item[0] for item in filtered]
    assert "Apple" in matched_contents
    assert "Pineapple" in matched_contents
    assert "Banana" not in matched_contents


def test_settings_changed(history_service: HistoryService, event_dispatcher: EventDispatcher) -> None:
    """設定変更イベントによって制限件数が変更され、あふれた履歴がクリーンアップされることを検証します。"""
    for i in range(5):
        history_service.add_history_item(f"Item {i}")
    assert len(history_service.history) == 5

    # 設定変更イベントを発火（上限を3件に縮小）
    event_dispatcher.dispatch("SETTINGS_CHANGED", {"history_limit": 3})

    # 上限値が3に更新され、履歴があふれた分カットされていること
    assert history_service.history_limit == 3
    assert len(history_service.history) == 3
    # 最新の3件が保持される
    assert history_service.history[0][0] == "Item 4"
    assert history_service.history[2][0] == "Item 2"
