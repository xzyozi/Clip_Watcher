"""ClipboardMonitor の取得・重複判定・除外アプリ・監視ループのテスト。"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.platform.services import PlatformServices


def _make(
    *, services: PlatformServices | None = None, excluded: list[str] | None = None
) -> ClipboardMonitor:
    return ClipboardMonitor(
        tk_root=MagicMock(),
        event_dispatcher=MagicMock(),
        history_file_path="history.json",
        db_manager=MagicMock(),
        history_service=MagicMock(history=[], last_clipboard_data=""),
        platform_services=services or PlatformServices(platform_name="test"),
        excluded_apps=excluded,
    )


def _services(inspector: Any = None, reader: Any = None) -> PlatformServices:
    return PlatformServices(
        process_inspector=inspector, clipboard_reader=reader, platform_name="test"
    )


# --- 設定・プロセス判定 ---


def test_settings_change_updates_limit_and_exclusions() -> None:
    monitor = _make()
    monitor.on_settings_changed({"history_limit": 7, "excluded_apps": ["a.exe"]})
    assert (monitor.history_limit, monitor.excluded_apps) == (7, ["a.exe"])
    monitor.on_settings_changed({})
    assert monitor.excluded_apps == []


def test_error_callback_is_stored() -> None:
    monitor = _make()
    callback = MagicMock()
    monitor.set_error_callback(callback)
    assert monitor.error_callback is callback


def test_active_process_name_comes_from_inspector_or_none() -> None:
    inspector = MagicMock()
    inspector.get_active_process_name.return_value = "app.exe"
    assert (
        _make(services=_services(inspector=inspector)).get_active_process_name()
        == "app.exe"
    )
    assert _make().get_active_process_name() is None


@pytest.mark.parametrize(
    ("excluded", "level"), [(["x.exe"], logging.ERROR), ([], logging.WARNING)]
)
def test_unsupported_inspector_is_reported_once(
    caplog: pytest.LogCaptureFixture, excluded: list[str], level: int
) -> None:
    monitor = _make(excluded=excluded)
    with caplog.at_level(logging.WARNING):
        monitor._report_process_inspector_support()
        monitor._report_process_inspector_support()
    records = [r for r in caplog.records if "process_inspector" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == level


# --- 取得とデコード ---


def test_clipboard_text_is_read_from_tk_first() -> None:
    monitor = _make()
    monitor.tk_root.clipboard_get.return_value = "from tk"
    assert monitor._get_clipboard_content() == "from tk"


def test_clipboard_falls_back_to_platform_reader() -> None:
    reader = MagicMock()
    reader.read_text.return_value = "from reader"
    monitor = _make(services=_services(reader=reader))
    monitor.tk_root.clipboard_get.side_effect = tk.TclError("no text")
    assert monitor._get_clipboard_content() == "from reader"


def test_unsupported_reader_returns_none_and_warns_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    monitor = _make()
    monitor.tk_root.clipboard_get.side_effect = UnicodeDecodeError(
        "utf-8", b"", 0, 1, "bad"
    )
    with caplog.at_level(logging.WARNING):
        assert monitor._get_clipboard_content() is None
        assert monitor._get_clipboard_content() is None
    assert sum("clipboard_reader" in r.getMessage() for r in caplog.records) == 1


def test_current_text_validates_and_normalizes() -> None:
    monitor = _make()
    monitor.tk_root.clipboard_get.return_value = "text"
    assert monitor.get_current_clipboard_text() == "text"

    monitor.tk_root.clipboard_get.return_value = ""
    assert monitor.get_current_clipboard_text() is None

    monitor.tk_root.clipboard_get.return_value = "x" * (1024 * 1024 + 1)
    assert monitor.get_current_clipboard_text() is None


def test_current_text_is_none_when_clipboard_is_unreadable() -> None:
    monitor = _make()
    with patch.object(monitor, "_get_clipboard_content", return_value=None):
        assert monitor.get_current_clipboard_text() is None


def test_current_text_uses_str_when_decoding_fails() -> None:
    monitor = _make()
    with (
        patch.object(monitor, "_get_clipboard_content", return_value=123),
        patch.object(monitor, "_decode_clipboard_data", side_effect=ValueError("bad")),
    ):
        assert monitor.get_current_clipboard_text() == "123"


# --- 履歴更新 ---


def test_update_clipboard_sets_clipboard_and_adds_history() -> None:
    monitor = _make()
    monitor.update_clipboard("hello")
    monitor.tk_root.clipboard_clear.assert_called_once()
    monitor.tk_root.clipboard_append.assert_called_once_with("hello")
    monitor.history_service.add_history_item.assert_called_once_with("hello")


def test_update_clipboard_ignores_empty_text() -> None:
    monitor = _make()
    monitor.update_clipboard("")
    monitor.tk_root.clipboard_clear.assert_not_called()
    monitor.history_service.add_history_item.assert_not_called()


def test_update_clipboard_always_writes_even_when_text_matches_latest_history() -> None:
    """Issue #229: 履歴の直近項目と同じ内容でも、システムクリップボードへ書き込む。

    実際のクリップボードが別の内容（履歴に残らないコピーなど）へ変わっていても、
    ユーザーが選んだ内容を確実に反映する。履歴の重複抑止は add_history_item() に委ねる。
    """
    monitor = _make()
    monitor.history_service.history = [("old", False, 1.0), ("latest", True, 9.0)]
    monitor.update_clipboard("latest")
    monitor.tk_root.clipboard_clear.assert_called_once()
    monitor.tk_root.clipboard_append.assert_called_once_with("latest")
    monitor.history_service.add_history_item.assert_called_once_with("latest")


def test_update_clipboard_keeps_history_when_clipboard_update_fails() -> None:
    monitor = _make()
    monitor.tk_root.clipboard_clear.side_effect = tk.TclError("busy")
    monitor.update_clipboard("hello")
    monitor.history_service.add_history_item.assert_not_called()


def test_new_entry_is_added_unless_app_is_excluded() -> None:
    inspector = MagicMock()
    inspector.get_active_process_name.return_value = "KeePass.exe"
    monitor = _make(services=_services(inspector=inspector), excluded=["keepass.exe"])
    monitor._update_history_with_new_entry("secret")
    monitor.history_service.add_history_item.assert_not_called()
    assert monitor.history_service.last_clipboard_data == "secret"

    inspector.get_active_process_name.return_value = "notepad.exe"
    monitor._update_history_with_new_entry("note")
    monitor.history_service.add_history_item.assert_called_once_with("note")


def test_new_entry_without_process_information_is_added() -> None:
    monitor = _make(excluded=["a.exe"])
    monitor._update_history_with_new_entry("text")
    monitor.history_service.add_history_item.assert_called_once_with("text")


# --- 同期・ポーリング ---


def test_initial_sync_adds_changed_clipboard_only() -> None:
    monitor = _make()
    monitor.tk_root.clipboard_get.return_value = "current"
    monitor.history_service.last_clipboard_data = "older"
    assert monitor.sync_initial_clipboard() == "current"
    monitor.history_service.add_history_item.assert_called_once_with("current")

    monitor.history_service.add_history_item.reset_mock()
    monitor.history_service.last_clipboard_data = "current"
    assert monitor.sync_initial_clipboard() == "current"
    monitor.history_service.add_history_item.assert_not_called()


def test_initial_sync_handles_empty_clipboard_and_errors() -> None:
    monitor = _make()
    with patch.object(monitor, "get_current_clipboard_text", return_value=None):
        assert monitor.sync_initial_clipboard() is None
    with patch.object(monitor, "get_current_clipboard_text", side_effect=RuntimeError):
        assert monitor.sync_initial_clipboard() is None


def test_check_clipboard_detects_changes_and_survives_errors() -> None:
    monitor = _make()
    monitor.tk_root.clipboard_get.return_value = "new"
    monitor._check_clipboard()
    monitor.history_service.add_history_item.assert_called_once_with("new")

    monitor.history_service.add_history_item.reset_mock()
    monitor.history_service.last_clipboard_data = "new"
    monitor._check_clipboard()
    monitor.history_service.add_history_item.assert_not_called()

    with patch.object(monitor, "get_current_clipboard_text", return_value=None):
        monitor._check_clipboard()
    with patch.object(monitor, "get_current_clipboard_text", side_effect=RuntimeError):
        monitor._check_clipboard()  # 例外を送出しない


def _run_loop(
    monitor: ClipboardMonitor, errors: list[BaseException | None]
) -> list[float]:
    """after() が errors を順に送出する間、監視ループを回す。待機時間を記録して返す。"""
    pending = list(errors)
    sleeps: list[float] = []

    def after(_delay: int, _callback: Any) -> None:
        error = pending.pop(0)
        if not pending:
            monitor._running = False
        if error is not None:
            raise error

    monitor.tk_root.after.side_effect = after
    monitor._running = True
    with patch(
        "src.core.clipboard.clipboard_monitor.time.sleep", side_effect=sleeps.append
    ):
        monitor._monitor_clipboard()
    return sleeps


def test_monitor_loop_polls_and_backs_off_on_errors() -> None:
    monitor = _make()
    sleeps = _run_loop(monitor, [None, RuntimeError("tk"), ValueError("other")])
    assert sleeps == [0.5, 1, 5]


def test_start_runs_monitor_thread_once_and_stop_joins_it() -> None:
    monitor = _make()
    with patch("src.core.clipboard.clipboard_monitor.threading.Thread") as thread_cls:
        thread = thread_cls.return_value
        thread.is_alive.return_value = True
        monitor.start()
        monitor.start()  # 二重起動しない
        thread_cls.assert_called_once()
        thread.start.assert_called_once()

        monitor.stop()
        thread.join.assert_called_once_with(timeout=2)
    assert monitor._running is False


def test_stop_without_thread_and_save_history_are_noops() -> None:
    monitor = _make()
    monitor.stop()
    monitor.save_history_to_file()
