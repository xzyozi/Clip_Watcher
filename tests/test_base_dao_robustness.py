from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from src.db.dao.base_dao import BaseDAO


@pytest.fixture
def base_dao(tmp_path: Path) -> BaseDAO:
    db_file = tmp_path / "base_dao_test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    return BaseDAO(str(db_file), threading.Lock())


def test_base_dao_execute_insert(base_dao: BaseDAO) -> None:
    """execute_insert が挿入された ID を正確に返すことを検証 (#124)。"""
    row_id_1 = base_dao.execute_insert(
        "INSERT INTO test_table (name) VALUES (?)", ("Alpha",)
    )
    assert row_id_1 == 1

    row_id_2 = base_dao.execute_insert(
        "INSERT INTO test_table (name) VALUES (?)", ("Beta",)
    )
    assert row_id_2 == 2


def test_base_dao_execute_update_zero_rows(base_dao: BaseDAO) -> None:
    """execute_update が更新対象が0件の場合に正確に 0 を返すことを検証 (#124)。"""
    base_dao.execute_insert("INSERT INTO test_table (name) VALUES (?)", ("Item1",))

    # 存在しないIDに対する UPDATE は rowcount = 0 を返すべき
    affected = base_dao.execute_update(
        "UPDATE test_table SET name = ? WHERE id = ?", ("Updated", 999)
    )
    assert affected == 0


def test_base_dao_execute_update_success(base_dao: BaseDAO) -> None:
    """execute_update が影響を受けた行数を正確に返すことを検証 (#124)。"""
    base_dao.execute_insert("INSERT INTO test_table (name) VALUES (?)", ("Item1",))
    base_dao.execute_insert("INSERT INTO test_table (name) VALUES (?)", ("Item2",))

    affected = base_dao.execute_update(
        "UPDATE test_table SET name = ? WHERE name LIKE ?", ("Group", "Item%")
    )
    assert affected == 2


def test_base_dao_execute_error_handling_and_rollback(base_dao: BaseDAO) -> None:
    """クエリエラー時にロールバックされ sqlite3.Error が送出されることを検証 (#124)。"""
    with pytest.raises(sqlite3.Error):
        base_dao.execute_insert(
            "INSERT INTO non_existent_table (name) VALUES (?)", ("Fail",)
        )

    with pytest.raises(sqlite3.Error):
        base_dao.execute_update("UPDATE non_existent_table SET name = ?", ("Fail",))
