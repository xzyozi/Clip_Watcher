"""tests/test_notification_manager.py

NotificationManager が PlatformServices 経由で通知音を再生し、
非対応環境では明示的にスキップすることを検証する。
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.services import PlatformServices
from src.services.notification_manager import NotificationManager


def _manager(
    services: PlatformServices, *, sound_enabled: bool = True
) -> NotificationManager:
    return NotificationManager(services, {"notification_sound_enabled": sound_enabled})


def test_plays_beep_when_enabled_and_supported() -> None:
    player = MagicMock()
    manager = _manager(PlatformServices(sound_player=player, platform_name="win32"))

    manager.play_notification_sound()

    player.play_notification_beep.assert_called_once_with(1000, 200)


def test_does_not_play_when_disabled() -> None:
    player = MagicMock()
    manager = _manager(
        PlatformServices(sound_player=player, platform_name="win32"),
        sound_enabled=False,
    )

    manager.play_notification_sound()

    player.play_notification_beep.assert_not_called()


def test_skips_with_debug_log_when_sound_player_is_unsupported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """非対応環境では例外を握りつぶさず、スキップしたことをログに残す。"""
    manager = _manager(PlatformServices(platform_name="darwin"))

    with (
        patch("src.utils.error_handler.log_and_show_error") as show_error,
        caplog.at_level(logging.DEBUG, logger="src.services.notification_manager"),
    ):
        manager.play_notification_sound()

    show_error.assert_not_called()
    assert any("sound_player" in record.getMessage() for record in caplog.records)


def test_playback_failure_logs_warning_without_gui_dialog(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """通知音の再生時に例外が発生しても messagebox を呼ばず、WARNING ログのみ記録する（#133）。"""
    player = MagicMock()
    player.play_notification_beep.side_effect = RuntimeError("device busy")
    manager = _manager(PlatformServices(sound_player=player, platform_name="win32"))

    with (
        patch("src.utils.error_handler.log_and_show_error") as show_error,
        caplog.at_level(logging.WARNING, logger="src.services.notification_manager"),
    ):
        manager.play_notification_sound()

    show_error.assert_not_called()
    assert any(
        record.levelno == logging.WARNING and "device busy" in record.getMessage()
        for record in caplog.records
    )
