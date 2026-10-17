from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from src.db.dao.category_dao import CategoryDAO
from src.db.dao.history_dao import ClipboardHistoryDAO
from src.db.dao.meta_phrase_dao import MetaPhraseDAO
from src.db.dto import CategoryDTO, ClipboardHistoryDTO, MetaPhraseDTO


@pytest.fixture
def dao_fixture(
    tmp_path: Path,
) -> tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path]:
    db_file = tmp_path / "test_history_dao.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE t_clipboard_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            is_pinned INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE t_category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE t_meta_phrase (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            FOREIGN KEY(category_id) REFERENCES t_category(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

    lock = threading.Lock()
    h_dao = ClipboardHistoryDAO(str(db_file), lock)
    m_dao = MetaPhraseDAO(str(db_file), lock)
    c_dao = CategoryDAO(str(db_file), lock)
    return h_dao, m_dao, c_dao, db_file


def test_history_dao_like_escape(
    dao_fixture: tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path],
) -> None:
    """LIKE メタ文字 (%, _, /) が正しくエスケープされ意図しない行がヒットしないことを検証 (#119)。"""
    h_dao, _, _, _ = dao_fixture

    h_dao.add_item(ClipboardHistoryDTO(content="100% discount!"))
    h_dao.add_item(ClipboardHistoryDTO(content="1000 discount!"))
    h_dao.add_item(ClipboardHistoryDTO(content="file_name.txt"))
    h_dao.add_item(ClipboardHistoryDTO(content="filename.txt"))
    h_dao.add_item(ClipboardHistoryDTO(content="path/to/resource"))

    # '%' の検索: '100% discount!' のみヒットし、'1000 discount!' はヒットしないこと
    percent_items = h_dao.get_items(query="100%")
    assert len(percent_items) == 1
    assert percent_items[0].content == "100% discount!"

    # '_' の検索: 'file_name.txt' のみヒットし、'filename.txt' はヒットしないこと
    underscore_items = h_dao.get_items(query="file_name")
    assert len(underscore_items) == 1
    assert underscore_items[0].content == "file_name.txt"

    # '/' の検索: 'path/to/resource' がヒットすること
    slash_items = h_dao.get_items(query="path/to")
    assert len(slash_items) == 1
    assert slash_items[0].content == "path/to/resource"


def test_history_dao_cleanup_old_negative_limit(
    dao_fixture: tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path],
) -> None:
    """cleanup_old に負の値が渡されても max(0, limit) で安全に処理されることを検証 (#121)。"""
    h_dao, _, _, _ = dao_fixture

    h_dao.add_item(ClipboardHistoryDTO(content="Item 1", is_pinned=False))
    h_dao.add_item(ClipboardHistoryDTO(content="Pinned Item", is_pinned=True))

    # 負の値を渡してもクラッシュせず、max(0, -5) -> limit=0 として動作（ピン留め以外が削除される）
    h_dao.cleanup_old(limit=-5)

    remaining = h_dao.get_items()
    assert len(remaining) == 1
    assert remaining[0].content == "Pinned Item"


def test_history_dao_cleanup_old_subquery(
    dao_fixture: tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path],
) -> None:
    """cleanup_old がサブクエリで動作し、古い項目のみが削除されることを検証 (#121)。"""
    h_dao, _, _, _ = dao_fixture

    for i in range(10):
        h_dao.add_item(ClipboardHistoryDTO(content=f"Item {i}", is_pinned=False))

    h_dao.cleanup_old(limit=4)

    remaining = h_dao.get_items()
    assert len(remaining) == 4
    contents = [item.content for item in remaining]
    # 最新の4件 (Item 6..9) が残っていること
    assert "Item 9" in contents
    assert "Item 6" in contents
    assert "Item 0" not in contents


def test_history_dao_handles_corrupted_created_at(
    dao_fixture: tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path],
) -> None:
    """created_at が壊れたレコードが存在しても一覧取得全体がフェイルせずフォールバックされることを検証 (#125)。"""
    h_dao, _, _, db_file = dao_fixture

    # 正常なアイテム
    h_dao.add_item(ClipboardHistoryDTO(content="Valid Item"))

    # 直接DBに不正な created_at を注入
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
        ("Corrupted String Item", "hash1", 0, "INVALID_DATETIME"),
    )
    conn.execute(
        "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
        ("Corrupted Empty Item", "hash2", 0, ""),
    )
    conn.commit()
    conn.close()

    items = h_dao.get_items()
    # 正常行と破損行の全3件が取得でき、空リストにならないこと
    assert len(items) == 3
    contents = [item.content for item in items]
    assert "Valid Item" in contents
    assert "Corrupted String Item" in contents
    assert "Corrupted Empty Item" in contents

    # 破損行の created_at が正当な float にフォールバックされていること
    for item in items:
        assert isinstance(item.created_at, float)
        assert item.created_at > 0


def test_meta_phrase_dao_handles_corrupted_created_at(
    dao_fixture: tuple[ClipboardHistoryDAO, MetaPhraseDAO, CategoryDAO, Path],
) -> None:
    """meta_phrase_dao において created_at 破損レコードが存在してもフォールバックされることを検証 (#125)。"""
    _, m_dao, c_dao, db_file = dao_fixture

    cat_id = c_dao.add(CategoryDTO(name="テストカテゴリ"))
    m_dao.add(
        MetaPhraseDTO(title="Valid Title", content="Valid Content", category_id=cat_id)
    )

    # 直接DBに不正な created_at を注入
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "INSERT INTO t_meta_phrase (title, content, category_id, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
        ("Corrupted Phrase", "Corrupted Content", cat_id, 10, "INVALID_DATE"),
    )
    conn.commit()
    conn.close()

    items = m_dao.get_by_category(cat_id)
    assert len(items) == 2
    titles = [item.title for item in items]
    assert "Valid Title" in titles
    assert "Corrupted Phrase" in titles
    for item in items:
        assert isinstance(item.created_at, float)
        assert item.created_at > 0
