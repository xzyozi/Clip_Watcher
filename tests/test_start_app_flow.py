"""start_app() の起動シーケンス（OS 別分岐・エラー処理）と補助関数のテスト。"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src import event_handlers
from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.services import PlatformServices
from src.event_handlers import (
    _acquire_single_instance,
    _release_single_instance,
    register_class_based_handlers,
    start_app,
)


@pytest.fixture
def env() -> Iterator[SimpleNamespace]:
    environment = SimpleNamespace(
        messagebox=MagicMock(),
        builder_class=MagicMock(),
        logger=MagicMock(),
        root=MagicMock(),
        makedirs=MagicMock(),
    )
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
        stack.enter_context(
            patch("src.event_handlers.os.makedirs", environment.makedirs)
        )
        stack.enter_context(patch("scripts.migrate_json_to_sqlite.main"))
        stack.enter_context(
            patch("src.event_handlers.tk.Tk", return_value=environment.root)
        )
        # macOS 実機の CI では、本物の `defaults` コマンドを起動してハングし得るため、
        # OS 判定のヘルパーは既定でモックする（各テストが必要に応じて上書きする）。
        stack.enter_context(
            patch("src.utils.platform_utils.is_macos_dark_mode", return_value=False)
        )
        stack.enter_context(
            patch("src.utils.platform_utils.is_legacy_macos_tk", return_value=False)
        )
        yield environment


def _services(controller: MagicMock | None = None) -> PlatformServices:
    controller = controller or MagicMock(**{"acquire.return_value": True})
    return PlatformServices(single_instance=controller, platform_name="test")


def _run(services: PlatformServices) -> None:
    with patch(
        "src.event_handlers.PlatformServices.for_current_platform",
        return_value=services,
    ):
        try:
            start_app()
        except KeyboardInterrupt:
            pass  # mainloop の代わりに送出させたもの


# --- 補助関数 ---


def test_register_handlers_attaches_all_handler_objects() -> None:
    app = MagicMock()
    register_class_based_handlers(app)
    assert app.history_handlers is not None
    assert app.file_handlers is not None
    assert app.settings_handlers is not None


def test_acquire_single_instance_outcomes() -> None:
    controller = MagicMock()
    controller.acquire.return_value = True
    services = PlatformServices(single_instance=controller, platform_name="t")
    assert _acquire_single_instance(services) == (controller, False)

    controller.acquire.return_value = False
    assert _acquire_single_instance(services) == (None, True)

    assert _acquire_single_instance(PlatformServices(platform_name="t")) == (
        None,
        False,
    )


def test_release_single_instance_handles_none_and_controller() -> None:
    _release_single_instance(None)
    controller = MagicMock()
    _release_single_instance(controller)
    controller.release.assert_called_once()


# --- 起動シーケンス ---


def test_successful_start_builds_application_and_releases_lock(
    env: SimpleNamespace,
) -> None:
    controller = MagicMock(**{"acquire.return_value": True})
    _run(_services(controller))
    env.builder_class.return_value.build.assert_called_once_with(env.root)
    env.root.mainloop.assert_called_once()
    controller.release.assert_called_once()


def test_unsupported_single_instance_logs_warning_and_continues(
    env: SimpleNamespace,
) -> None:
    services = MagicMock()
    services.single_instance.side_effect = UnsupportedFeatureError("single", "t")
    _run(services)
    assert any("single_instance" in str(c) for c in env.logger.warning.call_args_list)
    env.builder_class.return_value.build.assert_called_once()


def test_posix_data_directory_is_hidden_folder_in_home(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    _run(_services())
    created = env.makedirs.call_args.args[0]
    assert created.endswith(".clipwatcher")


def test_windows_data_directory_uses_userprofile(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("USERPROFILE", "C:/Users/test")
    _run(_services())
    assert env.makedirs.call_args.args[0].endswith(".clipWatcher")


def test_migration_failure_is_logged_and_start_continues(env: SimpleNamespace) -> None:
    with patch("scripts.migrate_json_to_sqlite.main", side_effect=RuntimeError("bad")):
        _run(_services())
    env.logger.error.assert_called()
    env.builder_class.return_value.build.assert_called_once()


def test_unexpected_error_is_logged_and_lock_is_released(env: SimpleNamespace) -> None:
    env.builder_class.side_effect = RuntimeError("boom")
    controller = MagicMock(**{"acquire.return_value": True})
    _run(_services(controller))
    assert any("起動エラー" in str(c) for c in env.logger.error.call_args_list)
    controller.release.assert_called_once()


def test_error_before_logging_is_printed_not_logged(
    env: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    controller = MagicMock()
    controller.acquire.side_effect = RuntimeError("lock exploded")
    _run(_services(controller))
    assert "アプリケーション起動エラー" in capsys.readouterr().out
    env.logger.error.assert_not_called()


def test_macos_legacy_tk_shows_alert_and_exits(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    with (
        patch("src.utils.platform_utils.is_macos_dark_mode", return_value=False),
        patch("src.utils.platform_utils.is_legacy_macos_tk", return_value=True),
        patch(
            "src.utils.platform_utils.apply_macos_aqua_appearance", return_value=True
        ) as aqua,
        patch("subprocess.run") as run,
    ):
        _run(_services())
    aqua.assert_called_once_with(env.root)
    run.assert_called_once()
    env.root.destroy.assert_called_once()
    env.builder_class.return_value.build.assert_not_called()


def test_macos_legacy_alert_failure_still_exits(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    with (
        patch("src.utils.platform_utils.is_macos_dark_mode", return_value=True),
        patch("src.utils.platform_utils.is_legacy_macos_tk", return_value=True),
        patch(
            "src.utils.platform_utils.apply_macos_aqua_appearance", return_value=False
        ),
        patch("subprocess.run", side_effect=OSError("no osascript")),
    ):
        _run(_services())
    env.root.destroy.assert_called_once()


def test_macos_modern_tk_continues_to_build(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    with (
        patch("src.utils.platform_utils.is_macos_dark_mode", return_value=False),
        patch("src.utils.platform_utils.is_legacy_macos_tk", return_value=False),
    ):
        _run(_services())
    env.builder_class.return_value.build.assert_called_once()


def test_old_python_version_shows_error_and_exits(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 9, 0, "final", 0))
    _run(_services())
    env.messagebox.showerror.assert_called_once()
    env.root.destroy.assert_called_once()
    env.builder_class.return_value.build.assert_not_called()


def test_module_exposes_main_handlers() -> None:
    assert event_handlers.main_handlers is not None
