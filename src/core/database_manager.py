from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import threading
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    SQLiteデータベースへの接続・操作を管理するクラス。
    threading.Lockを用いて、マルチスレッド環境（監視スレッドとUIスレッド）からの安全な同時アクセスを保証します。
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
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
            try:
                with self._get_connection() as conn:
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
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_hash ON t_clipboard_history(content_hash)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON t_clipboard_history(created_at DESC)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_phrase_category ON t_meta_phrase(category_id, sort_order)")
                    
                    conn.commit()
                logger.info("データベーステーブルおよびインデックスの初期化が完了しました。")
            except sqlite3.Error as e:
                logger.error("データベース初期化中にエラーが発生しました: %s", str(e), exc_info=True)
                raise

    def check_and_migrate_json(self, history_file_path: str) -> None:
        """
        既存の history.json からデータをインポートします。
        全体のインポート処理は単一トランザクションで行われ、失敗時はロールバックされます。
        """
        if not os.path.exists(history_file_path):
            logger.info("旧履歴ファイル（%s）が見つかりません。マイグレーションをスキップします。", history_file_path)
            return

        logger.info("旧履歴ファイル（%s）からのデータ移行を開始します。", history_file_path)
        with self._lock:
            conn = None
            try:
                with open(history_file_path, encoding='utf-8') as f:
                    loaded_data = json.load(f)

                if not isinstance(loaded_data, list):
                    logger.warning("history.json のデータ形式がリストではありません。移行をスキップします。")
                    return

                conn = self._get_connection()
                conn.execute("BEGIN TRANSACTION")

                # 旧データを逆順（古い順）に挿入してID順序を維持する
                for i, item in enumerate(reversed(loaded_data)):
                    content = ""
                    is_pinned = 0
                    created_at = time.time() - i  # デフォルトのタイムスタンプ

                    if isinstance(item, list):
                        if len(item) >= 2:
                            content = str(item[0])
                            is_pinned = 1 if item[1] else 0
                        if len(item) == 3:
                            created_at = float(item[2])
                    elif isinstance(item, str):
                        content = item

                    if not content:
                        continue

                    # ハッシュ計算と重複チェック
                    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    
                    # 既に存在するかチェック
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, is_pinned FROM t_clipboard_history WHERE content_hash = ?", (content_hash,))
                    row = cursor.fetchone()

                    if row:
                        # 既存の場合はピン留め状態を合成し、作成日時のみ更新
                        existing_id, existing_pinned = row
                        merged_pinned = 1 if (existing_pinned or is_pinned) else 0
                        conn.execute(
                            "UPDATE t_clipboard_history SET is_pinned = ?, created_at = ? WHERE id = ?",
                            (merged_pinned, created_at, existing_id)
                        )
                    else:
                        conn.execute(
                            "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
                            (content, content_hash, is_pinned, created_at)
                        )

                conn.commit()
                logger.info("SQLiteへのデータ移行が成功しました。JSONファイルをバックアップします。")

                # jsonファイルのバックアップ（リネーム）
                backup_path = history_file_path + ".bak"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(history_file_path, backup_path)
                logger.info("旧履歴ファイルを %s にリネームしました。", backup_path)

            except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
                logger.error("履歴ファイル読み込みまたはリネーム中にエラーが発生しました: %s", str(e), exc_info=True)
                if conn:
                    conn.rollback()
            except sqlite3.Error as e:
                logger.error("マイグレーションのデータベース挿入中にエラーが発生しました。ロールバックします: %s", str(e), exc_info=True)
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()

    # ==========================================
    # 履歴データ (t_clipboard_history) 操作
    # ==========================================

    def add_history_item(self, content: str, is_pinned: bool = False, created_at: float | None = None) -> int:
        """
        新しい履歴項目を追加します。重複排除を行い、登録された項目のID（整数）を返します。
        """
        if not content:
            return -1

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        ts = created_at if created_at is not None else time.time()
        pinned_val = 1 if is_pinned else 0

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 重複チェック
                    cursor.execute("SELECT id, is_pinned FROM t_clipboard_history WHERE content_hash = ?", (content_hash,))
                    row = cursor.fetchone()

                    if row:
                        # 既存の場合：最上部に移動（created_atを最新化）し、ピン留め状態をマージ
                        existing_id, existing_pinned = row
                        merged_pinned = 1 if (existing_pinned or pinned_val) else 0
                        cursor.execute(
                            "UPDATE t_clipboard_history SET is_pinned = ?, created_at = ? WHERE id = ?",
                            (merged_pinned, ts, existing_id)
                        )
                        conn.commit()
                        logger.info("重複履歴を検出しました。最上部に移動します (ID: %d)", existing_id)
                        return existing_id
                    else:
                        # 新規挿入
                        cursor.execute(
                            "INSERT INTO t_clipboard_history (content, content_hash, is_pinned, created_at) VALUES (?, ?, ?, ?)",
                            (content, content_hash, pinned_val, ts)
                        )
                        new_id = cursor.lastrowid
                        conn.commit()
                        logger.info("新規履歴を登録しました (ID: %d)", new_id)
                        return new_id
            except sqlite3.Error as e:
                logger.error("履歴項目の追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_history_items(self, limit: int | None = None, query: str | None = None) -> list[tuple[int, str, bool, float]]:
        """
        履歴項目を取得します。ピン留めされている項目を優先し、次に `created_at DESC` で並び替えます。
        """
        sql = "SELECT id, content, is_pinned, created_at FROM t_clipboard_history"
        params = []

        if query:
            sql += " WHERE content LIKE ?"
            params.append(f"%{query}%")

        # ピン留め優先、次に日付順
        sql += " ORDER BY is_pinned DESC, created_at DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, tuple(params))
                    rows = cursor.fetchall()
                    # SQLiteから取得したデータをPython標準型（bool, float）に変換して返す
                    return [(row[0], row[1], bool(row[2]), float(row[3])) for row in rows]
            except sqlite3.Error as e:
                logger.error("履歴項目の取得中にエラーが発生しました: %s", str(e), exc_info=True)
                return []

    def update_history_content(self, item_id: int, new_content: str) -> bool:
        """履歴のテキスト内容を更新します。"""
        if not new_content:
            return False

        content_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE t_clipboard_history SET content = ?, content_hash = ? WHERE id = ?",
                        (new_content, content_hash, item_id)
                    )
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("履歴項目を更新しました (ID: %d)", item_id)
                    return success
            except sqlite3.Error as e:
                logger.error("履歴項目のテキスト更新中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def pin_history_item(self, item_id: int, pin: bool) -> bool:
        """履歴のピン留め状態を切り替えます。"""
        pinned_val = 1 if pin else 0
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE t_clipboard_history SET is_pinned = ? WHERE id = ?",
                        (pinned_val, item_id)
                    )
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("履歴項目のピン留め状態を変更しました (ID: %d, Pin: %s)", item_id, pin)
                    return success
            except sqlite3.Error as e:
                logger.error("履歴項目のピン留め処理中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def delete_history_item(self, item_id: int) -> bool:
        """履歴項目を1件削除します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM t_clipboard_history WHERE id = ?", (item_id,))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("履歴項目を削除しました (ID: %d)", item_id)
                    return success
            except sqlite3.Error as e:
                logger.error("履歴項目の削除中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def clear_history(self) -> None:
        """すべての履歴データをクリアします。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM t_clipboard_history")
                    conn.commit()
                logger.info("すべてのクリップボード履歴を削除しました。")
            except sqlite3.Error as e:
                logger.error("履歴クリア中にエラーが発生しました: %s", str(e), exc_info=True)

    def delete_unpinned_history(self) -> None:
        """ピン留めされていない履歴をすべて削除します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM t_clipboard_history WHERE is_pinned = 0")
                    conn.commit()
                logger.info("ピン留めされていない履歴をすべて削除しました。")
            except sqlite3.Error as e:
                logger.error("未ピン留め履歴の削除中にエラーが発生しました: %s", str(e), exc_info=True)

    def cleanup_old_history(self, limit: int) -> None:
        """
        履歴上限値を超えている場合、ピン留めされていない最も古い履歴から順に削除して上限値に収めます。
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 現在の全件数を確認
                    cursor.execute("SELECT COUNT(*) FROM t_clipboard_history")
                    count = cursor.fetchone()[0]

                    if count <= limit:
                        return

                    excess = count - limit
                    # ピン留めされていない古い項目を古い順（created_at ASC）で取得
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
                        logger.info("履歴件数上限（%d件）を超過したため、ピン留めされていない古い項目を %d 件クリーンアップしました。", limit, len(ids_to_delete))
            except sqlite3.Error as e:
                logger.error("履歴自動クリーンアップ中にエラーが発生しました: %s", str(e), exc_info=True)

    # ==========================================
    # カテゴリ (t_category) 操作
    # ==========================================

    def add_category(self, name: str) -> int:
        """カテゴリを新規追加します。"""
        if not name:
            return -1
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 最大sort_orderを取得
                    cursor.execute("SELECT COALESCE(MAX(sort_order), 0) FROM t_category")
                    max_order = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "INSERT INTO t_category (name, sort_order) VALUES (?, ?)",
                        (name, max_order + 1)
                    )
                    new_id = cursor.lastrowid
                    conn.commit()
                    logger.info("カテゴリを追加しました: %s (ID: %d)", name, new_id)
                    return new_id
            except sqlite3.IntegrityError:
                logger.warning("カテゴリ名 '%s' は既に存在します。", name)
                return -1
            except sqlite3.Error as e:
                logger.error("カテゴリの追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_all_categories(self) -> list[tuple[int, str, int]]:
        """すべてのカテゴリを表示順（sort_order）で取得します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, sort_order FROM t_category ORDER BY sort_order ASC")
                    return cursor.fetchall()
            except sqlite3.Error as e:
                logger.error("カテゴリ一覧の取得中にエラーが発生しました: %s", str(e), exc_info=True)
                return []

    def update_category(self, category_id: int, new_name: str) -> bool:
        """カテゴリ名を更新します。"""
        if not new_name:
            return False
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE t_category SET name = ? WHERE id = ?", (new_name, category_id))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("カテゴリ名を更新しました (ID: %d -> '%s')", category_id, new_name)
                    return success
            except sqlite3.IntegrityError:
                logger.warning("カテゴリ名 '%s' は既に存在するため更新できません。", new_name)
                return False
            except sqlite3.Error as e:
                logger.error("カテゴリ名の更新中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def delete_category(self, category_id: int) -> bool:
        """カテゴリを削除します。外国キーの ON DELETE CASCADE により、属するメタ定型文も自動削除されます。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM t_category WHERE id = ?", (category_id,))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("カテゴリを削除しました (ID: %d)", category_id)
                    return success
            except sqlite3.Error as e:
                logger.error("カテゴリの削除中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def get_meta_phrase_count_by_category(self, category_id: int) -> int:
        """指定カテゴリに紐づいている定型文（メタ文）の件数を取得します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM t_meta_phrase WHERE category_id = ?", (category_id,))
                    return cursor.fetchone()[0]
            except sqlite3.Error as e:
                logger.error("カテゴリ内定型文の件数取得中にエラーが発生しました: %s", str(e), exc_info=True)
                return 0

    # ==========================================
    # メタ定型文 (t_meta_phrase) 操作
    # ==========================================

    def add_meta_phrase(self, title: str, content: str, category_id: int) -> int:
        """メタ定型文を新規追加します。"""
        if not title or not content:
            return -1
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # 同一カテゴリ内での最大sort_orderを取得
                    cursor.execute("SELECT COALESCE(MAX(sort_order), 0) FROM t_meta_phrase WHERE category_id = ?", (category_id,))
                    max_order = cursor.fetchone()[0]

                    cursor.execute(
                        "INSERT INTO t_meta_phrase (title, content, category_id, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
                        (title, content, category_id, max_order + 1, time.time())
                    )
                    new_id = cursor.lastrowid
                    conn.commit()
                    logger.info("メタ定型文を追加しました: %s (ID: %d)", title, new_id)
                    return new_id
            except sqlite3.Error as e:
                logger.error("メタ定型文の追加中にエラーが発生しました: %s", str(e), exc_info=True)
                return -1

    def get_meta_phrases_by_category(self, category_id: int | None = None) -> list[tuple[int, str, str, int, float]]:
        """
        特定カテゴリに属するメタ定型文を表示順（sort_order）で取得します。
        category_id が None の場合はすべてのメタ定型文を取得します。
        """
        sql = "SELECT id, title, content, category_id, created_at FROM t_meta_phrase"
        params = []

        if category_id is not None:
            sql += " WHERE category_id = ?"
            params.append(category_id)

        sql += " ORDER BY sort_order ASC, created_at DESC"

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, tuple(params))
                    rows = cursor.fetchall()
                    return [(row[0], row[1], row[2], row[3], float(row[4])) for row in rows]
            except sqlite3.Error as e:
                logger.error("メタ定型文の取得中にエラーが発生しました: %s", str(e), exc_info=True)
                return []

    def update_meta_phrase(self, phrase_id: int, title: str, content: str, category_id: int) -> bool:
        """メタ定型文を更新します。カテゴリの変更もサポートします。"""
        if not title or not content:
            return False
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE t_meta_phrase SET title = ?, content = ?, category_id = ? WHERE id = ?",
                        (title, content, category_id, phrase_id)
                    )
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("メタ定型文を更新しました (ID: %d)", phrase_id)
                    return success
            except sqlite3.Error as e:
                logger.error("メタ定型文の更新中にエラーが発生しました: %s", str(e), exc_info=True)
                return False

    def delete_meta_phrase(self, phrase_id: int) -> bool:
        """メタ定型文を削除します。"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM t_meta_phrase WHERE id = ?", (phrase_id,))
                    conn.commit()
                    success = cursor.rowcount > 0
                    if success:
                        logger.info("メタ定型文を削除しました (ID: %d)", phrase_id)
                    return success
            except sqlite3.Error as e:
                logger.error("メタ定型文の削除中にエラーが発生しました: %s", str(e), exc_info=True)
                return False
