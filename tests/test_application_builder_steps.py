"""ApplicationBuilder の各構築ステップ（成功・前提条件不足・初期化失敗）のテスト。

個々のコンポーネントはモックに差し替え、ステップ間の前提条件チェックと
エラー時の ConfigError 変換・通知を検証する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.bootstrap.exceptions import ConfigError
from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.services import PlatformServices

MODULE = "src.core.bootstrap.application_builder"


@pytest.fixture(autouse=True)
def _silence_error_dialog() -> Any:
    """失敗時の log_and_show_error が実際のダイアログを開かないようにする。"""
    with patch(f"{MODULE}.log_and_show_error") as report:
        yield report


@pytest.fixture
def builder() -> ApplicationBuilder:
    return ApplicationBuilder(PlatformServices(platform_name="test"))


def _boom(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("boom")


# --- 成功・失敗が対称なステップ ---


def test_event_dispatcher_step(
    builder: ApplicationBuilder, _silence_error_dialog: MagicMock
) -> None:
    assert builder.with_event_dispatcher() is builder
    assert builder.event_dispatcher is not None

    with patch(f"{MODULE}.EventDispatcher", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_event_dispatcher()
    _silence_error_dialog.assert_called_once()


def test_database_step(builder: ApplicationBuilder, tmp_path: Path) -> None:
    assert builder.with_database(str(tmp_path / "x.db")) is builder
    assert builder.db_manager is not None

    with patch("src.db.database_manager.DatabaseManager", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_database("ignored.db")


def test_dependency_check_step(builder: ApplicationBuilder) -> None:
    with patch(f"{MODULE}.DependencyChecker.check_dependencies") as check:
        check.return_value = {}
        assert builder.with_dependency_check() is builder
    assert builder.app_status is not None

    with patch(f"{MODULE}.DependencyChecker.check_dependencies", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_dependency_check()


def test_settings_step_requires_dispatcher_then_builds_manager(
    builder: ApplicationBuilder, tmp_path: Path
) -> None:
    with pytest.raises(ConfigError, match="イベントディスパッチャ"):
        builder.with_settings(str(tmp_path / "settings.json"))

    builder.with_event_dispatcher()
    assert builder.with_settings(str(tmp_path / "settings.json")) is builder
    assert builder.settings_manager is not None

    with patch(f"{MODULE}.SettingsManager", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_settings("ignored.json")


def test_translator_step(builder: ApplicationBuilder) -> None:
    with pytest.raises(ConfigError, match="設定マネージャー"):
        builder.with_translator()

    builder.settings_manager = MagicMock()
    with patch(f"{MODULE}.Translator") as translator:
        assert builder.with_translator() is builder
    assert builder.translator is translator.return_value

    with patch(f"{MODULE}.Translator", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_translator()


def test_theme_manager_step(builder: ApplicationBuilder) -> None:
    with patch(f"{MODULE}.ThemeManager") as theme_manager:
        assert builder.with_theme_manager(MagicMock()) is builder
    assert builder.theme_manager is theme_manager.return_value

    with patch(f"{MODULE}.ThemeManager", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_theme_manager(MagicMock())


def test_history_service_step(builder: ApplicationBuilder, tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="イベントディスパッチャ"):
        builder.with_history_service()

    builder.with_event_dispatcher()
    builder.with_database(str(tmp_path / "h.db"))
    builder.settings_manager = MagicMock()
    builder.settings_manager.get_setting.return_value = 7
    assert builder.with_history_service() is builder
    assert builder.history_service is not None
    assert builder.history_service.history_limit == 7


def test_history_service_step_rejects_non_integer_limit(
    builder: ApplicationBuilder, tmp_path: Path
) -> None:
    builder.with_event_dispatcher()
    builder.with_database(str(tmp_path / "h.db"))
    builder.settings_manager = MagicMock()
    builder.settings_manager.get_setting.return_value = "many"
    with pytest.raises(ConfigError):
        builder.with_history_service()


def test_history_service_step_uses_default_limit_without_settings(
    builder: ApplicationBuilder, tmp_path: Path
) -> None:
    builder.with_event_dispatcher()
    builder.with_database(str(tmp_path / "h.db"))
    assert builder.with_history_service() is builder
    assert builder.history_service is not None


def test_plugin_manager_step(builder: ApplicationBuilder) -> None:
    with patch(f"{MODULE}.PluginManager") as plugin_manager:
        assert builder.with_plugin_manager() is builder
    assert builder.plugin_manager is plugin_manager.return_value

    with patch(f"{MODULE}.PluginManager", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_plugin_manager()


def test_window_state_manager_step(builder: ApplicationBuilder) -> None:
    master = MagicMock()
    with patch("src.core.window.window_state_manager.WindowStateManager") as manager:
        assert builder.with_window_state_manager(master) is builder
    manager.assert_called_once_with(master)

    with patch(
        "src.core.window.window_state_manager.WindowStateManager", side_effect=_boom
    ):
        with pytest.raises(ConfigError):
            builder.with_window_state_manager(master)


def test_clipboard_monitor_step(builder: ApplicationBuilder) -> None:
    with pytest.raises(ConfigError):
        builder.with_clipboard_monitor(MagicMock(), "history.json")

    builder.event_dispatcher = MagicMock()
    builder.app_status = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()
    with patch(f"{MODULE}.ClipboardMonitor") as monitor_cls:
        assert builder.with_clipboard_monitor(MagicMock(), "history.json") is builder
    assert builder.monitor is monitor_cls.return_value

    with patch(f"{MODULE}.ClipboardMonitor", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_clipboard_monitor(MagicMock(), "history.json")


# --- テキストワークフロー ---


def test_text_workflow_step_requires_dispatcher(builder: ApplicationBuilder) -> None:
    with pytest.raises(ConfigError):
        builder.with_text_workflow_service(MagicMock(), "data")


def test_text_workflow_step_builds_service_with_ui_marshal(
    builder: ApplicationBuilder, tmp_path: Path
) -> None:
    builder.event_dispatcher = MagicMock()
    master = MagicMock()
    with patch("src.services.text_workflow_service.TextWorkflowService") as service:
        assert builder.with_text_workflow_service(master, str(tmp_path)) is builder
    marshal: Callable[[Callable[[], None]], None] = service.call_args.kwargs[
        "ui_thread_marshal"
    ]
    callback = MagicMock()
    marshal(callback)
    master.after.assert_called_once_with(0, callback)
    assert builder.text_workflow_service is service.return_value


def test_text_workflow_step_reports_failures(
    builder: ApplicationBuilder, tmp_path: Path
) -> None:
    builder.event_dispatcher = MagicMock()
    with patch("src.core.text_workflow.history.ExecutionHistory", side_effect=_boom):
        with pytest.raises(ConfigError):
            builder.with_text_workflow_service(MagicMock(), str(tmp_path))


# --- ホットキー ---


def test_hotkey_listener_step_requires_dispatcher(builder: ApplicationBuilder) -> None:
    with pytest.raises(ConfigError):
        builder.with_global_hotkey_listener(MagicMock())


def test_hotkey_listener_step_dispatches_triggered_events(
    builder: ApplicationBuilder,
) -> None:
    builder.event_dispatcher = MagicMock()
    builder.platform_services = MagicMock()
    master = MagicMock()
    assert builder.with_global_hotkey_listener(master) is builder
    callback = builder.platform_services.create_hotkey_listener.call_args.kwargs[
        "on_triggered"
    ]
    callback(7)
    builder.event_dispatcher.dispatch.assert_called_once_with(
        "GLOBAL_HOTKEY_TRIGGERED", 7
    )
    assert builder.hotkey_listener is not None


def test_hotkey_listener_step_skips_unsupported_platform(
    builder: ApplicationBuilder,
) -> None:
    builder.event_dispatcher = MagicMock()
    builder.platform_services = MagicMock()
    builder.platform_services.create_hotkey_listener.side_effect = (
        UnsupportedFeatureError("hotkey", "test")
    )
    assert builder.with_global_hotkey_listener(MagicMock()) is builder
    assert builder.hotkey_listener is None


def test_hotkey_listener_step_reports_unexpected_failures(
    builder: ApplicationBuilder,
) -> None:
    builder.event_dispatcher = MagicMock()
    builder.platform_services = MagicMock()
    builder.platform_services.create_hotkey_listener.side_effect = RuntimeError("x")
    with pytest.raises(ConfigError):
        builder.with_global_hotkey_listener(MagicMock())


def test_hotkey_registration_manager_step(builder: ApplicationBuilder) -> None:
    assert builder.with_hotkey_registration_manager() is builder
    assert builder.hotkey_registration_manager is None  # リスナー無効なら作らない

    builder.hotkey_listener = MagicMock()
    with patch(
        "src.core.hotkey.hotkey_registration_manager.HotkeyRegistrationManager"
    ) as manager:
        assert builder.with_hotkey_registration_manager() is builder
    manager.assert_called_once_with(builder.hotkey_listener)

    with patch(
        "src.core.hotkey.hotkey_registration_manager.HotkeyRegistrationManager",
        side_effect=_boom,
    ):
        with pytest.raises(ConfigError):
            builder.with_hotkey_registration_manager()


# --- build ---


def _fill_components(builder: ApplicationBuilder) -> None:
    for name in (
        "settings_manager",
        "db_manager",
        "history_service",
        "monitor",
        "plugin_manager",
        "event_dispatcher",
        "theme_manager",
        "translator",
        "app_status",
    ):
        setattr(builder, name, MagicMock())


def test_build_requires_all_core_components(builder: ApplicationBuilder) -> None:
    with pytest.raises(ConfigError, match="必要なコンポーネント"):
        builder.build(MagicMock())


def test_build_loads_settings_before_signalling_ready(
    builder: ApplicationBuilder,
) -> None:
    _fill_components(builder)
    order: list[str] = []
    builder.settings_manager.load_and_notify.side_effect = lambda: order.append("load")  # type: ignore[union-attr]
    with patch("src.core.app_main.MainApplication") as app_cls:
        app_cls.return_value.on_ready.side_effect = lambda: order.append("ready")
        builder.build(MagicMock())
    assert order == ["load", "ready"]


def test_build_wraps_application_errors(builder: ApplicationBuilder) -> None:
    _fill_components(builder)
    with patch("src.core.app_main.MainApplication", side_effect=_boom):
        with pytest.raises(ConfigError, match="構築に失敗"):
            builder.build(MagicMock())
