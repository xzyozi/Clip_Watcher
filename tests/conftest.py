from __future__ import annotations

from collections.abc import Generator

import pytest

from src.core.events.event_dispatcher import EventDispatcher
from src.db.database_manager import DatabaseManager
from src.services.history_service import HistoryService


@pytest.fixture
def event_dispatcher() -> EventDispatcher:
    """テスト用のクリーンな EventDispatcher インスタンスを提供します。"""
    return EventDispatcher()


@pytest.fixture
def db_manager() -> Generator[DatabaseManager, None, None]:
    """テスト用の一時的な SQLite DB ファイルを使用した DatabaseManager インスタンスを提供します。"""
    import os
    db_path = "test_temp_db.db"

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    manager = DatabaseManager(db_path=db_path)
    yield manager

    # クリーンアップ
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


@pytest.fixture
def history_service(db_manager: DatabaseManager, event_dispatcher: EventDispatcher) -> HistoryService:
    """テスト用の HistoryService インスタンスを提供します（制限件数は5件に設定）。"""
    return HistoryService(
        db_manager=db_manager,
        event_dispatcher=event_dispatcher,
        history_limit=5
    )
