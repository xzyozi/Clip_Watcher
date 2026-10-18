"""ApplicationBuilderの初期化順序とコンポーネント登録を検証する。"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.bootstrap.exceptions import ConfigError
from src.core.platform.services import PlatformServices


def test_with_icon_manager_creates_and_registers_icon_manager(
    platform_services: PlatformServices,
) -> None:
    """要件5.4: IconManagerを生成し、ThemeManagerへ登録する。"""
    root = MagicMock()

    with patch(
        "src.core.bootstrap.application_builder.ThemeManager"
    ) as theme_manager_class:
        theme_manager = theme_manager_class.return_value
        builder = ApplicationBuilder(platform_services).with_theme_manager(root)

        result = builder.with_icon_manager("test-assets/icons")

    assert result is builder
    assert builder.icon_manager is not None
    assert builder.icon_manager._icons_dir == "test-assets/icons"
    theme_manager.set_icon_manager.assert_called_once_with(builder.icon_manager)


def test_with_icon_manager_requires_theme_manager_to_be_initialized_first(
    platform_services: PlatformServices,
) -> None:
    """要件5.4: ThemeManager未初期化なら呼出順を示すエラーにする。"""
    builder = ApplicationBuilder(platform_services)

    with pytest.raises(ConfigError, match=r"with_theme_manager\(\)"):
        builder.with_icon_manager()


def test_build_passes_icon_manager_to_main_application(
    platform_services: PlatformServices,
) -> None:
    """要件5.4: Builderは初期化済みIconManagerをMainApplicationへ渡す。"""
    builder = ApplicationBuilder(platform_services)
    builder.settings_manager = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()
    builder.monitor = MagicMock()
    builder.plugin_manager = MagicMock()
    builder.event_dispatcher = MagicMock()
    builder.theme_manager = MagicMock()
    builder.translator = MagicMock()
    builder.app_status = MagicMock()
    builder.icon_manager = MagicMock()
    built_app = MagicMock()

    with patch(
        "src.core.app_main.MainApplication", return_value=built_app
    ) as main_application_class:
        result = builder.build(MagicMock())

    assert result is built_app
    assert (
        main_application_class.call_args.kwargs["icon_manager"] is builder.icon_manager
    )
    built_app.on_ready.assert_called_once_with()


def test_build_passes_platform_services_to_main_application(
    platform_services: PlatformServices,
) -> None:
    """BuilderはPlatformServicesをMainApplicationへそのまま渡す。"""
    builder = ApplicationBuilder(platform_services)
    builder.settings_manager = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()
    builder.monitor = MagicMock()
    builder.plugin_manager = MagicMock()
    builder.event_dispatcher = MagicMock()
    builder.theme_manager = MagicMock()
    builder.translator = MagicMock()
    builder.app_status = MagicMock()

    with patch("src.core.app_main.MainApplication") as main_application_class:
        builder.build(MagicMock())

    assert (
        main_application_class.call_args.kwargs["platform_services"]
        is platform_services
    )


def test_build_creates_notification_manager_and_subscribes_to_settings(
    platform_services: PlatformServices,
) -> None:
    """NotificationManager は Builder が生成し、設定変更イベントを購読して MainApplication へ渡す。"""
    builder = ApplicationBuilder(platform_services)
    builder.settings_manager = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()
    builder.monitor = MagicMock()
    builder.plugin_manager = MagicMock()
    builder.event_dispatcher = MagicMock()
    builder.theme_manager = MagicMock()
    builder.translator = MagicMock()
    builder.app_status = MagicMock()

    with patch("src.core.app_main.MainApplication") as main_application_class:
        builder.build(MagicMock())

    notification_manager = main_application_class.call_args.kwargs[
        "notification_manager"
    ]
    assert notification_manager.platform_services is platform_services
    builder.event_dispatcher.subscribe.assert_any_call(
        "SETTINGS_CHANGED", notification_manager.update_settings
    )


def test_clipboard_monitor_does_not_own_history_or_notification_facade() -> None:
    """ClipboardMonitor は履歴操作・通知の委譲メソッドを持たず、監視に専念する (#116)。"""
    from src.core.clipboard.clipboard_monitor import ClipboardMonitor

    for name in (
        "get_history",
        "clear_history",
        "delete_history_item_by_id",
        "pin_item_by_id",
        "unpin_item_by_id",
        "delete_all_unpinned_history",
        "import_history",
        "get_filtered_history",
        "update_history_item_by_id",
        "history",
        "last_clipboard_data",
    ):
        assert not hasattr(ClipboardMonitor, name), name


def test_with_clipboard_monitor_passes_platform_services(
    platform_services: PlatformServices,
) -> None:
    """BuilderはPlatformServicesをClipboardMonitorへそのまま渡す。"""
    builder = ApplicationBuilder(platform_services)
    builder.event_dispatcher = MagicMock()
    builder.app_status = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()

    with patch(
        "src.core.bootstrap.application_builder.ClipboardMonitor"
    ) as monitor_class:
        builder.with_clipboard_monitor(MagicMock(), "history.json")

    assert monitor_class.call_args.args[-1] is platform_services


def test_with_global_hotkey_listener_non_windows() -> None:
    """ホットキー非対応環境で with_global_hotkey_listener が None を設定することを検証する。"""
    services = PlatformServices(platform_name="darwin")

    builder = ApplicationBuilder(services)
    builder.event_dispatcher = MagicMock()
    mock_handler = MagicMock()

    result = builder.with_global_hotkey_listener(mock_handler)
    assert result is builder
    assert builder.hotkey_listener is None

    builder.with_hotkey_registration_manager()
    assert builder.hotkey_registration_manager is None
