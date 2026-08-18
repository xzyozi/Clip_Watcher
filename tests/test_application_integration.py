"""tests/test_application_integration.py

ApplicationBuilder と MainApplication へのホットキー・ウィンドウ状態組み込み検証。
"""
from unittest.mock import MagicMock, patch

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.window.window_state_manager import WindowState, WindowStateManager


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
            translator=mock_translator,
            app_status=mock_status,
            window_state_manager=mock_wsm,
            hotkey_registration_manager=mock_hrm,
        )

        assert app.window_state_manager is mock_wsm
        assert app.hotkey_registration_manager is mock_hrm

        # GLOBAL_HOTKEY_TRIGGERED サブスクライブの確認
        mock_dispatcher.subscribe.assert_any_call("GLOBAL_HOTKEY_TRIGGERED", app.event_dispatcher.subscribe.call_args[0][1] if app.event_dispatcher.subscribe.call_args else MagicMock())

        # on_ready 呼び出し時の reconfigure
        app.on_ready()
        mock_hrm.reconfigure.assert_called_once_with(True, "Ctrl+Shift+F")

        # shutdown 呼び出し時の stop
        app.shutdown()
        mock_hrm.stop.assert_called_once()
