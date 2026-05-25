from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import TYPE_CHECKING

from src.db.dao.base_dao import BaseDAO
from src.db.dto import ClipboardHistoryDTO

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

class ClipboardHistoryDAO(BaseDAO):
    """クリップボード履歴（t_clipboard_history）テーブルへのデータアクセスを行うDAO"""

    def __init__(self, db_path: str, lock: threading.Lock) -> None:
        super().__init__(db_path, lock)

    def add_item(self, dto: ClipboardHistoryDTO) -> int:
        """
        新しい履歴項目を追加します。重複チェックを行い、登録された行のID（整数）を返します。
        既存の重複項目がある場合は、作成日時を最新化してピン留め状態をマージします。
        """
        pinned_val = 1 if dto.is_pinned else 0
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 重複チェック
                    cursor.execute(
                        "SELECT id, is_pinned FROM t_clipboard_history WHERE content_hash = ?",
                        (dto.content_hash,)
                    )
                    row = cursor.fetchone()

                    if row:
                        existing_id, existing_pinned = row
                        merged_pinned = 1 if (existing_pinned or pinned_val) else 0
                        cursor.execute(
                            "UPDATE t_clipboard_history SET is_pinned = ?, created_at = ? WHERE id = ?",
                            (merged_pinned, dto.created_at, existing_id)
                        )
                        conn.commit()
                        logger.info("重複履歴を検出しました。最上部に移動します (ID: %d)", existing_id)
                        return existing_id
                    else:
                        cursor.execute(
                            "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
                            (dto.content, dto.content_hash, pinned_val, dto.created_at)
                        )
                        new_id = cursor.lastrowid or -1
                        conn.commit()
                        logger.info("新規履歴を登録しました (ID: %d)", new_id)
                        return new_id
            except sqlite3.Error as e:
                logger.error("履歴項目の追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_items(self, limit: int | None = None, query: str | None = None) -> list[ClipboardHistoryDTO]:
        """履歴項目を取得します。ピン留めされている項目を優先し、次に created_at DESC でソートします。"""
        sql = "SELECT id, content, content_hash, is_pinned, created_at FROM t_clipboard_history"
        params = []

        if query:
            sql += " WHERE content LIKE ?"
            params.append(f"%{query}%")

        sql += " ORDER BY is_pinned DESC, created_at DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        try:
            rows = self.execute_read(sql, tuple(params))
            return [
                ClipboardHistoryDTO(
                    id=row[0],
                    content=row[1],
                    content_hash=row[2],
                    is_pinned=bool(row[3]),
                    created_at=float(row[4])
                ) for row in rows
            ]
        except Exception as e:
            logger.error("履歴項目の取得中にエラーが発生しました: %s", str(e), exc_info=True)
            return []

    def update_content(self, item_id: int, new_content: str, new_hash: str) -> bool:
        """履歴テキストの内容とハッシュを更新します。"""
        try:
            affected_rows = self.execute_write(
                "UPDATE t_clipboard_history SET content = ?, content_hash = ? WHERE id = ?",
                (new_content, new_hash, item_id)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("履歴テキストの更新中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def pin_item(self, item_id: int, pin: bool) -> bool:
        """ピン留め状態を切り替えます。"""
        pinned_val = 1 if pin else 0
        try:
            affected_rows = self.execute_write(
                "UPDATE t_clipboard_history SET is_pinned = ? WHERE id = ?",
                (pinned_val, item_id)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("ピン留め状態の更新中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def delete_item(self, item_id: int) -> bool:
        """履歴項目を削除します。"""
        try:
            affected_rows = self.execute_write(
                "DELETE FROM t_clipboard_history WHERE id = ?",
                (item_id,)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error("履歴項目の削除中にエラーが発生しました: %s", str(e), exc_info=True)
            return False

    def clear_all(self) -> None:
        """すべての履歴データをクリアします。"""
        try:
            self.execute_write("DELETE FROM t_clipboard_history")
            logger.info("すべての履歴をクリアしました。")
        except Exception as e:
            logger.error("履歴クリア中にエラーが発生しました: %s", str(e), exc_info=True)

    def delete_unpinned(self) -> None:
        """ピン留めされていない履歴をすべて削除します。"""
        try:
            self.execute_write("DELETE FROM t_clipboard_history WHERE is_pinned = 0")
            logger.info("ピン留めされていない履歴を削除しました。")
        except Exception as e:
            logger.error("未ピン留め履歴の削除中にエラーが発生しました: %s", str(e), exc_info=True)

    def cleanup_old(self, limit: int) -> None:
        """上限値を超えている場合、ピン留めされていない最も古い履歴からクリーンアップします。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM t_clipboard_history")
                    count = cursor.fetchone()[0]

                    if count <= limit:
                        return

                    excess = count - limit
                    cursor.execute(
                        "SELECT id FROM t_clipboard_history WHERE is_pinned = 0 ORDER BY created_at ASC LIMIT ?",
                        (excess,)
                    )
                    rows = cursor.fetchall()
                    
                    if rows:
                        ids_to_delete = [row[0] for row in rows]
                        placeholders = ",".join("?" for _ in ids_to_delete)
                        cursor.execute(
                            f"DELETE FROM t_clipboard_history WHERE id IN ({placeholders})",
                            tuple(ids_to_delete)
                        )
                        conn.commit()
                        logger.info(
                            "履歴件数上限（%d件）を超過したため、ピン留めされていない古い項目を %d 件クリーンアップしました。",
                            limit, len(ids_to_delete)
                        )
            except sqlite3.Error as e:
                logger.error("履歴の自動自動クリーンアップ中にエラーが発生しました: %s", str(e), exc_info=True)
