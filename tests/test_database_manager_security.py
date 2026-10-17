from __future__ import annotations

import os
import stat
from pathlib import Path

from src.db.database_manager import DatabaseManager


def test_database_manager_creates_parent_directory(tmp_path: Path) -> None:
    """親ディレクトリが存在しない場合でも自動作成されて初期化が成功することを検証 (#126)。"""
    nested_dir = tmp_path / "deep" / "nested" / "dir"
    db_file = nested_dir / "test.db"

    assert not nested_dir.exists()

    manager = DatabaseManager(str(db_file))
    assert nested_dir.exists()
    assert db_file.exists()

    # 正常にクエリ可能であることを確認
    conn = manager._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "t_clipboard_history" in tables
    finally:
        conn.close()


def test_database_manager_permissions(tmp_path: Path) -> None:
    """POSIX環境において親ディレクトリ(0o700)およびDBファイル(0o600)のパーミッションが設定されることを検証 (#120)。"""
    nested_dir = tmp_path / "secure_dir"
    db_file = nested_dir / "secure.db"

    DatabaseManager(str(db_file))

    if os.name != "nt":
        dir_stat = os.stat(nested_dir)
        dir_mode = stat.S_IMODE(dir_stat.st_mode)
        assert dir_mode == 0o700

        file_stat = os.stat(db_file)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        assert file_mode == 0o600


def test_database_manager_in_memory() -> None:
    """:memory: の指定時にエラーなく初期化できることを検証。"""
    manager = DatabaseManager(":memory:")
    assert manager.db_path == ":memory:"
