from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

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


def test_check_and_migrate_json_success_and_backup(tmp_path: Path) -> None:
    """旧履歴JSONが正常に移行され、バックアップにアトミックに置換されることを検証 (#118)。"""
    import json

    db_file = tmp_path / "test.db"
    manager = DatabaseManager(str(db_file))

    json_file = tmp_path / "history.json"
    dummy_data = [
        "Simple String 1",
        ["Two Elements", True],
        ["Three Elements", False, 1700000000.0],
        ["Four Elements", True, 1700000050.0, "extra_metadata"],
    ]
    json_file.write_text(json.dumps(dummy_data), encoding="utf-8")

    manager.check_and_migrate_json(str(json_file))

    # 元ファイルは存在せず、.bak に置換されていること
    assert not json_file.exists()
    bak_file = tmp_path / "history.json.bak"
    assert bak_file.exists()

    # DBに4件登録されていること
    items = manager.history_dao.get_items(limit=10)
    assert len(items) == 4
    contents = [item.content for item in items]
    assert "Simple String 1" in contents
    assert "Two Elements" in contents
    assert "Three Elements" in contents
    assert "Four Elements" in contents


def test_check_and_migrate_json_handles_invalid_data_types(tmp_path: Path) -> None:
    """created_at が壊れたデータ型（文字列やNone等）でもクラッシュせずフォールバックされることを検証 (#123)。"""
    import json

    db_file = tmp_path / "test.db"
    manager = DatabaseManager(str(db_file))

    json_file = tmp_path / "broken_history.json"
    broken_data = [
        ["Valid Item", False, 1700000000.0],
        ["Broken Timestamp String", False, "not-a-timestamp"],
        ["Broken Timestamp None", True, None],
        ["Empty List"],
        12345,  # 要素自体が辞書や数値などの想定外型
    ]
    json_file.write_text(json.dumps(broken_data), encoding="utf-8")

    # クラッシュせずに完了すること
    manager.check_and_migrate_json(str(json_file))

    items = manager.history_dao.get_items(limit=10)
    contents = [item.content for item in items]
    assert "Valid Item" in contents
    assert "Broken Timestamp String" in contents


def test_check_and_migrate_json_rejects_symlink(tmp_path: Path) -> None:
    """シンボリックリンク経由の指定が拒否され移行されないことを検証 (#118)。"""
    import json

    db_file = tmp_path / "test.db"
    manager = DatabaseManager(str(db_file))

    real_json = tmp_path / "real_history.json"
    real_json.write_text(json.dumps(["Secret Data"]), encoding="utf-8")

    link_path = tmp_path / "link_history.json"
    try:
        os.symlink(real_json, link_path)
    except OSError:
        pytest.skip("Symlink not supported in this environment")

    manager.check_and_migrate_json(str(link_path))

    # シンボリックリンクは移行されず、削除や移動もされない
    assert link_path.is_symlink()
    items = manager.history_dao.get_items(limit=10)
    assert len(items) == 0
