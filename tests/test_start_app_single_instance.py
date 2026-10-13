"""tests/test_start_app_single_instance.py

start_app() が SingleInstanceController の3つの結果を区別して扱うことを検証する。

- 重複起動 (acquire() が False): 「Already Running」を表示して終了する。
- 取得 API の失敗 (SingleInstanceError): 重複起動とは区別してエラー表示し、終了する。
- 非対応環境 (UnsupportedFeatureError): 警告して、多重起動を許したまま起動する。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.errors import SingleInstanceError
from src.core.platform.services import PlatformServices
from src.event_handlers import start_app


class _Env:
    """start_app() の外部依存を差し替えた実行環境。"""

    def __init__(self) -> None:
        self.messagebox = MagicMock()
        self.builder_class = MagicMock()
        self.logger = MagicMock()
        self.root = MagicMock()


@pytest.fixture
def env() -> Iterator[_Env]:
    environment = _Env()
    environment.root.mainloop.side_effect = KeyboardInterrupt
    builder = environment.builder_class.return_value
    # チェーン呼び出しは常に builder 自身を返す
    for name in (
        "with_event_dispatcher",
        "with_dependency_check",
        "with_settings",
        "with_database",
        "with_translator",
        "with_theme_manager",
        "with_icon_manager",
        "with_history_service",
        "with_text_workflow_service",
        "with_plugin_manager",
        "with_window_state_manager",
        "with_global_hotkey_listener",
        "with_hotkey_registration_manager",
        "with_clipboard_monitor",
    ):
        getattr(builder, name).return_value = builder

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.event_handlers.messagebox", environment.messagebox)
        )
        stack.enter_context(
            patch("src.event_handlers.ApplicationBuilder", environment.builder_class)
        )
        stack.enter_context(
            patch("src.event_handlers.setup_logging", return_value=environment.logger)
        )
        stack.enter_context(patch("src.event_handlers.os.makedirs"))
        stack.enter_context(patch("scripts.migrate_json_to_sqlite.main"))
        stack.enter_context(
            patch("src.event_handlers.tk.Tk", return_value=environment.root)
        )
        yield environment


def _run(services: PlatformServices) -> None:
    with patch(
        "src.event_handlers.PlatformServices.for_current_platform",
        return_value=services,
    ):
        try:
            start_app()
        except KeyboardInterrupt:
            pass  # mainloop の代わりに送出させたもの


def test_already_running_shows_info_and_does_not_start(env: _Env) -> None:
    controller = MagicMock()
    controller.acquire.return_value = False
    services = PlatformServices(single_instance=controller, platform_name="win32")

    _run(services)

    env.messagebox.showinfo.assert_called_once()
    env.messagebox.showerror.assert_not_called()
    env.builder_class.assert_not_called()


def test_single_instance_error_shows_error_distinct_from_already_running(
    env: _Env,
) -> None:
    controller = MagicMock()
    controller.acquire.side_effect = SingleInstanceError("CreateMutexW failed")
    services = PlatformServices(single_instance=controller, platform_name="win32")

    _run(services)

    env.messagebox.showerror.assert_called_once()
    env.messagebox.showinfo.assert_not_called()
    env.builder_class.assert_not_called()


def test_acquired_lock_is_released_on_exit(env: _Env) -> None:
    controller = MagicMock()
    controller.acquire.return_value = True
    services = PlatformServices(single_instance=controller, platform_name="win32")

    _run(services)

    env.builder_class.assert_called_once_with(services)
    controller.release.assert_called_once_with()


def test_unsupported_single_instance_warns_and_still_starts(env: _Env) -> None:
    services = PlatformServices(platform_name="darwin")

    _run(services)

    env.messagebox.showinfo.assert_not_called()
    env.messagebox.showerror.assert_not_called()
    env.builder_class.assert_called_once_with(services)
    warning_messages = [call.args[0] for call in env.logger.warning.call_args_list]
    assert any("single_instance" in message for message in warning_messages)
