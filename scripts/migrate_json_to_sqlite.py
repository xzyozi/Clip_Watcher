#!/usr/bin/env python
from __future__ import annotations

import logging
import os
import sys

# プロジェクトのルートディレクトリを sys.path に追加して src がインポートできるようにする
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.db.database_manager import DatabaseManager  # noqa: E402
from src.utils.logging_config import setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> None:
    # ロギングのセットアップ
    setup_logging()
    logger.info("JSONからSQLiteへのマイグレーションスクリプトを起動します。")

    # アプリケーションデータディレクトリの特定
    if sys.platform == "win32":
        app_data_dir = os.path.join(os.environ["USERPROFILE"], ".clipWatcher")
    else:
        app_data_dir = os.path.join(os.path.expanduser("~"), ".clipwatcher")

    history_file_path = os.path.join(app_data_dir, "history.json")
    db_path = os.path.join(app_data_dir, "clip_watcher.db")

    logger.info("対象履歴ファイル: %s", history_file_path)
    logger.info("対象データベース: %s", db_path)

    if not os.path.exists(history_file_path):
        logger.info(
            "移行対象の旧履歴ファイル（history.json）が存在しないため、マイグレーションを終了します。"
        )
        return

    try:
        db_manager = DatabaseManager(db_path)
        logger.info("マイグレーションを開始します...")
        db_manager.check_and_migrate_json(history_file_path)
        logger.info("マイグレーションが正常に終了しました。")
    except Exception as e:
        logger.error(
            "マイグレーション実行中に予期せぬエラーが発生しました: %s",
            str(e),
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
