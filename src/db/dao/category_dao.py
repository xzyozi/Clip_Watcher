from __future__ import annotations

import logging
import sqlite3
import threading
from src.db.dao.base_dao import BaseDAO
from src.db.dto import CategoryDTO

logger = logging.getLogger(__name__)

class CategoryDAO(BaseDAO):
    """メタ管理カテゴリ（t_category）テーブルへのデータアクセスを行うDAO"""

    def __init__(self, db_path: str, lock: threading.Lock) -> None:
        super().__init__(db_path, lock)

    def add(self, dto: CategoryDTO) -> int:
        """カテゴリを追加します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COALESCE(MAX(sort_order), 0) FROM t_category")
                    max_order = cursor.fetchone()[0]

                    cursor.execute(
                        "INSERT INTO t_category (name, sort_order) VALUES (?, ?)",
                        (dto.name, max_order + 1)
                    )
                    new_id = cursor.lastrowid or -1
                    conn.commit()
                    logger.info("カテゴリを追加しました: %s (ID: %d)", dto.name, new_id)
                    return new_id
            except sqlite3.IntegrityError:
                logger.warning("カテゴリ名 '%s' は既に存在します。", dto.name)
                return -1
            except sqlite3.Error as e:
                logger.error("カテゴリの追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_all(self) -> list[CategoryDTO]:
        """すべてのカテゴリを表示順（sort_order）で取得します。"""
        try:
            rows = self.execute_read("SELECT id, name, sort_order FROM t_category ORDER BY sort_order ASC")
            return [
                CategoryDTO(id=row[0], name=row[1], sort_order=row[2])
                for row in rows
            ]
        except Exception as e:
            logger.error("カテゴリ一覧の取得中にエラーが発生しました: %s", str(e), exc_info=True)
            return []

    def update(self, dto: CategoryDTO) -> bool:
        """カテゴリ名を更新します。"""
        if dto.id is None:
            return False
        try:
            affected_rows = self.execute_write(
                "UPDATE t_category SET name = ? WHERE id = ?",
                (dto.name, dto.id)
            )
            return affected_rows > 0
        except sqlite3.IntegrityError:
            logger.warning("カテゴリ名 '%s' は既に存在するため更新できません。", dto.name)
            return False
        except Exception as e:
            logger.error("カテゴリ名の更新中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def delete(self, category_id: int) -> bool:
        """カテゴリを削除します。"""
        try:
            affected_rows = self.execute_write(
                "DELETE FROM t_category WHERE id = ?",
                (category_id,)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("カテゴリの削除中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def get_meta_phrase_count(self, category_id: int) -> int:
        """指定されたカテゴリに属する定型文（メタ文）の件数を取得します。"""
        try:
            rows = self.execute_read(
                "SELECT COUNT(*) FROM t_meta_phrase WHERE category_id = ?",
                (category_id,)
            )
            return rows[0][0] if rows else 0
        except Exception as e:
            logger.error("カテゴリ内定型文の件数取得中にエラーが発生しました: %s", str(e), exc_info=True)
            return 0
