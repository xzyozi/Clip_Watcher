from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import datetime

from src.core.text_workflow.models import HistoryEntry

logger = logging.getLogger(__name__)


class ExecutionHistory:
    """Workflow の実行履歴を保存・管理するアダプター"""

    def __init__(self, db_path: str = ":memory:", max_records: int = 500) -> None:
        self._db_path = db_path
        self._max_records = max_records
        self._lock = threading.Lock()
        self._is_closed = False

        if self._db_path != ":memory:":
            db_dir = os.path.dirname(os.path.abspath(self._db_path))
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o700, exist_ok=True)
            if not os.path.exists(self._db_path):
                try:
                    fd = os.open(self._db_path, os.O_CREAT | os.O_RDWR, 0o600)
                    os.close(fd)
                except OSError as e:
                    logger.warning(
                        "履歴DBファイルのパーミッション事前設定に失敗しました: %s", e
                    )
            elif os.name != "nt":
                try:
                    os.chmod(self._db_path, 0o600)
                except OSError:
                    pass

        # :memory: やファイル DB 用のコネクションを準備
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS t_workflow_history (
                        record_id TEXT PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        category_id TEXT NOT NULL,
                        rule_id TEXT,
                        template_id TEXT,
                        input_text TEXT NOT NULL,
                        output_text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

    def record(self, entry: HistoryEntry) -> bool:
        """履歴レコードを追加し、上限を超えた場合は古いレコードを削除する"""
        with self._lock:
            if self._is_closed:
                return False
            try:
                with self._conn:
                    self._conn.execute(
                        """
                        INSERT INTO t_workflow_history (
                            record_id, request_id, category_id, rule_id, template_id, input_text, output_text, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry.record_id,
                            entry.request_id,
                            entry.category_id,
                            entry.rule_id,
                            entry.template_id,
                            entry.input_text,
                            entry.output_text,
                            entry.created_at or datetime.now().isoformat(),
                        ),
                    )

                    # 上限パージ
                    self._conn.execute(
                        """
                        DELETE FROM t_workflow_history
                        WHERE record_id NOT IN (
                            SELECT record_id FROM t_workflow_history
                            ORDER BY created_at DESC
                            LIMIT ?
                        )
                        """,
                        (self._max_records,),
                    )
                return True
            except Exception:
                return False

    def get_recent(self, limit: int = 50) -> list[HistoryEntry]:
        """最新の履歴を取得する"""
        with self._lock:
            if self._is_closed:
                return []
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT record_id, request_id, category_id, rule_id, template_id, input_text, output_text, created_at
                FROM t_workflow_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                HistoryEntry(
                    record_id=r[0],
                    request_id=r[1],
                    category_id=r[2],
                    rule_id=r[3],
                    template_id=r[4],
                    input_text=r[5],
                    output_text=r[6],
                    created_at=r[7],
                )
                for r in rows
            ]

    def close(self) -> None:
        """データベース接続を閉じる"""
        with self._lock:
            if not self._is_closed:
                self._is_closed = True
                try:
                    self._conn.close()
                except Exception as e:
                    logger.warning(
                        "履歴DB接続のクローズ中にエラーが発生しました: %s", e
                    )
