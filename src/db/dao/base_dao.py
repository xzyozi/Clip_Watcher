from __future__ import annotations

import sqlite3
import threading
from typing import Any


class BaseDAO:
    """すべてのDAOクラスの共通基底クラス。排他ロックと接続の取得を管理します。"""

    def __init__(self, db_path: str, lock: threading.Lock) -> None:
        self.db_path = db_path
        self._lock = lock

    def _get_connection(self) -> sqlite3.Connection:
        """SQLite接続を取得し、外部キー制約を有効にします。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """書き込みクエリをスレッドセーフに実行し、影響を受けた行数または最後に挿入されたIDを返します。"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid or cursor.rowcount

    def execute_read(self, query: str, params: tuple[Any, ...] = ()) -> list[Any]:
        """読み込みクエリをスレッドセーフに実行し、結果リストを返します。"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
