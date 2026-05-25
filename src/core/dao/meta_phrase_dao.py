from __future__ import annotations

import logging
import sqlite3
import threading
from src.core.dao.base_dao import BaseDAO
from src.core.dto import MetaPhraseDTO

logger = logging.getLogger(__name__)

class MetaPhraseDAO(BaseDAO):
    """メタ定型文（t_meta_phrase）テーブルへのデータアクセスを行うDAO"""

    def __init__(self, db_path: str, lock: threading.Lock) -> None:
        super().__init__(db_path, lock)

    def add(self, dto: MetaPhraseDTO) -> int:
        """メタ定型文を追加します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) FROM t_meta_phrase WHERE category_id = ?",
                        (dto.category_id,)
                    )
                    max_order = cursor.fetchone()[0]

                    cursor.execute(
                        "INSERT INTO t_meta_phrase (title, content, category_id, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
                        (dto.title, dto.content, dto.category_id, max_order + 1, dto.created_at)
                    )
                    new_id = cursor.lastrowid or -1
                    conn.commit()
                    logger.info("メタ定型文を追加しました: %s (ID: %d)", dto.title, new_id)
                    return new_id
            except sqlite3.Error as e:
                logger.error("メタ定型文の追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_by_category(self, category_id: int | None = None) -> list[MetaPhraseDTO]:
        """特定カテゴリのメタ定型文を表示順で取得します。Noneの場合はすべてのメタ定型文を取得します。"""
        sql = "SELECT id, title, content, category_id, sort_order, created_at FROM t_meta_phrase"
        params = []

        if category_id is not None:
            sql += " WHERE category_id = ?"
            params.append(category_id)

        sql += " ORDER BY sort_order ASC, created_at DESC"

        try:
            rows = self.execute_read(sql, tuple(params))
            return [
                MetaPhraseDTO(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    category_id=row[3],
                    sort_order=row[4],
                    created_at=float(row[5])
                ) for row in rows
            ]
        except Exception as e:
            logger.error("メタ定型文の取得中にエラーが発生しました: %s", str(e), exc_info=True)
            return []

    def update(self, dto: MetaPhraseDTO) -> bool:
        """メタ定型文の内容を更新します。カテゴリの切り替えも対応。"""
        if dto.id is None:
            return False
        try:
            affected_rows = self.execute_write(
                "UPDATE t_meta_phrase SET title = ?, content = ?, category_id = ? WHERE id = ?",
                (dto.title, dto.content, dto.category_id, dto.id)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("メタ定型文の更新中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def delete(self, phrase_id: int) -> bool:
        """メタ定型文を削除します。"""
        try:
            affected_rows = self.execute_write(
                "DELETE FROM t_meta_phrase WHERE id = ?",
                (phrase_id,)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("メタ定型文の削除中にエラーが発生しました: %s", str(e), exc_info=True)
            return False
