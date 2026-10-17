"""tests/test_app_main_paste.py

MainApplication._paste_into_active_window() が PlatformServices 経由で貼り付けを送り、
非対応環境では警告して継続（クリップボードには設定済み）することを検証する。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.core.app_main import MainApplication
from src.core.platform.services import PlatformServices


@pytest.fixture
def make_app() -> Iterator[Callable[[PlatformServices], MainApplication]]:
    def _make(services: PlatformServices) -> MainApplication:
        settings = MagicMock()
        settings.get_setting.side_effect = lambda key, default=None: default
        return MainApplication(
            master=MagicMock(),
            settings_manager=settings,
            db_manager=MagicMock(),
            history_service=MagicMock(),
            monitor=MagicMock(),
            plugin_manager=MagicMock(),
            event_dispatcher=MagicMock(),
            theme_manager=MagicMock(),
            translator=MagicMock(),
            app_status=MagicMock(),
            platform_services=services,
            notification_manager=MagicMock(),
        )

    with (
        patch("src.core.app_main.ClipWatcherGUI"),
        patch("src.core.app_main.menu_bar"),
        patch("src.event_handlers.register_class_based_handlers"),
    ):
        yield _make


def test_paste_is_sent_when_supported(
    make_app: Callable[[PlatformServices], MainApplication],
) -> None:
    sender = MagicMock()
    sender.are_modifiers_released.return_value = True
    sender.paste_active_window.return_value = True
    app = make_app(PlatformServices(paste_sender=sender, platform_name="win32"))

    app._paste_into_active_window()

    sender.paste_active_window.assert_called_once_with()


def test_paste_retries_while_modifiers_are_held(
    make_app: Callable[[PlatformServices], MainApplication],
) -> None:
    sender = MagicMock()
    sender.are_modifiers_released.return_value = False
    app = make_app(PlatformServices(paste_sender=sender, platform_name="win32"))

    app._paste_into_active_window()

    sender.paste_active_window.assert_not_called()
    app.master.after.assert_called_once()


def test_unsupported_paste_warns_and_does_not_raise_or_retry(
    make_app: Callable[[PlatformServices], MainApplication],
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = make_app(PlatformServices(platform_name="darwin"))

    with caplog.at_level(logging.WARNING, logger="src.core.app_main"):
        app._paste_into_active_window()

    app.master.after.assert_not_called()
    assert any("paste_sender" in record.getMessage() for record in caplog.records)
