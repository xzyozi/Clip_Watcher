from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import threading
import time

from src.db.dao.category_dao import CategoryDAO
from src.db.dao.history_dao import ClipboardHistoryDAO
from src.db.dao.meta_phrase_dao import MetaPhraseDAO
from src.db.dto import ClipboardHistoryDTO

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLiteデータベースの初期化、接続管理、マイグレーションを行うマネージャ。
    個別のテーブル操作は、それぞれ history_dao, category_dao, meta_phrase_dao に処理を委譲します。
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()

        # 各DAOの初期化
        self.history_dao = ClipboardHistoryDAO(db_path, self._lock)
        self.category_dao = CategoryDAO(db_path, self._lock)
        self.meta_phrase_dao = MetaPhraseDAO(db_path, self._lock)

        logger.info("DatabaseManager を初期化します。DBパス: %s", db_path)
        self._initialize_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """SQLite接続を取得し、外部キー制約を有効にします。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize_tables(self) -> None:
        """テーブルとインデックスを作成します。"""
        with self._lock:
            conn = self._get_connection()
            try:
                # 1. クリップボード履歴テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS t_clipboard_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        is_pinned INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL
                    )
                """)

                # 2. カテゴリテーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS t_category (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        sort_order INTEGER NOT NULL DEFAULT 0
                    )
                """)

                # 3. カテゴリ別定型文（メタ管理）テーブル
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS t_meta_phrase (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category_id INTEGER NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL,
                        FOREIGN KEY(category_id) REFERENCES t_category(id) ON DELETE CASCADE
                    )
                """)

                # インデックス作成
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_hash ON t_clipboard_history(content_hash)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_created ON t_clipboard_history(created_at DESC)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_meta_phrase_category ON t_meta_phrase(category_id, sort_order)"
                )

                conn.commit()
                logger.info(
                    "データベーステーブルおよびインデックスの初期化が完了しました。"
                )
            except sqlite3.Error as e:
                logger.error(
                    "データベース初期化中にエラーが発生しました: %s",
                    str(e),
                    exc_info=True,
                )
                raise
            finally:
                conn.close()

    def check_and_migrate_json(self, history_file_path: str) -> None:
        """
        既存 of history.json からデータをインポートします。
        全体のインポート処理は単一トランザクションで行われ、失敗時はロールバックされます。
        """
        if not os.path.exists(history_file_path):
            logger.info(
                "旧履歴ファイル（%s）が見つかりません。マイグレーションをスキップします。",
                history_file_path,
            )
            return

        logger.info(
            "旧履歴ファイル（%s）からのデータ移行を開始します。", history_file_path
        )
        with self._lock:
            conn = None
            try:
                with open(history_file_path, encoding="utf-8") as f:
                    loaded_data = json.load(f)

                if not isinstance(loaded_data, list):
                    logger.warning(
                        "history.json のデータ形式がリストではありません。移行をスキップします。"
                    )
                    return

                conn = self._get_connection()
                conn.execute("BEGIN TRANSACTION")

                # 旧データを逆順（古い順）に挿入してID順序を維持する
                for i, item in enumerate(reversed(loaded_data)):
                    content = ""
                    is_pinned = False
                    created_at = time.time() - i

                    if isinstance(item, list):
                        if len(item) >= 2:
                            content = str(item[0])
                            is_pinned = bool(item[1])
                        if len(item) == 3:
                            created_at = float(item[2])
                    elif isinstance(item, str):
                        content = item

                    if not content:
                        continue

                    # DTOを作成してハッシュ・日時初期化を自動で行う
                    dto = ClipboardHistoryDTO(
                        content=content, is_pinned=is_pinned, created_at=created_at
                    )

                    # 既に存在するかチェック
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, is_pinned FROM t_clipboard_history WHERE content_hash = ?",
                        (dto.content_hash,),
                    )
                    row = cursor.fetchone()

                    if row:
                        existing_id, existing_pinned = row
                        merged_pinned = 1 if (existing_pinned or dto.is_pinned) else 0
                        conn.execute(
                            "UPDATE t_clipboard_history SET is_pinned = ?, created_at = ? WHERE id = ?",
                            (merged_pinned, dto.created_at, existing_id),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
                            (
                                dto.content,
                                dto.content_hash,
                                1 if dto.is_pinned else 0,
                                dto.created_at,
                            ),
                        )

                conn.commit()
                logger.info(
                    "SQLiteへのデータ移行が成功しました。JSONファイルをバックアップします。"
                )

                # jsonファイルのバックアップ（リネーム）
                backup_path = history_file_path + ".bak"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(history_file_path, backup_path)
                logger.info("旧履歴ファイルを %s にリネームしました。", backup_path)

            except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
                logger.error(
                    "履歴ファイル読み込みまたはリネーム中にエラーが発生しました: %s",
                    str(e),
                    exc_info=True,
                )
                if conn:
                    conn.rollback()
            except sqlite3.Error as e:
                logger.error(
                    "マイグレーションのデータベース挿入中にエラーが発生しました。ロールバックします: %s",
                    str(e),
                    exc_info=True,
                )
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
