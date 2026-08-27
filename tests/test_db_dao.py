from __future__ import annotations

import time

from src.db.database_manager import DatabaseManager
from src.db.dto import CategoryDTO, ClipboardHistoryDTO, MetaPhraseDTO

# ==========================================
# DatabaseManager / Schema Tests
# ==========================================


def test_database_initialization(db_manager: DatabaseManager) -> None:
    """初期化時に3つの主要テーブルおよびインデックスが正常に作成されていることを検証します。"""
    conn = db_manager._get_connection()
    cursor = conn.cursor()

    # テーブルの存在確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "t_clipboard_history" in tables
    assert "t_category" in tables
    assert "t_meta_phrase" in tables

    # インデックスの存在確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    assert "idx_history_hash" in indexes
    assert "idx_history_created" in indexes
    assert "idx_meta_phrase_category" in indexes

    conn.close()


# ==========================================
# ClipboardHistoryDAO Tests (4 Items)
# ==========================================


def test_history_dao_add_and_get(db_manager: DatabaseManager) -> None:
    """履歴アイテムを追加し、取得した際に正しく復元されることを検証します。"""
    dao = db_manager.history_dao
    dto = ClipboardHistoryDTO(content="Test DB Content", is_pinned=False)

    # 1. 追加
    new_id = dao.add_item(dto)
    assert new_id > 0

    # 2. 取得
    items = dao.get_items(limit=10)
    assert len(items) == 1
    assert items[0].id == new_id
    assert items[0].content == "Test DB Content"
    assert items[0].is_pinned is False


def test_history_dao_cleanup_old(db_manager: DatabaseManager) -> None:
    """制限件数を超えた古い履歴が正常にクリーンアップ(物理削除)されることを検証します。"""
    dao = db_manager.history_dao

    # 7件追加
    for i in range(7):
        dto = ClipboardHistoryDTO(content=f"Item {i}", is_pinned=False)
        dao.add_item(dto)
        # created_at の順序を確実にするためわずかな遅延
        time.sleep(0.01)

    # 制限数を5件にしてクリーンアップを実行
    dao.cleanup_old(limit=5)

    items = dao.get_items(limit=10)
    assert len(items) == 5
    # 最新の5件 (Item 2 ~ Item 6) が残り、Item 0, Item 1 が削除されていること
    contents = [item.content for item in items]
    assert "Item 6" in contents
    assert "Item 2" in contents
    assert "Item 0" not in contents
    assert "Item 1" not in contents


def test_history_dao_update_content(db_manager: DatabaseManager) -> None:
    """履歴アイテムのコンテンツとハッシュが正しく更新されることを検証します。"""
    dao = db_manager.history_dao
    dto = ClipboardHistoryDTO(content="Original Text", is_pinned=False)
    item_id = dao.add_item(dto)

    new_text = "Updated Text"
    import hashlib

    new_hash = hashlib.sha256(new_text.encode("utf-8")).hexdigest()

    # 更新実行
    success = dao.update_content(item_id, new_text, new_hash)
    assert success is True

    # データベースから再ロード
    items = dao.get_items(limit=1)
    assert items[0].content == "Updated Text"
    assert items[0].content_hash == new_hash


def test_history_dao_pin_item(db_manager: DatabaseManager) -> None:
    """ピン留め状態が正しくトグルされることを検証します。"""
    dao = db_manager.history_dao
    dto = ClipboardHistoryDTO(content="Pin Test Content", is_pinned=False)
    item_id = dao.add_item(dto)

    # 初期状態はFalse
    items = dao.get_items(limit=1)
    assert items[0].is_pinned is False

    # ピン留め有効化 (True)
    success = dao.pin_item(item_id, pin=True)
    assert success is True
    items_pinned = dao.get_items(limit=1)
    assert items_pinned[0].is_pinned is True

    # ピン留め解除 (False)
    success_unpin = dao.pin_item(item_id, pin=False)
    assert success_unpin is True
    items_unpinned = dao.get_items(limit=1)
    assert items_unpinned[0].is_pinned is False


# ==========================================
# CategoryDAO & MetaPhraseDAO Tests (1 Item)
# ==========================================


def test_fixed_phrase_and_category(db_manager: DatabaseManager) -> None:
    """カテゴリ作成(空タイトル可)とそれに紐づく定型文の登録・取得・削除フローを検証します。"""
    cat_dao = db_manager.category_dao
    phrase_dao = db_manager.meta_phrase_dao

    # 1. カテゴリの作成
    cat_dto = CategoryDTO(name="開発用定型文")
    cat_id = cat_dao.add(cat_dto)
    assert cat_id > 0

    # 2. 定型文（空タイトル含む）の追加
    # タイトルあり
    phrase1 = MetaPhraseDTO(
        title="挨拶", content="こんにちは、お疲れ様です。", category_id=cat_id
    )
    p1_id = phrase_dao.add(phrase1)
    assert p1_id > 0

    # タイトルなし (空タイトル) の登録
    phrase2 = MetaPhraseDTO(
        title="", content="タイトルなしの定型文コンテンツです。", category_id=cat_id
    )
    p2_id = phrase_dao.add(phrase2)
    assert p2_id > 0

    # 3. 取得とアサーション
    phrases = phrase_dao.get_by_category(cat_id)
    assert len(phrases) == 2

    # タイトル空文字で取得できていること
    titles = [p.title for p in phrases]
    assert "挨拶" in titles
    assert "" in titles

    # 4. カテゴリ削除時のカスケード削除の確認
    # (外部キー制約 ON DELETE CASCADE がテーブル定義にあるため、カテゴリを消すと中の定型文も消えるはず)
    success_delete = cat_dao.delete(cat_id)
    assert success_delete is True

    # 定型文が自動カスケード削除されて空になっていること
    remaining_phrases = phrase_dao.get_by_category(cat_id)
    assert len(remaining_phrases) == 0
