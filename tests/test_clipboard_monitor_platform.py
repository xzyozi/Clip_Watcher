"""tests/test_clipboard_monitor_platform.py

ClipboardMonitor が ProcessInspector の非対応環境で、明示的に縮退することを検証する。

- 起動時に WARNING を1回出す。excluded_apps が設定済みなら ERROR に格上げする。
- 除外判定ができなくても、履歴保存は継続する。
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.events.event_dispatcher import EventDispatcher
from src.core.platform.services import PlatformServices
from src.services.history_service import HistoryService


def _monitor(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    services: PlatformServices,
    excluded_apps: list[str] | None = None,
) -> ClipboardMonitor:
    return ClipboardMonitor(
        tk_root=mocker.Mock(),
        event_dispatcher=event_dispatcher,
        history_file_path="dummy.json",
        db_manager=mocker.Mock(),
        history_service=history_service,
        platform_services=services,
        history_limit=5,
        excluded_apps=excluded_apps,
    )


def _start(monitor: ClipboardMonitor) -> None:
    """監視スレッドを起動せずに start() の起動時処理だけを実行する。"""
    with patch("src.core.clipboard.clipboard_monitor.threading.Thread"):
        monitor.start()


def test_start_logs_warning_once_when_process_inspector_is_unsupported(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    platform_services: PlatformServices,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monitor = _monitor(mocker, event_dispatcher, history_service, platform_services)

    with caplog.at_level(logging.INFO):
        _start(monitor)
        monitor.stop()
        _start(monitor)

    records = [r for r in caplog.records if "process_inspector" in r.getMessage()]
    assert [r.levelno for r in records] == [logging.WARNING]


def test_start_logs_error_when_excluded_apps_are_configured_but_unsupported(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    platform_services: PlatformServices,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """設定があるのに効かない状態を目立たせるため ERROR に格上げする。"""
    monitor = _monitor(
        mocker,
        event_dispatcher,
        history_service,
        platform_services,
        excluded_apps=["KeePass.exe"],
    )

    with caplog.at_level(logging.INFO):
        _start(monitor)

    records = [r for r in caplog.records if "process_inspector" in r.getMessage()]
    assert [r.levelno for r in records] == [logging.ERROR]


def test_start_logs_nothing_when_process_inspector_is_supported(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    inspector = MagicMock()
    services = PlatformServices(process_inspector=inspector, platform_name="win32")
    monitor = _monitor(
        mocker, event_dispatcher, history_service, services, ["KeePass.exe"]
    )

    with caplog.at_level(logging.INFO):
        _start(monitor)

    assert not [r for r in caplog.records if "process_inspector" in r.getMessage()]


def test_history_is_still_saved_when_process_inspector_is_unsupported(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    platform_services: PlatformServices,
) -> None:
    monitor = _monitor(
        mocker,
        event_dispatcher,
        history_service,
        platform_services,
        excluded_apps=["KeePass.exe"],
    )

    monitor._update_history_with_new_entry("copied text")

    assert [item[0] for item in history_service.history] == ["copied text"]


def test_get_active_process_name_uses_supported_inspector(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
) -> None:
    inspector = MagicMock()
    inspector.get_active_process_name.return_value = "notepad.exe"
    services = PlatformServices(process_inspector=inspector, platform_name="win32")
    monitor = _monitor(mocker, event_dispatcher, history_service, services)

    assert monitor.get_active_process_name() == "notepad.exe"
