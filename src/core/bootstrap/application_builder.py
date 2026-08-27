from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING

from src.core.bootstrap.dependency_checker import DependencyChecker
from src.core.bootstrap.exceptions import ConfigError
from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.config.app_status import AppStatus
from src.core.config.defaults import DEFAULT_USER_SETTINGS
from src.core.config.settings_manager import SettingsManager
from src.core.events.event_dispatcher import EventDispatcher
from src.gui.icon_manager import IconManager
from src.gui.theme_manager import ThemeManager
from src.plugins.manager import PluginManager
from src.utils.error_handler import log_and_show_error
from src.utils.i18n import Translator

if TYPE_CHECKING:
    from src.core.app_main import MainApplication
    from src.core.hotkey.global_hotkey_listener import GlobalHotkeyListener
    from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager
    from src.core.window.window_state_manager import WindowStateManager
    from src.db.database_manager import DatabaseManager
    from src.services.history_service import HistoryService

logger = logging.getLogger(__name__)


class ApplicationBuilder:
    """アプリケーションの構築を担当するクラス"""

    def __init__(self) -> None:
        self.settings_manager: SettingsManager | None = None
        self.db_manager: DatabaseManager | None = None
        self.history_service: HistoryService | None = None
        self.monitor: ClipboardMonitor | None = None
        self.plugin_manager: PluginManager | None = None
        self.event_dispatcher: EventDispatcher | None = None
        self.theme_manager: ThemeManager | None = None
        self.icon_manager: IconManager | None = None

        self.translator: Translator | None = None
        self.app_status: AppStatus | None = None

        self.window_state_manager: WindowStateManager | None = None
        self.hotkey_listener: GlobalHotkeyListener | None = None
        self.hotkey_registration_manager: HotkeyRegistrationManager | None = None

    def with_event_dispatcher(self) -> ApplicationBuilder:
        """イベントディスパッチャの初期化"""
        try:
            self.event_dispatcher = EventDispatcher()
            logger.info("イベントディスパッチャを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"イベントディスパッチャの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"イベントディスパッチャの初期化に失敗しました: {str(e)}"
            ) from e

    def with_database(self, db_path: str) -> ApplicationBuilder:
        """データベースマネージャーの初期化"""
        try:
            from src.db.database_manager import DatabaseManager

            self.db_manager = DatabaseManager(db_path)
            logger.info("データベースマネージャーを初期化しました: %s", db_path)
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"データベースの初期化に失敗: {str(e)}"
            )
            raise ConfigError(f"データベースの初期化に失敗しました: {str(e)}") from e

    def with_dependency_check(self) -> ApplicationBuilder:
        """依存関係のチェック"""
        try:
            dependency_status = DependencyChecker.check_dependencies()
            self.app_status = AppStatus(dependencies=dependency_status)
            logger.info("依存関係のチェックが完了しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"依存関係のチェック中にエラーが発生: {str(e)}"
            )
            raise ConfigError(f"依存関係のチェックに失敗しました: {str(e)}") from e

    def with_settings(
        self, settings_file_path: str = "settings.json"
    ) -> ApplicationBuilder:
        """設定マネージャーの初期化"""
        if not self.event_dispatcher:
            raise ConfigError("イベントディスパッチャが初期化されていません")
        try:
            self.settings_manager = SettingsManager(
                self.event_dispatcher, settings_file_path
            )
            logger.info("設定マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"設定マネージャーの初期化に失敗: {str(e)}"
            )
            raise ConfigError(f"設定の読み込みに失敗しました: {str(e)}") from e

    def with_translator(self) -> ApplicationBuilder:
        """翻訳サービスの初期化"""
        if not self.settings_manager:
            raise ConfigError("設定マネージャーが初期化されていません")
        try:
            self.translator = Translator(self.settings_manager)
            logger.info("翻訳サービスを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"翻訳サービスの初期化に失敗: {str(e)}"
            )
            raise ConfigError(f"翻訳サービスの初期化に失敗しました: {str(e)}") from e

    def with_theme_manager(self, root: tk.Tk) -> ApplicationBuilder:
        """テーママネージャーの初期化"""
        try:
            self.theme_manager = ThemeManager(root)
            logger.info("テーママネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"テーママネージャーの初期化に失敗: {str(e)}"
            )
            raise ConfigError(
                f"テーママネージャーの初期化に失敗しました: {str(e)}"
            ) from e

    def with_icon_manager(self, icons_dir: str = "assets/icons") -> ApplicationBuilder:
        """IconManagerを初期化し、ThemeManagerへ登録する。

        このメソッドは必ず ``with_theme_manager()`` の後に呼び出すこと。

        Args:
            icons_dir: アイコンPNGファイルを格納するディレクトリ。

        Raises:
            ConfigError: ThemeManagerが初期化されていない場合。
        """
        if self.theme_manager is None:
            raise ConfigError(
                "テーママネージャーが初期化されていません。"
                "with_icon_manager()の前にwith_theme_manager()を呼び出してください"
            )

        self.icon_manager = IconManager(icons_dir)
        self.theme_manager.set_icon_manager(self.icon_manager)
        logger.info("アイコンマネージャーを初期化し、テーママネージャーへ登録しました")
        return self

    def with_history_service(self) -> ApplicationBuilder:
        """履歴サービスの初期化"""
        if not self.event_dispatcher or not self.db_manager:
            raise ConfigError(
                "イベントディスパッチャまたはデータベースマネージャーが初期化されていません"
            )
        try:
            from src.services.history_service import HistoryService

            # デフォルト設定から履歴数上限を取得（後でSETTINGS_CHANGEDでも同期されます）
            # history_limit のデフォルト値は defaults.DEFAULT_USER_SETTINGS を単一の参照元とする。
            limit = DEFAULT_USER_SETTINGS["history_limit"]
            if self.settings_manager:
                limit = self.settings_manager.get_setting("history_limit", limit)
            if not isinstance(limit, int):
                raise ConfigError("history_limitは整数である必要があります")
            self.history_service = HistoryService(
                self.db_manager, self.event_dispatcher, history_limit=limit
            )
            logger.info("履歴サービスを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"履歴サービスの初期化に失敗: {str(e)}"
            )
            raise ConfigError(f"履歴サービスの初期化に失敗しました: {str(e)}") from e

    def with_clipboard_monitor(
        self, master: tk.Tk, history_file_path: str
    ) -> ApplicationBuilder:
        """クリップボードモニターの初期化"""
        if (
            not self.event_dispatcher
            or not self.app_status
            or not self.db_manager
            or not self.history_service
        ):
            raise ConfigError(
                "イベントディスパッチャ、アプリケーションステータス、データベースマネージャー、または履歴サービスが初期化されていません"
            )

        try:
            win32_available = self.app_status.dependencies.win32_available
            self.monitor = ClipboardMonitor(
                master,
                self.event_dispatcher,
                history_file_path,
                win32_available,
                self.db_manager,
                self.history_service,
            )
            logger.info("クリップボードモニターを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"クリップボードモニターの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"クリップボードモニターの初期化に失敗しました: {str(e)}"
            ) from e

    def with_plugin_manager(self) -> ApplicationBuilder:
        """プラグインマネージャーの初期化"""
        try:
            self.plugin_manager = PluginManager()
            logger.info("プラグインマネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"プラグインマネージャーの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"プラグインマネージャーの初期化に失敗しました: {str(e)}"
            ) from e

    def with_window_state_manager(self, master: tk.Tk) -> ApplicationBuilder:
        """ウィンドウ状態マネージャーの初期化"""
        try:
            from src.core.window.window_state_manager import WindowStateManager

            self.window_state_manager = WindowStateManager(master)
            logger.info("ウィンドウ状態マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"ウィンドウ状態マネージャーの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"ウィンドウ状態マネージャーの初期化に失敗しました: {str(e)}"
            ) from e

    def with_global_hotkey_listener(self, master: tk.Tk) -> ApplicationBuilder:
        """グローバルホットキーリスナーの初期化"""
        event_dispatcher = self.event_dispatcher
        if event_dispatcher is None:
            raise ConfigError("イベントディスパッチャが初期化されていません")
        try:
            from src.core.hotkey.global_hotkey_listener import GlobalHotkeyListener

            self.hotkey_listener = GlobalHotkeyListener(
                master,
                on_triggered=lambda hotkey_id: event_dispatcher.dispatch(
                    "GLOBAL_HOTKEY_TRIGGERED", hotkey_id
                ),
            )
            logger.info("グローバルホットキーリスナーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"グローバルホットキーリスナーの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"グローバルホットキーリスナーの初期化に失敗しました: {str(e)}"
            ) from e

    def with_hotkey_registration_manager(self) -> ApplicationBuilder:
        """ホットキー登録マネージャーの初期化"""
        if not self.hotkey_listener:
            raise ConfigError("グローバルホットキーリスナーが初期化されていません")
        try:
            from src.core.hotkey.hotkey_registration_manager import (
                HotkeyRegistrationManager,
            )

            self.hotkey_registration_manager = HotkeyRegistrationManager(
                self.hotkey_listener
            )
            logger.info("ホットキー登録マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(
                title="エラー",
                message=f"ホットキー登録マネージャーの初期化に失敗: {str(e)}",
            )
            raise ConfigError(
                f"ホットキー登録マネージャーの初期化に失敗しました: {str(e)}"
            ) from e

    def build(self, master: tk.Tk) -> MainApplication:
        """アプリケーションのビルド"""
        if not all(
            [
                self.settings_manager,
                self.db_manager,
                self.history_service,
                self.monitor,
                self.plugin_manager,
                self.event_dispatcher,
                self.theme_manager,
                self.translator,
                self.app_status,
            ]
        ):
            raise ConfigError("必要なコンポーネントが初期化されていません")

        try:
            from src.core.app_main import MainApplication

            app = MainApplication(
                master=master,
                settings_manager=self.settings_manager,  # type: ignore
                db_manager=self.db_manager,  # type: ignore
                history_service=self.history_service,  # type: ignore
                monitor=self.monitor,  # type: ignore
                plugin_manager=self.plugin_manager,  # type: ignore
                event_dispatcher=self.event_dispatcher,  # type: ignore
                theme_manager=self.theme_manager,  # type: ignore
                icon_manager=self.icon_manager,
                translator=self.translator,  # type: ignore
                app_status=self.app_status,  # type: ignore
                window_state_manager=self.window_state_manager,
                hotkey_registration_manager=self.hotkey_registration_manager,
            )
            logger.info("アプリケーションのビルドが完了しました")

            # Load settings and notify all components
            self.settings_manager.load_and_notify()  # type: ignore

            # Signal that the application is ready
            app.on_ready()

            return app
        except Exception as e:
            log_and_show_error(
                title="エラー", message=f"アプリケーションのビルドに失敗: {str(e)}"
            )
            raise ConfigError(f"アプリケーションの構築に失敗しました: {str(e)}") from e
