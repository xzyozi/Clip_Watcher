from __future__ import annotations

from typing import Any

from src.core.events.event_dispatcher import EventDispatcher
from src.services.history_service import HistoryService


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


def test_delete_history_item(history_service: HistoryService, mocker: Any) -> None:
    """同一作成時刻でも最新IDの履歴を削除できることを検証します。"""
    mocker.patch("src.db.dto.time.time", return_value=1.0)

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


def test_settings_changed(
    history_service: HistoryService, event_dispatcher: EventDispatcher, mocker: Any
) -> None:
    """同一作成時刻でも設定縮小時に最新IDの履歴が保持されることを検証します。"""
    mocker.patch("src.db.dto.time.time", return_value=1.0)

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


def test_settings_changed_limit_increase_reloads_from_db(
    history_service: HistoryService, event_dispatcher: EventDispatcher, mocker: Any
) -> None:
    """history_limit が増加した際に、メモリ上の件数を単純比較するだけでなく
    DB から再読み込みされ、増加後の上限までの件数が反映されることを検証します。

    再現シナリオ:
    起動時に SettingsManager がまだファイルを読み込んでいないデフォルト値
    （小さい history_limit）で HistoryService が初期化され、その後
    settings.json 由来の大きい history_limit が SETTINGS_CHANGED で通知される
    ケース（ApplicationBuilder の初期化順序に起因する既知の不具合）。
    """
    # add_history_item()/ClipboardHistoryDTO は created_at に time.time() を
    # 使うため、高速に連続実行すると同一タイムスタンプになり
    # `ORDER BY created_at DESC` の順序が不定になる（既存の技術的負債）。
    # このテストでは順序を安定させるため time.time を単調増加するダミー値に
    # モックする。
    fake_time = iter(float(i) for i in range(1, 1000))
    mocker.patch("src.db.dto.time.time", side_effect=lambda: next(fake_time))

    # フィクスチャの history_limit=5 の状態で7件追加すると、
    # DB側の cleanup_old(5) により DB には最新5件のみ残る。
    for i in range(7):
        history_service.add_history_item(f"Item {i}")
    assert len(history_service.history) == 5
    assert history_service.history_limit == 5

    # DB の cleanup_old が history_limit=5 で動作しているため、
    # 上限拡大後にDB内の全件（5件）が再読込されることを確認する前提として、
    # 事前に DB 側の実件数を確認する。
    db_items_before = history_service.db_manager.history_dao.get_items(limit=None)
    assert len(db_items_before) == 5

    event_data: dict[str, Any] = {}

    def on_updated(data: dict[str, Any]) -> None:
        nonlocal event_data
        event_data = data

    event_dispatcher.subscribe("HISTORY_UPDATED", on_updated)

    # 上限を10に拡大する設定変更イベントを発火する。
    # cleanup_old が limit=5 で既に実行済みのため、DBには5件しか無いが、
    # 上限拡大時に load_history() が呼ばれ、メモリ上の履歴が
    # DBの実件数（5件）と一致した状態で再構築されることを確認する
    # （拡大前の実装では load_history() が呼ばれず、拡大前のメモリ内容の
    # ままになっていた）。
    event_dispatcher.dispatch("SETTINGS_CHANGED", {"history_limit": 10})

    assert history_service.history_limit == 10
    assert len(history_service.history) == 5
    assert history_service.history[0][0] == "Item 6"
    assert history_service.history[4][0] == "Item 2"

    # 上限拡大による再読込でも HISTORY_UPDATED イベントが通知されること
    assert event_data != {}
    assert len(event_data["history"]) == 5


def test_settings_changed_limit_increase_recovers_items_beyond_previous_limit(
    db_manager: Any, event_dispatcher: EventDispatcher
) -> None:
    """小さい history_limit で初期化された直後にDBへ多くの件数が存在する状態から、
    history_limit を増加させた際、DB上の全件が上限拡大後の件数まで復元されることを
    検証します（起動直後にデフォルト値で初期ロードされ、後から設定ファイルの
    大きい history_limit が通知される実際の不具合シナリオを再現する）。
    """
    # HistoryService を経由せず、DAO を直接使って7件のダミー履歴をDBへ投入する
    # （HistoryService.add_history_item は追加ごとに cleanup_old を実行してしまうため、
    #  「DBには小さいlimitを超える件数が既に存在する」状況を作れない）。
    from src.db.dto import ClipboardHistoryDTO

    # created_at=0.0 は ClipboardHistoryDTO.__post_init__ の
    # `if not self.created_at:` 判定で falsy とみなされ time.time() に
    # 上書きされてしまうため、i=0 のケースを避けて 1 始まりの値を使う。
    for i in range(7):
        db_manager.history_dao.add_item(
            ClipboardHistoryDTO(content=f"Preloaded {i}", is_pinned=False, created_at=float(i + 1))
        )

    db_items = db_manager.history_dao.get_items(limit=None)
    assert len(db_items) == 7

    # 起動シーケンスを再現: デフォルト値（小さい上限）で HistoryService を初期化する。
    # コンストラクタ内の load_history() が limit=3 で読み込むため、
    # この時点のメモリ内履歴は3件のみになる。
    service = HistoryService(db_manager=db_manager, event_dispatcher=event_dispatcher, history_limit=3)
    assert len(service.history) == 3

    # settings.json 読み込み完了後に発火する SETTINGS_CHANGED を再現する
    # （history_limit を7以上に拡大）。
    event_dispatcher.dispatch("SETTINGS_CHANGED", {"history_limit": 7})

    assert service.history_limit == 7
    # 拡大前の実装では再読込されず3件のままだったが、修正後はDB上の7件全てが復元される
    assert len(service.history) == 7
    assert service.history[0][0] == "Preloaded 6"
    assert service.history[6][0] == "Preloaded 0"
