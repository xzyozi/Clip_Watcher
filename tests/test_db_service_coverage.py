"""DAO・DatabaseManager・HistoryService の正常系と異常系を補うテスト。

既存の test_db_dao.py / test_history_service.py が扱わない経路（更新・削除・
エラー時のフォールバック・JSON 移行・設定変更時の上限更新）を検証する。
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.events.event_dispatcher import EventDispatcher
from src.db.database_manager import DatabaseManager
from src.db.dto import CategoryDTO, ClipboardHistoryDTO, MetaPhraseDTO
from src.services.history_service import HistoryService


def _boom(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("boom")


def _broken_connection(exc: Exception) -> MagicMock:
    """execute 系が必ず例外を送出する SQLite 接続のモックを返す。"""
    conn = MagicMock()
    conn.execute.side_effect = exc
    conn.cursor.return_value.execute.side_effect = exc
    return conn


@pytest.fixture
def manager(tmp_path: Path) -> DatabaseManager:
    return DatabaseManager(db_path=str(tmp_path / "data" / "cw.db"))


# --- DatabaseManager ---


def test_manager_creates_missing_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "cw.db"
    DatabaseManager(db_path=str(db_path))
    assert db_path.exists()


def test_manager_reuses_existing_database_file(tmp_path: Path) -> None:
    db_path = str(tmp_path / "cw.db")
    first = DatabaseManager(db_path=db_path)
    first.history_dao.add_item(ClipboardHistoryDTO(content="keep me"))
    second = DatabaseManager(db_path=db_path)
    assert [d.content for d in second.history_dao.get_items()] == ["keep me"]


def test_manager_supports_in_memory_path() -> None:
    manager = DatabaseManager(db_path=":memory:")
    assert manager.db_path == ":memory:"


def test_manager_initialize_tables_reraises_sqlite_errors(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = _broken_connection(sqlite3.OperationalError("disk I/O error"))
    monkeypatch.setattr(manager, "_get_connection", lambda: conn)
    with pytest.raises(sqlite3.OperationalError):
        manager._initialize_tables()
    conn.close.assert_called_once()


def _write_history_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_migrate_imports_all_supported_item_shapes(
    manager: DatabaseManager, tmp_path: Path
) -> None:
    source = _write_history_json(
        tmp_path / "history.json",
        [
            ["newest", True, 300.0],
            ["bad time", False, "not-a-number"],
            ["only content"],
            "plain string",
            ["", False, 1.0],  # 空文字列は移行しない
            ["newest", False, 400.0],  # 重複はピン留めを維持して統合
            [None, False, 1.0],  # content が None の場合は移行しない
            123,  # 想定外の型は無視
        ],
    )

    manager.check_and_migrate_json(str(source))

    items = {d.content: d for d in manager.history_dao.get_items()}
    assert set(items) == {"newest", "bad time", "only content", "plain string"}
    assert items["newest"].is_pinned is True
    # 古い順（リストの末尾から）に処理するため、リスト先頭側の値で最後に更新される
    assert items["newest"].created_at == 300.0
    # 移行完了後は元ファイルが .bak に退避される
    assert not source.exists()
    assert (tmp_path / "history.json.bak").exists()


def test_migrate_skips_missing_file(manager: DatabaseManager, tmp_path: Path) -> None:
    manager.check_and_migrate_json(str(tmp_path / "missing.json"))
    assert manager.history_dao.get_items() == []


def test_migrate_skips_non_list_json(manager: DatabaseManager, tmp_path: Path) -> None:
    source = _write_history_json(tmp_path / "history.json", {"not": "a list"})
    manager.check_and_migrate_json(str(source))
    assert manager.history_dao.get_items() == []
    assert source.exists()  # 失敗時は退避しない


def test_migrate_ignores_broken_json(manager: DatabaseManager, tmp_path: Path) -> None:
    source = tmp_path / "history.json"
    source.write_text("{broken", encoding="utf-8")
    manager.check_and_migrate_json(str(source))
    assert manager.history_dao.get_items() == []
    assert source.exists()


def test_migrate_rejects_symlink(manager: DatabaseManager, tmp_path: Path) -> None:
    target = _write_history_json(tmp_path / "real.json", [["x", False, 1.0]])
    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("シンボリックリンクを作成できない環境です")
    manager.check_and_migrate_json(str(link))
    assert manager.history_dao.get_items() == []


def test_migrate_rolls_back_on_sqlite_error(
    manager: DatabaseManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _write_history_json(tmp_path / "history.json", [["a", False, 1.0]])
    conn = _broken_connection(sqlite3.OperationalError("locked"))
    monkeypatch.setattr(manager, "_get_connection", lambda: conn)
    manager.check_and_migrate_json(str(source))
    conn.rollback.assert_called_once()
    conn.close.assert_called_once()
    assert source.exists()


def test_migrate_rolls_back_on_unexpected_error(
    manager: DatabaseManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _write_history_json(tmp_path / "history.json", [["a", False, 1.0]])
    conn = _broken_connection(RuntimeError("unexpected"))
    monkeypatch.setattr(manager, "_get_connection", lambda: conn)
    manager.check_and_migrate_json(str(source))
    conn.rollback.assert_called_once()
    assert source.exists()


# --- CategoryDAO ---


def test_category_crud_and_ordering(manager: DatabaseManager) -> None:
    dao = manager.category_dao
    first = dao.add(CategoryDTO(name="  Work  "))
    second = dao.add(CategoryDTO(name="Home"))
    assert first > 0 and second > first

    categories = dao.get_all()
    assert [c.name for c in categories] == ["Work", "Home"]
    assert [c.sort_order for c in categories] == [1, 2]

    assert dao.update(CategoryDTO(name="Office", id=first)) is True
    assert [c.name for c in dao.get_all()] == ["Office", "Home"]

    assert dao.delete(second) is True
    assert [c.name for c in dao.get_all()] == ["Office"]


def test_category_duplicate_name_is_rejected(manager: DatabaseManager) -> None:
    dao = manager.category_dao
    first = dao.add(CategoryDTO(name="Same"))
    assert dao.add(CategoryDTO(name="Same")) == -1
    other = dao.add(CategoryDTO(name="Other"))
    assert dao.update(CategoryDTO(name="Same", id=other)) is False
    assert first > 0


def test_category_update_and_delete_report_missing_rows(
    manager: DatabaseManager,
) -> None:
    dao = manager.category_dao
    assert dao.update(CategoryDTO(name="No id")) is False
    assert dao.update(CategoryDTO(name="Ghost", id=999)) is False
    assert dao.delete(999) is False


def test_category_meta_phrase_count(manager: DatabaseManager) -> None:
    category_id = manager.category_dao.add(CategoryDTO(name="Greetings"))
    assert manager.category_dao.get_meta_phrase_count(category_id) == 0
    manager.meta_phrase_dao.add(MetaPhraseDTO("hi", "Hello", category_id))
    manager.meta_phrase_dao.add(MetaPhraseDTO("bye", "Goodbye", category_id))
    assert manager.category_dao.get_meta_phrase_count(category_id) == 2


def test_category_add_returns_minus_one_on_sqlite_error(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = _broken_connection(sqlite3.OperationalError("disk full"))
    monkeypatch.setattr(manager.category_dao, "_get_connection", lambda: conn)
    assert manager.category_dao.add(CategoryDTO(name="x")) == -1
    conn.close.assert_called_once()


def test_category_dao_read_and_write_failures_use_safe_defaults(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    dao = manager.category_dao
    monkeypatch.setattr(dao, "execute_read", _boom)
    monkeypatch.setattr(dao, "execute_update", _boom)
    assert dao.get_all() == []
    assert dao.get_meta_phrase_count(1) == 0
    assert dao.update(CategoryDTO(name="x", id=1)) is False
    assert dao.delete(1) is False


# --- MetaPhraseDAO ---


def test_meta_phrase_crud_and_filtering(manager: DatabaseManager) -> None:
    cats = manager.category_dao
    dao = manager.meta_phrase_dao
    work = cats.add(CategoryDTO(name="Work"))
    home = cats.add(CategoryDTO(name="Home"))
    a = dao.add(MetaPhraseDTO("greet", "Hello", work))
    b = dao.add(MetaPhraseDTO("thanks", "Thank you", work))
    c = dao.add(MetaPhraseDTO("dinner", "Soup", home))
    assert a > 0 and b > a and c > b

    assert [p.title for p in dao.get_by_category(work)] == ["greet", "thanks"]
    assert [p.title for p in dao.get_by_category(home)] == ["dinner"]
    assert {p.title for p in dao.get_by_category()} == {"greet", "thanks", "dinner"}

    updated = MetaPhraseDTO("greet2", "Hi there", home, id=a)
    assert dao.update(updated) is True
    assert {p.title for p in dao.get_by_category(home)} == {"greet2", "dinner"}

    assert dao.delete(b) is True
    assert dao.delete(b) is False


def test_meta_phrase_update_requires_id(manager: DatabaseManager) -> None:
    category_id = manager.category_dao.add(CategoryDTO(name="Work"))
    dto = MetaPhraseDTO("t", "c", category_id)
    assert manager.meta_phrase_dao.update(dto) is False


def test_meta_phrase_corrupted_created_at_falls_back_to_now(
    manager: DatabaseManager,
) -> None:
    category_id = manager.category_dao.add(CategoryDTO(name="Work"))
    phrase_id = manager.meta_phrase_dao.add(MetaPhraseDTO("t", "c", category_id))
    conn = sqlite3.connect(manager.db_path)
    conn.execute(
        "UPDATE t_meta_phrase SET created_at = 'corrupted' WHERE id = ?", (phrase_id,)
    )
    conn.commit()
    conn.close()

    phrase = manager.meta_phrase_dao.get_by_category(category_id)[0]
    assert isinstance(phrase.created_at, float)
    assert phrase.created_at > 0


def test_meta_phrase_deleting_category_cascades(manager: DatabaseManager) -> None:
    category_id = manager.category_dao.add(CategoryDTO(name="Temp"))
    manager.meta_phrase_dao.add(MetaPhraseDTO("t", "c", category_id))
    manager.category_dao.delete(category_id)
    assert manager.meta_phrase_dao.get_by_category() == []


def test_meta_phrase_add_returns_minus_one_on_sqlite_error(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = _broken_connection(sqlite3.OperationalError("disk full"))
    monkeypatch.setattr(manager.meta_phrase_dao, "_get_connection", lambda: conn)
    assert manager.meta_phrase_dao.add(MetaPhraseDTO("t", "c", 1)) == -1


def test_meta_phrase_dao_failures_use_safe_defaults(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    dao = manager.meta_phrase_dao
    monkeypatch.setattr(dao, "execute_read", _boom)
    monkeypatch.setattr(dao, "execute_update", _boom)
    assert dao.get_by_category() == []
    assert dao.update(MetaPhraseDTO("t", "c", 1, id=1)) is False
    assert dao.delete(1) is False


# --- ClipboardHistoryDAO ---


def test_history_add_duplicate_merges_pin_and_refreshes_time(
    manager: DatabaseManager,
) -> None:
    dao = manager.history_dao
    first = dao.add_item(ClipboardHistoryDTO(content="dup", created_at=100.0))
    again = dao.add_item(
        ClipboardHistoryDTO(content="dup", is_pinned=True, created_at=200.0)
    )
    assert again == first
    items = dao.get_items()
    assert len(items) == 1
    assert items[0].is_pinned is True
    assert items[0].created_at == 200.0


def test_history_get_items_filters_with_escaped_wildcards_and_limit(
    manager: DatabaseManager,
) -> None:
    dao = manager.history_dao
    dao.add_item(ClipboardHistoryDTO(content="100% done", created_at=1.0))
    dao.add_item(ClipboardHistoryDTO(content="1000 done", created_at=2.0))
    dao.add_item(ClipboardHistoryDTO(content="a_b", created_at=3.0))
    dao.add_item(ClipboardHistoryDTO(content="axb", created_at=4.0))

    assert [d.content for d in dao.get_items(query="100%")] == ["100% done"]
    assert [d.content for d in dao.get_items(query="a_b")] == ["a_b"]
    assert len(dao.get_items(limit=2)) == 2


def test_history_corrupted_created_at_falls_back_to_now(
    manager: DatabaseManager,
) -> None:
    item_id = manager.history_dao.add_item(ClipboardHistoryDTO(content="x"))
    conn = sqlite3.connect(manager.db_path)
    conn.execute(
        "UPDATE t_clipboard_history SET created_at = 'bad' WHERE id = ?", (item_id,)
    )
    conn.commit()
    conn.close()
    item = manager.history_dao.get_items()[0]
    assert isinstance(item.created_at, float)
    assert item.created_at > 0


def test_history_update_pin_delete_and_last_added(manager: DatabaseManager) -> None:
    dao = manager.history_dao
    assert dao.get_last_added_content() is None
    old_id = dao.add_item(ClipboardHistoryDTO(content="old", created_at=1.0))
    dao.add_item(ClipboardHistoryDTO(content="new", created_at=2.0))
    assert dao.get_last_added_content() == "new"

    assert dao.update_content(old_id, "edited", "hash") is True
    assert dao.update_content(9999, "x", "h") is False
    assert dao.pin_item(old_id, True) is True
    assert dao.pin_item(9999, True) is False
    assert dao.get_items()[0].content == "edited"  # ピン留めが先頭

    assert dao.delete_item(old_id) is True
    assert dao.delete_item(old_id) is False


def test_history_delete_unpinned_clear_and_cleanup(manager: DatabaseManager) -> None:
    dao = manager.history_dao
    dao.add_item(ClipboardHistoryDTO(content="pinned", is_pinned=True, created_at=1.0))
    for i in range(4):
        dao.add_item(ClipboardHistoryDTO(content=f"n{i}", created_at=10.0 + i))

    dao.cleanup_old(10)  # 上限以内なら何もしない
    assert len(dao.get_items()) == 5

    dao.cleanup_old(3)  # ピン留め以外の古いものから削除
    contents = [d.content for d in dao.get_items()]
    assert "pinned" in contents
    assert len(contents) == 3

    dao.delete_unpinned()
    assert [d.content for d in dao.get_items()] == ["pinned"]

    dao.clear_all()
    assert dao.get_items() == []


def test_history_dao_failures_use_safe_defaults(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    dao = manager.history_dao
    monkeypatch.setattr(dao, "execute_read", _boom)
    monkeypatch.setattr(dao, "execute_update", _boom)
    assert dao.get_items() == []
    assert dao.get_last_added_content() is None
    assert dao.update_content(1, "x", "h") is False
    assert dao.pin_item(1, True) is False
    assert dao.delete_item(1) is False
    dao.clear_all()  # 例外を送出しない
    dao.delete_unpinned()


def test_history_add_and_cleanup_survive_sqlite_errors(
    manager: DatabaseManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    dao = manager.history_dao
    conn = _broken_connection(sqlite3.OperationalError("locked"))
    monkeypatch.setattr(dao, "_get_connection", lambda: conn)
    assert dao.add_item(ClipboardHistoryDTO(content="x")) == -1
    dao.cleanup_old(1)  # 例外を送出しない


# --- HistoryService ---


@pytest.fixture
def service(tmp_path: Path) -> tuple[HistoryService, list[dict[str, Any]]]:
    dispatcher = EventDispatcher()
    events: list[dict[str, Any]] = []
    dispatcher.subscribe("HISTORY_UPDATED", events.append)
    manager = DatabaseManager(db_path=str(tmp_path / "svc.db"))
    return HistoryService(manager, dispatcher, history_limit=5), events


def test_service_ignores_empty_and_duplicate_text(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, events = service
    svc.add_history_item("")
    assert svc.history == []
    svc.add_history_item("hello")
    svc.add_history_item("hello")  # 直前と同じ内容は追加しない
    assert [item[0] for item in svc.history] == ["hello"]
    assert len(events) == 1


def test_service_update_item_refreshes_last_clipboard_data(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, events = service
    svc.add_history_item("first")
    svc.add_history_item("second")
    newest_id = svc.history[0][2]

    svc.update_history_item_by_id(newest_id, "second edited")

    assert svc.history[0][0] == "second edited"
    assert svc.last_clipboard_data == "second edited"
    assert events[-1]["last_content"] == "second edited"


def test_service_delete_item_and_empty_state(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, events = service
    svc.add_history_item("only")
    item_id = svc.history[0][2]
    svc.delete_history_item_by_id(item_id)
    assert svc.history == []
    assert svc.last_clipboard_data == ""

    notified = len(events)
    svc.delete_history_item_by_id(9999.0)  # 存在しない ID は通知しない
    assert len(events) == notified


def test_service_pin_and_unpin_reorder_history(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, _ = service
    svc.add_history_item("a")
    svc.add_history_item("b")
    a_id = next(item[2] for item in svc.history if item[0] == "a")

    svc.pin_item_by_id(a_id)
    assert svc.get_history()[0][:2] == ("a", True)

    svc.unpin_item_by_id(a_id)
    assert all(not pinned for _, pinned, _ in svc.history)


def test_service_clear_and_delete_unpinned(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, _ = service
    svc.add_history_item("keep")
    svc.add_history_item("drop")
    keep_id = next(item[2] for item in svc.history if item[0] == "keep")
    svc.pin_item_by_id(keep_id)

    svc.delete_all_unpinned_history()
    assert [item[0] for item in svc.history] == ["keep"]

    svc.clear_history()
    assert svc.history == []
    assert svc.last_clipboard_data == ""


def test_service_import_history_keeps_order_and_limit(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, _ = service
    svc.import_history([f"item{i}" for i in range(8)])  # リストの後ろ側が最新
    assert [item[0] for item in svc.history] == [
        "item7",
        "item6",
        "item5",
        "item4",
        "item3",
    ]


def test_service_filtered_history_matches_query(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, _ = service
    svc.add_history_item("apple pie")
    svc.add_history_item("banana")
    assert [item[0] for item in svc.get_filtered_history("apple")] == ["apple pie"]
    assert svc.get_filtered_history("zzz") == []


@pytest.mark.parametrize("bad_value", [None, "10", 0, -3, 1.5])
def test_service_ignores_invalid_history_limit(
    service: tuple[HistoryService, list[dict[str, Any]]], bad_value: object
) -> None:
    svc, events = service
    svc.on_settings_changed({"history_limit": bad_value})
    assert svc.history_limit == 5
    assert events == []


def test_service_increasing_limit_reloads_from_database(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, events = service
    svc.import_history([f"item{i}" for i in range(5)])
    svc.on_settings_changed({"history_limit": 10})
    assert svc.history_limit == 10
    assert events  # 再読み込み後に通知される


def test_service_decreasing_limit_trims_history(
    service: tuple[HistoryService, list[dict[str, Any]]],
) -> None:
    svc, events = service
    svc.import_history([f"item{i}" for i in range(5)])
    notified = len(events)
    svc.on_settings_changed({"history_limit": 2})
    assert len(svc.history) == 2
    assert len(events) == notified + 1


def test_service_load_history_returns_empty_on_database_error(
    service: tuple[HistoryService, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _ = service
    monkeypatch.setattr(svc.db_manager.history_dao, "get_items", _boom)
    assert svc.load_history() == []
    assert svc.get_filtered_history("x") == []


def test_service_operations_swallow_database_errors(
    service: tuple[HistoryService, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, events = service
    svc.add_history_item("seed")
    item_id = svc.history[0][2]
    dao = svc.db_manager.history_dao
    for name in (
        "add_item",
        "update_content",
        "delete_item",
        "pin_item",
        "clear_all",
        "delete_unpinned",
    ):
        monkeypatch.setattr(dao, name, _boom)
    notified = len(events)

    svc.add_history_item("new")
    svc.update_history_item_by_id(item_id, "edited")
    svc.delete_history_item_by_id(item_id)
    svc.pin_item_by_id(item_id)
    svc.unpin_item_by_id(item_id)
    svc.clear_history()
    svc.delete_all_unpinned_history()
    svc.import_history(["a", "b"])

    assert len(events) == notified  # どの操作も通知されず、例外も出ない
