"""tests/test_startup_clipboard_display.py

アプリ起動時における OS クリップボード内容の即時取得・初期表示機能の検証。
Issue #201: 起動時の「Waiting...」表示や古いDB履歴とのズレ・チラつきを解消する。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.events.event_dispatcher import EventDispatcher
from src.core.platform.services import PlatformServices


def _create_monitor(
    tk_root: Any,
    history_service: Any,
    platform_services: PlatformServices | None = None,
    excluded_apps: list[str] | None = None,
) -> ClipboardMonitor:
    dispatcher = EventDispatcher()
    db_mock = MagicMock()
    services = platform_services or PlatformServices(platform_name="darwin")
    return ClipboardMonitor(
        tk_root=tk_root,
        event_dispatcher=dispatcher,
        history_file_path="",
        db_manager=db_mock,
        history_service=history_service,
        platform_services=services,
        excluded_apps=excluded_apps or [],
    )


class TestStartupClipboardMonitor:
    def test_get_current_clipboard_text_success(self) -> None:
        """クリップボードから正常なテキストが取得・正規化されること。"""
        tk_root = MagicMock()
        tk_root.clipboard_get.return_value = "Hello Clipboard"
        history_service = MagicMock()
        monitor = _create_monitor(tk_root, history_service)

        text = monitor.get_current_clipboard_text()
        assert text == "Hello Clipboard"

    def test_get_current_clipboard_text_returns_none_when_empty_or_too_large(
        self,
    ) -> None:
        """空文字や1MB超の巨大コンテンツの場合は None を返すこと。"""
        tk_root = MagicMock()
        history_service = MagicMock()
        monitor = _create_monitor(tk_root, history_service)

        # 空文字
        tk_root.clipboard_get.return_value = ""
        assert monitor.get_current_clipboard_text() is None

        # None (取得失敗)
        tk_root.clipboard_get.return_value = None
        assert monitor.get_current_clipboard_text() is None

        # 1MB 超
        tk_root.clipboard_get.return_value = "A" * (1024 * 1024 + 1)
        assert monitor.get_current_clipboard_text() is None

    def test_sync_initial_clipboard_adds_entry_when_different_from_db(self) -> None:
        """起動時のクリップボードがDB最新履歴と異なる場合、履歴に登録して画面更新を発火すること。"""
        tk_root = MagicMock()
        tk_root.clipboard_get.return_value = "New text from browser"

        history_service = MagicMock()
        history_service.last_clipboard_data = "Old text from yesterday"

        monitor = _create_monitor(tk_root, history_service)

        result = monitor.sync_initial_clipboard()

        assert result == "New text from browser"
        assert history_service.last_clipboard_data == "New text from browser"
        history_service.add_history_item.assert_called_once_with(
            "New text from browser"
        )

    def test_sync_initial_clipboard_does_not_duplicate_when_same_as_db(self) -> None:
        """起動時のクリップボードがDB最新履歴と同じ場合、新規追加せず重複を避けること。"""
        tk_root = MagicMock()
        tk_root.clipboard_get.return_value = "Same text"

        history_service = MagicMock()
        history_service.last_clipboard_data = "Same text"

        monitor = _create_monitor(tk_root, history_service)

        result = monitor.sync_initial_clipboard()

        assert result == "Same text"
        history_service.add_history_item.assert_not_called()

    def test_sync_initial_clipboard_returns_none_when_empty(self) -> None:
        """起動時にクリップボードが空の場合、何もしないこと。"""
        tk_root = MagicMock()
        tk_root.clipboard_get.return_value = ""

        history_service = MagicMock()
        history_service.last_clipboard_data = "Existing DB text"

        monitor = _create_monitor(tk_root, history_service)

        result = monitor.sync_initial_clipboard()

        assert result is None
        assert history_service.last_clipboard_data == "Existing DB text"
        history_service.add_history_item.assert_not_called()

    def test_sync_initial_clipboard_handles_exceptions_gracefully(self) -> None:
        """クリップボード取得時に予期せぬエラーが発生しても安全に処理すること。"""
        tk_root = MagicMock()
        tk_root.clipboard_get.side_effect = RuntimeError("Clipboard access error")

        history_service = MagicMock()
        history_service.last_clipboard_data = "Existing DB text"

        # fallback もエラーにする
        platform_services = MagicMock()
        platform_services.clipboard_reader.side_effect = RuntimeError("Reader error")

        monitor = _create_monitor(
            tk_root, history_service, platform_services=platform_services
        )

        result = monitor.sync_initial_clipboard()

        assert result is None
        history_service.add_history_item.assert_not_called()


class TestStartupMainApplicationIntegration:
    def test_main_application_calls_sync_initial_clipboard_before_gui(
        self, platform_services: PlatformServices
    ) -> None:
        """MainApplication 初期化時に sync_initial_clipboard が呼ばれ、初期表示が同期されること。"""
        from src.core.app_main import MainApplication

        mock_master = MagicMock()
        mock_settings = MagicMock()
        mock_settings.get_setting.side_effect = lambda k, default=None: default
        mock_db = MagicMock()
        mock_history_service = MagicMock()
        mock_history_service.last_clipboard_data = "Initial Synced Text"
        mock_monitor = MagicMock()
        mock_dispatcher = MagicMock()

        with (
            patch("src.core.app_main.ClipWatcherGUI") as mock_gui_cls,
            patch("src.core.app_main.menu_bar"),
            patch("src.event_handlers.register_class_based_handlers"),
        ):
            app = MainApplication(
                master=mock_master,
                settings_manager=mock_settings,
                db_manager=mock_db,
                history_service=mock_history_service,
                monitor=mock_monitor,
                plugin_manager=MagicMock(),
                event_dispatcher=mock_dispatcher,
                theme_manager=MagicMock(),
                translator=MagicMock(),
                app_status=MagicMock(),
                platform_services=platform_services,
                notification_manager=MagicMock(),
            )

            # GUI初期化前に sync_initial_clipboard が呼ばれていること
            mock_monitor.sync_initial_clipboard.assert_called_once()
            mock_gui_cls.assert_called_once_with(mock_master, app)


class TestStartupMainGUIBehavior:
    def test_update_widget_text_uses_last_clipboard_data_if_available(self) -> None:
        """_update_widget_text は last_clipboard_data があればそのテキストをテキストエリアにセットすること。"""
        from src.gui.main_gui import ClipWatcherGUI

        gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
        gui.master = MagicMock()
        gui.notebook = MagicMock()
        gui.clipboard_tab_frame = MagicMock()
        gui.current_clipboard_frame = MagicMock()
        gui.search_label = MagicMock()
        gui.history_container_frame = MagicMock()
        gui.copy_history_button = MagicMock()
        gui.sort_button = MagicMock()
        gui.format_button = MagicMock()
        gui.quit_button = MagicMock()
        gui.meta_management_tab_frame = MagicMock()

        gui.clipboard_text_widget = MagicMock()
        gui.clipboard_text_widget.get.return_value = ""  # 空

        gui.app = MagicMock()
        gui.app.history_sort_ascending = False
        gui.app.translator = lambda k: f"[{k}]"
        gui.app.history_service.last_clipboard_data = "Startup Copied String"

        gui._update_widget_text()

        gui.clipboard_text_widget.insert.assert_called_once_with(
            "end", "Startup Copied String"
        )
        assert gui._text_source_text == "Startup Copied String"

    def test_update_widget_text_shows_waiting_when_no_clipboard_data(self) -> None:
        """last_clipboard_data が空の場合は waiting_for_clipboard_content をセットすること。"""
        from src.gui.main_gui import ClipWatcherGUI

        gui = ClipWatcherGUI.__new__(ClipWatcherGUI)
        gui.master = MagicMock()
        gui.notebook = MagicMock()
        gui.clipboard_tab_frame = MagicMock()
        gui.current_clipboard_frame = MagicMock()
        gui.search_label = MagicMock()
        gui.history_container_frame = MagicMock()
        gui.copy_history_button = MagicMock()
        gui.sort_button = MagicMock()
        gui.format_button = MagicMock()
        gui.quit_button = MagicMock()
        gui.meta_management_tab_frame = MagicMock()

        gui.clipboard_text_widget = MagicMock()
        gui.clipboard_text_widget.get.return_value = ""  # 空

        gui.app = MagicMock()
        gui.app.history_sort_ascending = False
        gui.app.translator = lambda k: f"[{k}]"
        gui.app.history_service.last_clipboard_data = ""

        gui._update_widget_text()

        gui.clipboard_text_widget.insert.assert_called_once_with(
            "end", "[waiting_for_clipboard_content]"
        )
        assert gui._text_source_text == "[waiting_for_clipboard_content]"
