from __future__ import annotations

import logging
import sqlite3
import threading
from typing import Any

logger = logging.getLogger(__name__)


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

    def execute_insert(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """INSERT クエリをスレッドセーフに実行し、挿入されたレコードのID（lastrowid）を返します。"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid or -1
            except sqlite3.Error as e:
                logger.error(
                    "INSERT クエリ実行中にエラーが発生しました: %s (query=%s)",
                    e,
                    query,
                    exc_info=True,
                )
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute_update(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """UPDATE または DELETE クエリをスレッドセーフに実行し、影響を受けた行数（rowcount）を返します。"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(
                    "UPDATE/DELETE クエリ実行中にエラーが発生しました: %s (query=%s)",
                    e,
                    query,
                    exc_info=True,
                )
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """後方互換性のための書き込みメソッド。execute_update を呼び出します。"""
        return self.execute_update(query, params)

    def execute_read(self, query: str, params: tuple[Any, ...] = ()) -> list[Any]:
        """読み込みクエリをスレッドセーフに実行し、結果リストを返します。"""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
            except sqlite3.Error as e:
                logger.error(
                    "READ クエリ実行中にエラーが発生しました: %s (query=%s)",
                    e,
                    query,
                    exc_info=True,
                )
                raise
            finally:
                conn.close()
