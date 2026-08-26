"""tests/test_application_integration.py

ApplicationBuilder と MainApplication へのホットキー・ウィンドウ状態組み込み検証。
"""
from unittest.mock import MagicMock, patch

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.window.window_state_manager import WindowState


def test_application_builder_component_injection() -> None:
    mock_root = MagicMock()

    with patch("src.core.window.window_state_manager.WindowStateManager") as mock_wsm_cls, \
         patch("src.core.hotkey.global_hotkey_listener.GlobalHotkeyListener") as mock_hkl_cls, \
         patch("src.core.hotkey.hotkey_registration_manager.HotkeyRegistrationManager") as mock_hrm_cls:

        mock_wsm = MagicMock()
        mock_wsm_cls.return_value = mock_wsm
        mock_hkl = MagicMock()
        mock_hkl_cls.return_value = mock_hkl
        mock_hrm = MagicMock()
        mock_hrm_cls.return_value = mock_hrm

        builder = (
            ApplicationBuilder()
            .with_event_dispatcher()
            .with_window_state_manager(mock_root)
            .with_global_hotkey_listener(mock_root)
            .with_hotkey_registration_manager()
        )

        assert builder.window_state_manager is mock_wsm
        assert builder.hotkey_listener is mock_hkl
        assert builder.hotkey_registration_manager is mock_hrm


def test_main_application_hotkey_and_window_integration() -> None:
    from src.core.app_main import MainApplication

    mock_master = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_setting.side_effect = lambda k, default=None: default
    mock_db = MagicMock()
    mock_history_service = MagicMock()
    mock_monitor = MagicMock()
    mock_plugin_manager = MagicMock()
    mock_dispatcher = MagicMock()
    mock_theme = MagicMock()
    mock_icon_manager = MagicMock()
    mock_translator = MagicMock()
    mock_status = MagicMock()
    mock_wsm = MagicMock()
    mock_wsm.state = WindowState.VISIBLE
    mock_hrm = MagicMock()

    with patch("src.core.app_main.ClipWatcherGUI"), \
         patch("src.core.app_main.menu_bar"), \
         patch("src.event_handlers.register_class_based_handlers"):

        app = MainApplication(
            master=mock_master,
            settings_manager=mock_settings,
            db_manager=mock_db,
            history_service=mock_history_service,
            monitor=mock_monitor,
            plugin_manager=mock_plugin_manager,
            event_dispatcher=mock_dispatcher,
            theme_manager=mock_theme,
            icon_manager=mock_icon_manager,
            translator=mock_translator,
            app_status=mock_status,
            window_state_manager=mock_wsm,
            hotkey_registration_manager=mock_hrm,
        )

        assert app.window_state_manager is mock_wsm
        assert app.hotkey_registration_manager is mock_hrm
        assert app.icon_manager is mock_icon_manager

        mock_dispatcher.subscribe.assert_any_call(
            "GLOBAL_HOTKEY_TRIGGERED", app.event_dispatcher.subscribe.call_args[0][1] if app.event_dispatcher.subscribe.call_args else MagicMock()
        )

        app.on_ready()
        mock_hrm.reconfigure.assert_called_once_with(True, "Ctrl+Shift+F")

        app.shutdown()
        mock_hrm.stop.assert_called_once()


def test_global_hotkey_triggered_event_dispatch_zero_args() -> None:
    from src.core.app_main import MainApplication
    from src.core.events.event_dispatcher import EventDispatcher

    dispatcher = EventDispatcher()
    mock_master = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_setting.side_effect = lambda k, default=None: default
    mock_wsm = MagicMock()

    with patch("src.core.app_main.ClipWatcherGUI"), \
         patch("src.core.app_main.menu_bar"), \
         patch("src.event_handlers.register_class_based_handlers"):

        _ = MainApplication(
            master=mock_master,
            settings_manager=mock_settings,
            db_manager=MagicMock(),
            history_service=MagicMock(),
            monitor=MagicMock(),
            plugin_manager=MagicMock(),
            event_dispatcher=dispatcher,
            theme_manager=MagicMock(),
            translator=MagicMock(),
            app_status=MagicMock(),
            window_state_manager=mock_wsm,
            hotkey_registration_manager=MagicMock(),
        )

        # 引数なしで dispatch された場合に TypeError が発生せず toggle が実行されること
        dispatcher.dispatch("GLOBAL_HOTKEY_TRIGGERED")
        mock_wsm.toggle.assert_called_once()


def test_start_app_builder_chain_includes_icon_manager_after_theme_manager() -> None:
    """要件5.4: 起動チェーンはテーママネージャー直後にIconManagerを初期化する。"""
    from src.event_handlers import start_app

    with patch("socket.socket"), \
         patch("src.event_handlers.setup_logging"), \
         patch("scripts.migrate_json_to_sqlite.main"), \
         patch("src.event_handlers.tk.Tk") as mock_tk_cls, \
         patch("src.event_handlers.ApplicationBuilder") as mock_builder_cls:

        mock_root = MagicMock()
        mock_tk_cls.return_value = mock_root

        mock_builder = MagicMock()
        mock_builder_cls.return_value = mock_builder
        mock_builder.with_event_dispatcher.return_value = mock_builder
        mock_builder.with_dependency_check.return_value = mock_builder
        mock_builder.with_settings.return_value = mock_builder
        mock_builder.with_database.return_value = mock_builder
        mock_builder.with_translator.return_value = mock_builder
        mock_builder.with_theme_manager.return_value = mock_builder
        mock_builder.with_icon_manager.return_value = mock_builder
        mock_builder.with_history_service.return_value = mock_builder
        mock_builder.with_plugin_manager.return_value = mock_builder
        mock_builder.with_window_state_manager.return_value = mock_builder
        mock_builder.with_global_hotkey_listener.return_value = mock_builder
        mock_builder.with_hotkey_registration_manager.return_value = mock_builder
        mock_builder.with_clipboard_monitor.return_value = mock_builder

        mock_root.mainloop.side_effect = KeyboardInterrupt

        try:
            start_app()
        except KeyboardInterrupt:
            pass

        relevant_calls = [
            (method_call[0], method_call[1], method_call[2])
            for method_call in mock_builder.method_calls
            if method_call[0]
            in {"with_theme_manager", "with_icon_manager", "with_history_service"}
        ]
        assert relevant_calls == [
            ("with_theme_manager", (mock_root,), {}),
            ("with_icon_manager", (), {}),
            ("with_history_service", (), {}),
        ]
        mock_builder.with_window_state_manager.assert_called_once_with(mock_root)
        mock_builder.with_global_hotkey_listener.assert_called_once_with(mock_root)
        mock_builder.with_hotkey_registration_manager.assert_called_once()
