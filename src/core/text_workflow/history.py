from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HistoryEntry:
    record_id: str
    request_id: str
    category_id: str
    rule_id: str | None
    template_id: str | None
    input_text: str
    output_text: str
    created_at: str


class ExecutionHistory:
    """Workflow の実行履歴を保存・管理するアダプター"""

    def __init__(self, db_path: str = ":memory:", max_records: int = 500) -> None:
        self._db_path = db_path
        self._max_records = max_records
        # :memory: やファイル DB 用のコネクションを準備
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
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
        self._conn.close()
