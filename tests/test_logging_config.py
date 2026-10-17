"""tests/test_logging_config.py

logging_config のパーミッション制御および空ログクリーンアップの安全性テスト（#136, #176）。
"""

from __future__ import annotations

import logging
import os
import stat
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.logging_config import (
    DailyFileHandler,
    _cleanup_empty_logs,
    setup_logging,
)


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """setup_logging がルートロガーのハンドラを変更するため、テスト後に復元する。"""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    yield
    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_setup_logging_sets_restrictive_permissions(tmp_path: Path) -> None:
    """ログディレクトリ(0o700)とログファイル(0o600)の権限が制限されることを検証する。"""
    log_dir = tmp_path / "logs"

    with patch("os.chmod", wraps=os.chmod) as mock_chmod:
        setup_logging(str(log_dir))

    chmod_calls = [
        (Path(call.args[0]), call.args[1]) for call in mock_chmod.call_args_list
    ]
    assert (log_dir, 0o700) in chmod_calls
    assert any(path.parent == log_dir and mode == 0o600 for path, mode in chmod_calls)

    if os.name == "posix":
        dir_mode = stat.S_IMODE(log_dir.stat().st_mode)
        assert dir_mode == 0o700
        log_files = list(log_dir.glob("clipwatcher_*.log"))
        assert len(log_files) == 1
        file_mode = stat.S_IMODE(log_files[0].stat().st_mode)
        assert file_mode == 0o600


def test_daily_file_handler_rollover_restricts_new_file_permissions(
    tmp_path: Path,
) -> None:
    """日付変更時のローテーションで新規生成されるログファイルにも 0o600 が適用される。"""
    handler = DailyFileHandler(str(tmp_path))
    try:
        handler.current_date = "19990101"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="rollover message",
            args=(),
            exc_info=None,
        )
        with patch("os.chmod", wraps=os.chmod) as mock_chmod:
            handler.emit(record)

        assert any(
            Path(call.args[0]) == Path(handler.baseFilename) and call.args[1] == 0o600
            for call in mock_chmod.call_args_list
        )
    finally:
        handler.close()


def test_cleanup_empty_logs_removes_only_empty_regular_log_files(
    tmp_path: Path,
) -> None:
    """空の通常 .log のみ削除し、非空ファイルやシンボリックリンクは削除しない。"""
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("", encoding="utf-8")

    non_empty_log = tmp_path / "active.log"
    non_empty_log.write_text("some log content\n", encoding="utf-8")

    target_file = tmp_path / "external_empty.txt"
    target_file.write_text("", encoding="utf-8")
    symlink_log = tmp_path / "symlink.log"
    try:
        symlink_log.symlink_to(target_file)
        symlink_created = True
    except (OSError, NotImplementedError):
        symlink_created = False

    _cleanup_empty_logs(str(tmp_path))

    assert not empty_log.exists()
    assert non_empty_log.exists()
    assert target_file.exists()
    if symlink_created:
        assert symlink_log.is_symlink()


def test_cleanup_empty_logs_continues_on_toctou_oserror(tmp_path: Path) -> None:
    """1つのファイル削除で OSError が起きても残りの空ログ削除が継続される。"""
    first_log = tmp_path / "a_first.log"
    first_log.write_text("", encoding="utf-8")
    second_log = tmp_path / "b_second.log"
    second_log.write_text("", encoding="utf-8")

    real_remove = os.remove

    def flaky_remove(path: str) -> None:
        if path.endswith("a_first.log"):
            raise PermissionError("simulated TOCTOU lock")
        real_remove(path)

    with patch("os.remove", side_effect=flaky_remove):
        _cleanup_empty_logs(str(tmp_path))

    assert first_log.exists()
    assert not second_log.exists()
